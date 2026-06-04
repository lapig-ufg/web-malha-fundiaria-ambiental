"""
Per-property vegetation zonal statistics.

Ported from scripts/zonal_statistics.py (functions
``criar_matriz_codificada_temporal`` and ``pipeline_raster_codificado``).
The script's ``__main__`` block is dropped — the server receives the
property geometry from the client, not from a parquet file.
"""
import glob
import os
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import rasterio
from pyproj import Transformer
from rasterio.mask import mask
from shapely.geometry import shape as shapely_shape
from shapely.ops import transform as shapely_transform


# -------- Geometry helpers --------

def _normalize_geometry(geometry: Dict[str, Any]) -> Dict[str, Any]:
    """Accept a GeoJSON Feature, FeatureCollection, or bare Geometry; return bare Geometry."""
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


# -------- Core algorithm (ported from scripts/zonal_statistics.py) --------

def _build_bitpacked_matrix(
    raster_files: List[str],
    geom_geojson_in_raster_crs: Dict[str, Any],
    classe_vegetacao: int,
) -> Tuple[np.ndarray, float, Optional[float]]:
    """
    Port of ``criar_matriz_codificada_temporal``.

    Returns ``(matrix_int64, area_pixel_m2, nodata_value)``.
    """
    matriz_codificada_final: Optional[np.ndarray] = None
    pixel_size_x: Optional[float] = None
    pixel_size_y: Optional[float] = None
    nodata_val: Optional[float] = None

    for idx, img_path in enumerate(raster_files):
        with rasterio.open(img_path) as src:
            imagem_recortada, transform = mask(src, [geom_geojson_in_raster_crs], crop=True)

            if pixel_size_x is None:
                pixel_size_x = abs(transform[0])
                pixel_size_y = abs(transform[4])
                nodata_val = src.nodata

            banda = imagem_recortada[0]

            mascara_veg = (banda == classe_vegetacao)
            if nodata_val is not None:
                mascara_veg &= (banda != nodata_val)

            peso_do_ano = 1 << idx

            if matriz_codificada_final is None:
                matriz_codificada_final = np.zeros_like(banda, dtype=np.int64)

            matriz_codificada_final[mascara_veg] += peso_do_ano

    area_pixel = (pixel_size_x or 0.0) * (pixel_size_y or 0.0)
    return matriz_codificada_final, area_pixel, nodata_val


def compute_zonal_history(
    geometry: Dict[str, Any],
    raster_dir: str,
    classe_vegetacao: int = 1,
    input_crs: str = "EPSG:4326",
) -> List[Dict[str, Any]]:
    """
    Port of ``pipeline_raster_codificado``, but the geometry is passed in
    directly (no parquet lookup).

    Returns a list of dicts, one per raster file in ``raster_dir``, with the
    per-year vegetation statistics plus the property total area and the
    percentage of vegetation cover.

    Each row:
        {
            "ano_arquivo": "brazil_coverage_1985_reclassificado",
            "ano": 1985,                                 # parsed from filename
            "area_vegetacao_natural_ha": float,
            "pixels_contados": int,
            "total_pixels_mask": int,
            "area_total_ha": float,
            "percent_vegetacao": float,                  # 0-100
        }
    """
    if not os.path.isdir(raster_dir):
        raise FileNotFoundError(f"Raster directory does not exist: {raster_dir}")

    raster_files = sorted(glob.glob(os.path.join(raster_dir, "*.tif*")))
    if not raster_files:
        raise FileNotFoundError(f"No raster files (.tif/.tiff) in {raster_dir}")

    # Read the raster CRS dynamically from the first file (no hard-coding).
    with rasterio.open(raster_files[0]) as src:
        raster_crs = src.crs.to_string() if src.crs else "EPSG:4326"

    bare_geom = _normalize_geometry(geometry)
    reproj_geom = _reproject_geometry(bare_geom, input_crs, raster_crs)

    matrix, area_pixel, nodata_val = _build_bitpacked_matrix(
        raster_files, reproj_geom, classe_vegetacao
    )

    anos_mapeados = [
        os.path.basename(f).replace(".tif", "").replace(".tiff", "")
        for f in raster_files
    ]

    total_pixels_mask = int(matrix.size)

    resultados: List[Dict[str, Any]] = []
    for idx, ano_nome in enumerate(anos_mapeados):
        peso_do_ano = 1 << idx
        pixels_do_ano = (matrix & peso_do_ano) > 0
        if nodata_val is not None:
            pixels_do_ano &= (matrix != nodata_val)

        total_pixels = int(np.sum(pixels_do_ano))
        area_hectares = (total_pixels * area_pixel) / 10_000.0
        area_total_ha = (total_pixels_mask * area_pixel) / 10_000.0
        percent = (total_pixels / total_pixels_mask * 100.0) if total_pixels_mask else 0.0

        # Parse the year from the filename (best-effort).
        ano_int: Optional[int] = None
        for token in ano_nome.replace("_", "-").split("-"):
            if token.isdigit() and len(token) == 4 and token.startswith(("19", "20")):
                ano_int = int(token)
                break

        resultados.append({
            "ano_arquivo": ano_nome,
            "ano": ano_int,
            "area_vegetacao_natural_ha": float(area_hectares),
            "pixels_contados": total_pixels,
            "total_pixels_mask": total_pixels_mask,
            "area_total_ha": float(area_total_ha),
            "percent_vegetacao": float(percent),
        })

    return resultados
