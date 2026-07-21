"""
Per-property vegetation zonal statistics.

Ported from scripts/zonal_statistics_v3.py. Computes natural vegetation
area per year for three raster zones — Propriedade (whole property), APP
(Permanent Preservation Area), and Reserva Legal (Legal Reserve) — by
clipping the vegetation time-series rasters and two binary zone masks
against the property geometry. Two derived zones are computed on top of
those: the APP ∪ RL union (deduplicating their overlap) and the Excedente
Florestal (forest surplus) — see ``compute_zonal_history``'s docstring.

The geometry is received from the client (not read from a parquet file).

APP and RL rasters may be in a different CRS (e.g. ESRI:102033) than the
vegetation rasters (e.g. EPSG:4326). When that happens, WarpedVRT is used
to reproject them on-the-fly to the vegetation CRS before clipping. If the
resulting pixel grids still don't align (different resolutions), the masks
are resampled to match the vegetation grid using nearest-neighbour interpolation.

Key differences from the v2 script:
  - classes_naturais is a tuple (default (1,)) instead of a single int,
    matching v3's np.isin() approach.
  - area_total_ha for Propriedade is computed from the vector geometry area,
    not from pixel count (matching v3).
  - area_total_ha for APP/RL is computed from the zone mask pixel count,
    matching v3.
"""

import glob
import os
import re
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import rasterio
from pyproj import CRS, Geod, Transformer
from rasterio.mask import mask
from rasterio.vrt import WarpedVRT
from rasterio.warp import reproject as warp_reproject, Resampling
from shapely.geometry import box as shapely_box, shape as shapely_shape
from shapely.ops import transform as shapely_transform

# Regex to extract a 4-digit year (19xx or 20xx) from a filename.
_REGEX_ANO = re.compile(r"(19|20)\d{2}")

# Used for geodesic area calculations when a CRS is geographic (degrees,
# e.g. EPSG:4326) — a planar shapely `.area` on lon/lat coordinates is in
# square degrees, not a real unit of area, and silently rounds to ~0 ha.
_GEOD = Geod(ellps="WGS84")


# -------- Geometry helpers --------


def _normalize_geometry(geometry: Dict[str, Any]) -> Dict[str, Any]:
    """Accept a GeoJSON Feature, FeatureCollection, or bare Geometry;
    return bare Geometry."""
    if not isinstance(geometry, dict):
        raise ValueError("geometry must be a dict (Feature, FeatureCollection, or Geometry)")
    gtype = geometry.get("type")
    if gtype == "Feature":
        if not geometry.get("geometry"):
            raise ValueError("Feature has no geometry")
        return geometry["geometry"]
    if gtype == "FeatureCollection":
        feats = geometry.get("features") or []
        if not feats:
            raise ValueError("FeatureCollection is empty")
        return feats[0]["geometry"]
    if gtype in (
        "Polygon", "MultiPolygon", "Point", "MultiPoint",
        "LineString", "MultiLineString", "GeometryCollection",
    ):
        return geometry
    raise ValueError(f"Unsupported GeoJSON type: {gtype}")


def _reproject_geometry(
    geom_geojson: Dict[str, Any],
    src_crs: str,
    dst_crs: str,
) -> Dict[str, Any]:
    """Reproject a GeoJSON geometry dict from src_crs to dst_crs."""
    if src_crs == dst_crs:
        return geom_geojson
    transformer = Transformer.from_crs(src_crs, dst_crs, always_xy=True)
    geom = shapely_shape(geom_geojson)
    reproj = shapely_transform(lambda x, y, z=None: transformer.transform(x, y), geom)
    return reproj.__geo_interface__


def _is_geographic(crs: str) -> bool:
    # Uses pyproj's own CRS (bundled PROJ data), not rasterio/GDAL's, to
    # avoid picking up a conflicting system-wide PROJ install.
    return CRS.from_user_input(crs).is_geographic


def _area_ha(geom_geojson: Dict[str, Any], crs: str) -> float:
    """
    Area (hectares) of a GeoJSON geometry, computed correctly regardless of
    whether ``crs`` is geographic (e.g. EPSG:4326, lon/lat degrees — a
    planar shapely ``.area`` there is in square degrees, not hectares, and
    rounds to ~0 for any real property) or projected (meters — planar
    ``.area / 10_000`` is valid).
    """
    geom = shapely_shape(geom_geojson)
    if _is_geographic(crs):
        area_m2, _ = _GEOD.geometry_area_perimeter(geom)
        return abs(area_m2) / 10_000.0
    return geom.area / 10_000.0


def _pixel_area_ha(transform: rasterio.Affine, crs: str, row: int, col: int) -> float:
    """
    Area (hectares) of one raster pixel at grid position (row, col).

    Uses geodesic calculation when ``crs`` is geographic — ground pixel
    area varies with latitude there, and ``pixel_width * pixel_height``
    (in degrees) is not a unit of area at all — otherwise falls back to
    the planar ``width * height / 10_000`` (valid for projected/meter CRSs).
    """
    if not _is_geographic(crs):
        return (abs(transform[0]) * abs(transform[4])) / 10_000.0

    x0, y0 = transform * (col, row)
    x1, y1 = transform * (col + 1, row + 1)
    pixel_box = shapely_box(min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1))
    area_m2, _ = _GEOD.geometry_area_perimeter(pixel_box)
    return abs(area_m2) / 10_000.0


# -------- Year extraction --------


def _extract_year(filename: str) -> Optional[int]:
    """Extract a 4-digit year (19xx/20xx) from a filename."""
    m = _REGEX_ANO.search(os.path.basename(filename))
    if m:
        return int(m.group(0))
    # Fallback: try all tokens after replacing underscores with dashes
    for token in os.path.basename(filename).replace("_", "-").split("-"):
        if token.isdigit() and len(token) == 4 and token.startswith(("19", "20")):
            return int(token)
    return None


def _clip_zone_raster(
    path: str,
    geom_geojson: Dict[str, Any],
    target_crs: str,
) -> Tuple[Optional[np.ndarray], Optional[float]]:
    """
    Clip a binary zone raster (APP or RL) to the property geometry.

    If the raster's CRS differs from ``target_crs``, a WarpedVRT is used to
    reproject on-the-fly before clipping.

    Returns ``(masked_data_2d, nodata_value)`` or ``(None, None)`` if the
    file does not exist or cannot be read.
    """
    if not os.path.isfile(path):
        return None, None

    with rasterio.open(path) as src:
        nodata_val = src.nodata
        src_crs_str = src.crs.to_string() if src.crs else ""

        if src_crs_str != target_crs:
            # Raster CRS differs from vegetation CRS — reproject on-the-fly
            vrt = WarpedVRT(src, crs=target_crs)
            try:
                chunk, _ = mask(vrt, [geom_geojson], crop=True)
            finally:
                vrt.close()
        else:
            chunk, _ = mask(src, [geom_geojson], crop=True)

    return chunk[0], nodata_val


def _resample_mask_to_grid(
    mask_arr: np.ndarray,
    src_shape: Tuple[int, int],
    src_transform: rasterio.Affine,
    src_crs: rasterio.crs.CRS,
    dst_shape: Tuple[int, int],
    dst_transform: rasterio.Affine,
    dst_crs: rasterio.crs.CRS,
) -> np.ndarray:
    """
    Resample a 2D boolean mask array from its source pixel grid to a
    destination pixel grid using nearest-neighbour interpolation.

    This is needed when the APP/RL rasters have a different pixel resolution
    than the vegetation rasters, even after CRS reprojection.
    """
    dst_data = np.zeros(dst_shape, dtype=mask_arr.dtype)
    warp_reproject(
        source=mask_arr,
        destination=dst_data,
        src_transform=src_transform,
        src_crs=src_crs,
        dst_transform=dst_transform,
        dst_crs=dst_crs,
        resampling=Resampling.nearest,
    )
    return dst_data


# -------- Excedente Florestal --------


def _compute_excedente_florestal(
    propriedade_rows: List[Dict[str, Any]],
    uniao_rows: Optional[List[Dict[str, Any]]],
) -> List[Dict[str, Any]]:
    """
    Per-year "Excedente Florestal": natural vegetation area in the whole
    property that exceeds the legally-protected APP ∪ RL area
    (propriedade.area_natural_ha - app_rl_uniao.area_natural_ha). The union
    (not APP + RL summed) is used so overlapping APP/RL natural vegetation
    isn't subtracted twice — see the module docstring.

    Rows share the same shape as the other zones (ano, area_natural_ha,
    area_nao_natural_ha, area_total_ha, pct_natural) so the client can reuse
    the same chart-building code: here "area_natural_ha" holds the surplus
    area and "pct_natural" the surplus as a % of the property's total area.

    Missing APP/RL data (``uniao_rows`` is None) is treated as 0 protected
    area, so the surplus falls back to the property's full natural area.
    """
    uniao_natural_by_year = {
        r["ano"]: r["area_natural_ha"] for r in (uniao_rows or [])
    }

    rows = []
    for r in propriedade_rows:
        total_ha = r["area_total_ha"]
        protegido_ha = uniao_natural_by_year.get(r["ano"], 0.0)
        excedente_ha = r["area_natural_ha"] - protegido_ha
        pct_excedente = (100 * excedente_ha / total_ha) if total_ha > 0 else None

        rows.append({
            "ano": r["ano"],
            "area_natural_ha": round(excedente_ha, 4),
            "area_nao_natural_ha": round(total_ha - excedente_ha, 4),
            "area_total_ha": total_ha,
            "pct_natural": round(pct_excedente, 4) if pct_excedente is not None else None,
        })
    return rows


# -------- Core algorithm --------


def compute_zonal_history(
    geometry: Dict[str, Any],
    raster_dir: str,
    classe_vegetacao: int = 1,
    input_crs: str = "EPSG:4326",
    path_app: Optional[str] = None,
    path_rl: Optional[str] = None,
    classes_naturais: Optional[Tuple[int, ...]] = None,
) -> Dict[str, Any]:
    """
    Compute per-year natural-vegetation statistics for a property, optionally
    restricted to APP and Reserva Legal zones.

    Returns a dict with keys ``propriedade``, ``app``, ``rl``, ``app_rl_uniao``,
    ``excedente_florestal``. Each value is a list of per-year dicts with fields:
        ano, pct_natural, area_natural_ha, area_nao_natural_ha, area_total_ha

    ``app_rl_uniao`` is the union of the APP and RL zone masks (not their
    sum) — APP and RL commonly overlap in practice (the Reserva Legal
    requirement can be met using APP area, per Art. 15 of Law 12.651/2012),
    so naively summing ``area_natural_ha`` from ``app`` and ``rl`` would
    double-count the overlapping natural vegetation.

    ``excedente_florestal`` is the "forest surplus": propriedade natural
    vegetation minus the legally-protected (``app_rl_uniao``) natural
    vegetation, per year — see ``_compute_excedente_florestal``.

    If ``path_app`` or ``path_rl`` is None (or the file does not exist), the
    corresponding key is set to None. ``app_rl_uniao`` is None only when
    both are unavailable, in which case ``excedente_florestal`` falls back to
    the property's full natural area (0 protected area assumed).

    ``classes_naturais`` is a tuple of integer class codes considered "natural"
    (default (1,)). When only ``classe_vegetacao`` is provided, it is used as
    a single-element tuple. This matches the v3 script's ``np.isin`` approach.
    """
    # If classes_naturais is not provided, derive from classe_vegetacao
    if classes_naturais is None:
        classes_naturais = (classe_vegetacao,)

    # ---- 1. Discover and sort vegetation rasters ----
    if not os.path.isdir(raster_dir):
        raise FileNotFoundError(f"Raster directory does not exist: {raster_dir}")

    raster_files_raw = glob.glob(os.path.join(raster_dir, "*.tif*"))
    raster_files = [
        f for f in raster_files_raw
        if os.path.splitext(f)[1].lower() in (".tif", ".tiff")
    ]
    if not raster_files:
        raise FileNotFoundError(f"No raster files (.tif/.tiff) in {raster_dir}")

    anos_arquivos: List[Tuple[int, str]] = []
    for f in raster_files:
        ano = _extract_year(f)
        if ano is None:
            continue
        anos_arquivos.append((ano, f))

    if not anos_arquivos:
        # Fallback: include all files even without parseable years
        anos_arquivos = [(0, f) for f in sorted(raster_files)]

    anos_arquivos.sort(key=lambda x: x[0])
    anos_lista = [a for a, _ in anos_arquivos]

    # Check for duplicate years
    seen = set()
    for a in anos_lista:
        if a in seen:
            raise ValueError(f"Duplicate year {a} detected in raster filenames.")
        seen.add(a)

    # ---- 2. Read CRS from first raster and reproject geometry ----
    with rasterio.open(anos_arquivos[0][1]) as src_ref:
        raster_crs = src_ref.crs.to_string() if src_ref.crs else "EPSG:4326"
        raster_crs_obj = src_ref.crs
        raster_bounds = src_ref.bounds
        nodata_ref = src_ref.nodata

    bare_geom = _normalize_geometry(geometry)
    area_geom_ha = _area_ha(bare_geom, input_crs)
    geom_geojson = _reproject_geometry(bare_geom, input_crs, raster_crs)

    # ---- 3. Clip APP and RL rasters (reprojecting if needed) ----
    app_available = path_app is not None and os.path.isfile(path_app)
    rl_available = path_rl is not None and os.path.isfile(path_rl)

    mask_app_raw, nodata_app = _clip_zone_raster(path_app, geom_geojson, raster_crs) if app_available else (None, None)
    mask_rl_raw, nodata_rl = _clip_zone_raster(path_rl, geom_geojson, raster_crs) if rl_available else (None, None)

    # ---- 4. Read each year, stack into 3D array ----
    bandas: List[np.ndarray] = []
    shape_ref = None
    transform_ref = None
    pixel_area_ha: Optional[float] = None

    for ano, caminho in anos_arquivos:
        with rasterio.open(caminho) as src_mb:
            if src_mb.crs and src_mb.crs.to_string() != raster_crs:
                raise ValueError(
                    f"CRS mismatch: '{os.path.basename(caminho)}' has "
                    f"{src_mb.crs}, expected {raster_crs}."
                )
            chunk_mb, transform_mb = mask(src_mb, [geom_geojson], crop=True)

        banda = chunk_mb[0]

        if shape_ref is None:
            shape_ref = banda.shape
            transform_ref = transform_mb
            pixel_area_ha = _pixel_area_ha(
                transform_mb, raster_crs, banda.shape[0] // 2, banda.shape[1] // 2
            )
        else:
            if banda.shape != shape_ref or not transform_mb.almost_equals(transform_ref, precision=1e-6):
                raise ValueError(
                    f"Grid mismatch: year {ano} does not match the reference grid."
                )

        bandas.append(banda)

    chunk_3d = np.stack(bandas, axis=0)  # (n_years, h, w)
    anos = np.array(anos_lista)
    assert shape_ref is not None
    assert transform_ref is not None
    assert pixel_area_ha is not None

    # ---- 5. Resample APP/RL masks to match the vegetation grid if needed ----
    mask_app: Optional[np.ndarray] = None
    area_total_app_ha: Optional[float] = None
    if mask_app_raw is not None:
        # Build boolean mask: pixel == 1 and not nodata
        app_bool = (mask_app_raw == 1)
        if nodata_app is not None:
            app_bool = app_bool & (mask_app_raw != nodata_app)

        if app_bool.shape != shape_ref:
            # Different resolution after reprojection — resample to match
            app_bool = _resample_mask_to_grid(
                app_bool.astype(np.uint8),
                app_bool.shape,
                transform_ref,
                raster_crs_obj,
                shape_ref,
                transform_ref,
                raster_crs_obj,
            ).astype(bool)

        mask_app = app_bool
        area_total_app_ha = float(mask_app.sum()) * pixel_area_ha

    mask_rl: Optional[np.ndarray] = None
    area_total_rl_ha: Optional[float] = None
    if mask_rl_raw is not None:
        rl_bool = (mask_rl_raw == 1)
        if nodata_rl is not None:
            rl_bool = rl_bool & (mask_rl_raw != nodata_rl)

        if rl_bool.shape != shape_ref:
            rl_bool = _resample_mask_to_grid(
                rl_bool.astype(np.uint8),
                rl_bool.shape,
                transform_ref,
                raster_crs_obj,
                shape_ref,
                transform_ref,
                raster_crs_obj,
            ).astype(bool)

        mask_rl = rl_bool
        area_total_rl_ha = float(mask_rl.sum()) * pixel_area_ha

    # ---- 5b. Union of APP + RL masks ----
    # APP and RL commonly overlap (see docstring). Summing area_natural_ha
    # from the two independent zones double-counts that overlap, so a
    # separate union zone is computed here for correct "forest surplus"
    # (protected-area) calculations.
    mask_union: Optional[np.ndarray] = None
    area_total_union_ha: Optional[float] = None
    if mask_app is not None or mask_rl is not None:
        if mask_app is not None and mask_rl is not None:
            mask_union = mask_app | mask_rl
        else:
            mask_union = mask_app if mask_app is not None else mask_rl
        area_total_union_ha = float(mask_union.sum()) * pixel_area_ha

    # ---- 6. Compute statistics ----
    # Valid pixels: not nodata
    valido_3d = np.ones_like(chunk_3d, dtype=bool)
    if nodata_ref is not None:
        valido_3d = valido_3d & (chunk_3d != nodata_ref)

    # Natural pixels: class matches one of classes_naturais and is valid
    natural_3d = np.isin(chunk_3d, classes_naturais) & valido_3d

    def _compute_zone(zone_mask: Optional[np.ndarray], total_area_ha: float) -> List[Dict[str, Any]]:
        """Compute per-year natural/total stats for a zone defined by a 2D mask.

        Args:
            zone_mask: 2D boolean mask for the zone, or None for the whole property.
            total_area_ha: Total area of the zone in hectares (constant per zone,
                not per-year). For Propriedade, this is the vector geometry area.
                For APP/RL, this is the mask pixel count × pixel area.
        """
        if zone_mask is not None:
            valido_zone = valido_3d & zone_mask
            natural_zone = natural_3d & zone_mask
        else:
            valido_zone = valido_3d
            natural_zone = natural_3d

        natural_ha = natural_zone.sum(axis=(1, 2)) * pixel_area_ha  # type: ignore[operator]
        nao_natural_ha = (valido_zone & ~natural_zone).sum(axis=(1, 2)) * pixel_area_ha  # type: ignore[operator]
        pct_natural = np.where(
            total_area_ha > 0,
            100 * natural_ha / total_area_ha,
            np.nan,
        )

        rows = []
        for i, ano in enumerate(anos):
            rows.append({
                "ano": int(ano) if ano != 0 else None,
                "area_natural_ha": round(float(natural_ha[i]), 4),
                "area_nao_natural_ha": round(float(nao_natural_ha[i]), 4),
                "area_total_ha": round(total_area_ha, 4),
                "pct_natural": round(float(pct_natural[i]), 4) if not np.isnan(pct_natural[i]) else None,
            })
        return rows

    # Propriedade (whole property) — area from vector geometry, matching v3
    result_propriedade = _compute_zone(None, area_geom_ha)

    # APP zone — area from mask pixel count
    result_app = _compute_zone(mask_app, area_total_app_ha) if mask_app is not None else None

    # RL zone — area from mask pixel count
    result_rl = _compute_zone(mask_rl, area_total_rl_ha) if mask_rl is not None else None

    # APP ∪ RL zone (deduplicated) — area from mask pixel count
    result_app_rl_uniao = (
        _compute_zone(mask_union, area_total_union_ha) if mask_union is not None else None
    )

    # Excedente Florestal — propriedade natural minus the legally-protected
    # (APP ∪ RL) natural area, per year
    result_excedente_florestal = _compute_excedente_florestal(
        result_propriedade, result_app_rl_uniao
    )

    return {
        "propriedade": result_propriedade,
        "app": result_app,
        "rl": result_rl,
        "app_rl_uniao": result_app_rl_uniao,
        "excedente_florestal": result_excedente_florestal,
    }