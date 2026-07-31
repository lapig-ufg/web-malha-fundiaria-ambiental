"""
Calcula, para as propriedades de um parquet de entrada -- todas, ou uma so
via --id-propriedade -- o deficit de APP, o deficit de Reserva Legal (RL) e
o excedente florestal.

Script AUTOCONTIDO: nao depende do resto do repositorio. compute_zonal_history()
e suas funcoes auxiliares (mais abaixo, na secao "compute_zonal_history e
auxiliares") sao uma copia direta de app/server/utils/zonal_statistics.py
(a mesma logica usada pela API em /service/zonal/jobs) -- se aquele arquivo
for atualizado, replique as mudancas aqui tambem.

Da pasta de rasters (--raster-dir, um .tif por ano), usa APENAS a imagem do
ANO MAIS RECENTE -- as demais nao sao lidas.

DESENHO PARA BAIXO USO DE RAM / ALTA CONCORRENCIA
------------------------------------------------------------------------
- O parquet de propriedades e lido em LOTES via pyarrow
  (ParquetFile.iter_batches, projetando so as colunas id/geometria), nunca
  como um GeoDataFrame inteiro -- geopandas nem e usado aqui.
- A geometria de cada propriedade trafega como WKB (bytes) ate o worker; a
  conversao para shapely/GeoJSON acontece DENTRO do processo worker, nao no
  processo principal.
- No maximo `--workers * 4` propriedades ficam "em voo" (submetidas mas
  ainda nao concluidas) a qualquer momento -- ao contrario de
  executor.submit() em loop fechado ou executor.map(), que enfileiram o
  iteravel inteiro de uma vez.
- O parquet de saida e escrito incrementalmente (pyarrow.ParquetWriter, a
  cada --flush-a-cada propriedades), entao os resultados tambem nao se
  acumulam inteiramente em memoria.

Com isso o pico de RAM do processo principal fica limitado a alguns lotes
de leitura + a fila em voo, independente do tamanho do dataset nacional.

Gera UMA LINHA POR PROPRIEDADE. Use --serie-completa para obter uma linha
por propriedade x zona (Propriedade/APP/Reserva_Legal/app_rl_uniao/
excedente_florestal) em vez do resumo com as colunas ja calculadas.

"Deficit" de uma zona (APP ou RL) e a parte da area delimitada dessa zona
que NAO tem cobertura de vegetacao natural no ano usado
(area_total_ha - area_natural_ha). "Excedente florestal" e a vegetacao
natural da propriedade que excede a area de APP-uniao-RL exigida
(ver docstring de compute_zonal_history).

Uso -- todas as propriedades (exemplo dimensionado para 96 nucleos / 1.2 TB RAM):
    uv run python deficit_rl_app_excedente_florestal.py \
        --parquet-propriedades data/balanco_passivo_ambiental_br_v5.parquet \
        --raster-dir /caminho/para/rasters_mapbiomas \
        --path-app /caminho/para/img_area_preservacao_permanente.tif \
        --path-rl /caminho/para/img_reserva_legal.tif \
        --output deficit_rl_app_por_propriedade.parquet \
        --workers 90 --lote-leitura 5000 --flush-a-cada 20000

Uso -- uma unica propriedade (roda sincrono, sem pool de processos, e
imprime o resultado no terminal alem de salvar o parquet):
    uv run python deficit_rl_app_excedente_florestal.py \
        --parquet-propriedades data/balanco_passivo_ambiental_br_v5.parquet \
        --raster-dir /caminho/para/rasters_mapbiomas \
        --path-app /caminho/para/img_area_preservacao_permanente.tif \
        --path-rl /caminho/para/img_reserva_legal.tif \
        --id-propriedade GO-5203203-B3F7BC3DC1FF4498A408F0458A482207 \
        --output deficit_uma_propriedade.parquet

Dependencias (instale no Python do servidor; nenhuma delas precisa do
resto do repositorio):
    pip install pandas pyarrow rasterio shapely pyproj numpy
"""
import argparse
import glob
import itertools
import json
import os
import re
import shutil
import tempfile
import time
from concurrent.futures import FIRST_COMPLETED, ProcessPoolExecutor, wait
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Tuple

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.dataset as ds
import pyarrow.parquet as pq
import rasterio
import shapely.wkb
from pyproj import CRS, Transformer
from rasterio.mask import mask
from rasterio.vrt import WarpedVRT
from rasterio.warp import Resampling
from rasterio.warp import reproject as warp_reproject
from shapely.geometry import shape as shapely_shape
from shapely.ops import transform as shapely_transform

_REGEX_ANO = re.compile(r"(19|20)\d{2}")


# -------- Cache de datasets rasterio por processo worker --------
# raster_dir/path_app/path_rl sao os MESMOS para todas as propriedades da
# execucao inteira -- sem isso, compute_zonal_history() reabriria os 3
# rasters (e reconstruiria o WarpedVRT de reprojecao, se o CRS de APP/RL
# for diferente do da vegetacao) do zero A CADA propriedade, o que domina
# o tempo de execucao em datasets de milhoes de linhas. Os dicts abaixo sao
# globais por PROCESSO (cada worker do ProcessPoolExecutor tem sua propria
# copia, populada sob demanda na primeira propriedade que processar, e
# reaproveitada ate o worker terminar).
_CACHE_RASTERS: Dict[str, "rasterio.DatasetReader"] = {}
_CACHE_VRTS: Dict[Tuple[str, str], "WarpedVRT"] = {}


def _open_cached(path: str) -> "rasterio.DatasetReader":
    ds = _CACHE_RASTERS.get(path)
    if ds is None or ds.closed:
        ds = rasterio.open(path)
        _CACHE_RASTERS[path] = ds
    return ds


def _open_cached_vrt(src: "rasterio.DatasetReader", path: str, target_crs: str) -> "WarpedVRT":
    chave = (path, target_crs)
    vrt = _CACHE_VRTS.get(chave)
    if vrt is None:
        vrt = WarpedVRT(src, crs=target_crs)
        _CACHE_VRTS[chave] = vrt
    return vrt


def _worker_init() -> None:
    """Roda uma vez por processo worker (ProcessPoolExecutor initializer).
    Aumenta o cache de blocos do GDAL (util com 1.2 TB de RAM disponiveis)
    e evita listagens de diretorio desnecessarias a cada open()."""
    rasterio.Env(
        GDAL_CACHEMAX=1024,  # MB por worker; ajuste conforme RAM/numero de workers
        GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR",
    ).__enter__()


# -------- compute_zonal_history e auxiliares --------
# Portados de app/server/utils/zonal_statistics.py para este script ser
# autocontido (o servidor onde ele roda nao tem o resto do repositorio), com
# duas mudancas deliberadas em relacao aquele modulo:
#   1. _open_cached()/_open_cached_vrt() em vez de rasterio.open()/WarpedVRT()
#      diretos -- datasets ficam abertos ate o worker terminar em vez de
#      fechados a cada chamada; nao muda nenhum numero, so I/O.
#   2. area_geom_ha e pixel_area_ha SEMPRE planares (sem correcao geodesica
#      para CRS geografico) -- igual a scripts/zonal_statistics_v3.py, de
#      proposito, para os dois scripts baterem exatamente. O modulo original
#      em app/server/utils/zonal_statistics.py faz correcao geodesica (mais
#      exata se o raster estiver em CRS geografico/graus); aqui foi trocado
#      por pedido explicito para reproduzir o v3.


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


def _pixel_area_ha(transform: rasterio.Affine) -> float:
    """Area (hectares) of one raster pixel -- planar, matching
    zonal_statistics_v3.py exactly (no geodesic correction for geographic
    CRSs). Valid as long as the raster's CRS is projected (meters); if it
    is geographic (degrees), this matches v3's calculation but is not a
    true real-world area."""
    return (abs(transform[0]) * abs(transform[4])) / 10_000.0


def _extract_year(filename: str) -> Optional[int]:
    """Extract a 4-digit year (19xx/20xx) from a filename."""
    m = _REGEX_ANO.search(os.path.basename(filename))
    if m:
        return int(m.group(0))
    for token in os.path.basename(filename).replace("_", "-").split("-"):
        if token.isdigit() and len(token) == 4 and token.startswith(("19", "20")):
            return int(token)
    return None


def _clip_zone_raster(
    path: str,
    geom_geojson: Dict[str, Any],
    target_crs: str,
) -> Tuple[Optional[np.ndarray], Optional[float]]:
    """Clip a binary zone raster (APP or RL) to the property geometry,
    reprojecting on-the-fly via WarpedVRT if its CRS differs from target_crs.
    Uses cached dataset/VRT handles (see _open_cached/_open_cached_vrt) --
    opened once per worker, reused across every propriedade."""
    if not os.path.isfile(path):
        return None, None

    src = _open_cached(path)
    nodata_val = src.nodata
    src_crs_str = src.crs.to_string() if src.crs else ""

    if src_crs_str != target_crs:
        vrt = _open_cached_vrt(src, path, target_crs)
        chunk, _ = mask(vrt, [geom_geojson], crop=True)
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
    """Resample a 2D boolean mask array to a destination pixel grid
    (nearest-neighbour), used when APP/RL rasters have a different
    resolution than the vegetation rasters even after CRS reprojection."""
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


def _compute_excedente_florestal(
    propriedade_rows: List[Dict[str, Any]],
    uniao_rows: Optional[List[Dict[str, Any]]],
) -> List[Dict[str, Any]]:
    """Per-year "Excedente Florestal": natural vegetation area in the whole
    property that exceeds the legally-protected APP union RL area."""
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

_COLUNAS_RESUMO = [
    "id_propriedade", "ano_referencia",
    "area_propriedade_ha", "area_natural_propriedade_ha", "pct_natural_propriedade",
    "area_app_ha", "area_natural_app_ha", "deficit_app_ha", "deficit_app_pct",
    "area_rl_ha", "area_natural_rl_ha", "deficit_rl_ha", "deficit_rl_pct",
    "excedente_florestal_ha", "excedente_florestal_pct",
    "status", "erro",
]

_COLUNAS_ZONA = [
    "id_propriedade", "zona", "ano",
    "area_natural_ha", "area_nao_natural_ha", "area_total_ha", "pct_natural",
    "status", "erro",
]

_COLUNAS_TEXTO = {"id_propriedade", "zona", "status", "erro"}
_COLUNAS_INTEIRAS = {"ano", "ano_referencia"}



def _dtype_para_coluna(nome: str) -> str:
    if nome in _COLUNAS_INTEIRAS:
        return "Int64"
    if nome in _COLUNAS_TEXTO:
        return "string"
    return "float64"


def _para_dataframe(linhas: List[Dict[str, Any]], colunas: List[str]) -> pd.DataFrame:
    df = pd.DataFrame(linhas, columns=colunas)
    for nome in colunas:
        df[nome] = df[nome].astype(_dtype_para_coluna(nome))
    return df


def _parse_classes_naturais(valor: str) -> Tuple[int, ...]:
    return tuple(int(c.strip()) for c in valor.split(",") if c.strip())


def _preparar_pasta_ultimo_ano(raster_dir: str) -> Tuple[str, int]:
    """Localiza o raster de ano mais recente em raster_dir e o copia (hardlink,
    com fallback para copia se o hardlink falhar, ex. volumes diferentes) para
    uma pasta temporaria isolada, para que compute_zonal_history() leia
    somente esse ano em vez da serie inteira."""
    origem = Path(raster_dir)
    candidatos = []
    for f in origem.glob("*.tif*"):
        if f.suffix.lower() not in (".tif", ".tiff"):
            continue
        m = _REGEX_ANO.search(f.name)
        if m:
            candidatos.append((int(m.group(0)), f))

    if not candidatos:
        raise SystemExit(f"Nenhum raster com ano reconhecivel (19xx/20xx no nome) em {raster_dir}.")

    ano, arquivo = max(candidatos, key=lambda item: item[0])

    tmp_dir = Path(tempfile.mkdtemp(prefix="raster_ultimo_ano_"))
    destino = tmp_dir / arquivo.name
    try:
        os.link(arquivo, destino)
    except OSError:
        shutil.copy2(arquivo, destino)

    return str(tmp_dir), ano


def _ler_crs_geoparquet(parquet_path: str, geom_coluna: str) -> str:
    """Le o CRS da geometria a partir do metadado GeoParquet (chave 'geo' no
    schema do parquet), sem carregar nenhuma linha/geometria em memoria."""
    schema = pq.read_schema(parquet_path)
    geo_meta = (schema.metadata or {}).get(b"geo")
    if not geo_meta:
        raise SystemExit(
            f"'{parquet_path}' nao tem metadado GeoParquet ('geo'); nao foi possivel "
            f"determinar o CRS automaticamente. Reescreva o parquet com "
            f"geopandas.GeoDataFrame.to_parquet() (formato GeoParquet padrao)."
        )
    info = json.loads(geo_meta.decode("utf-8"))
    colunas_geo = info.get("columns", {})
    if geom_coluna not in colunas_geo:
        raise SystemExit(
            f"Coluna de geometria '{geom_coluna}' nao esta no metadado GeoParquet de "
            f"'{parquet_path}'. Colunas de geometria disponiveis: {list(colunas_geo)}"
        )
    crs = colunas_geo[geom_coluna].get("crs")
    if crs is None:
        return "EPSG:4326"  # GeoParquet: crs ausente == OGC:CRS84
    if isinstance(crs, dict):
        return CRS.from_json_dict(crs).to_wkt()
    return str(crs)

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
    src_ref = _open_cached(anos_arquivos[0][1])
    raster_crs = src_ref.crs.to_string() if src_ref.crs else "EPSG:4326"
    raster_crs_obj = src_ref.crs
    raster_bounds = src_ref.bounds
    nodata_ref = src_ref.nodata

    bare_geom = _normalize_geometry(geometry)
    geom_geojson = _reproject_geometry(bare_geom, input_crs, raster_crs)
    # Area planar sobre a geometria ja reprojetada pro CRS do raster --
    # igual a zonal_statistics_v3.py (geom_reproj.area / 10_000.0), em vez
    # do calculo geodesico no CRS original de entrada.
    area_geom_ha = shapely_shape(geom_geojson).area / 10_000.0

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
        src_mb = _open_cached(caminho)
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
            pixel_area_ha = _pixel_area_ha(transform_mb)
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
        # total_area_ha e um escalar (constante por zona, nao por ano) -- um
        # if/else evita a divisao por zero quando a zona (ex. RL/APP) nao
        # tem area alguma dentro da propriedade, sem depender do np.where
        # descartar um resultado invalido ja calculado (o que dispara
        # RuntimeWarning: invalid value encountered in divide).
        if total_area_ha > 0:
            pct_natural = 100 * natural_ha / total_area_ha
        else:
            pct_natural = np.full(natural_ha.shape, np.nan)

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


def _iter_propriedades(
    parquet_path: str, id_coluna: str, geom_coluna: str, tamanho_lote: int, limit: Optional[int],
) -> Iterator[Tuple[Any, Optional[bytes]]]:
    """Le o parquet em lotes via pyarrow, projetando so id + geometria --
    nunca materializa o dataset inteiro (nem como GeoDataFrame, nem como
    lista) em memoria."""
    pf = pq.ParquetFile(parquet_path)
    colunas_disponiveis = pf.schema_arrow.names
    for coluna in (id_coluna, geom_coluna):
        if coluna not in colunas_disponiveis:
            raise SystemExit(f"Coluna '{coluna}' nao encontrada no parquet. Colunas disponiveis: {colunas_disponiveis}")

    emitidas = 0
    for lote in pf.iter_batches(batch_size=tamanho_lote, columns=[id_coluna, geom_coluna]):
        ids = lote.column(id_coluna).to_pylist()
        geoms = lote.column(geom_coluna).to_pylist()
        for id_propriedade, geom_wkb in zip(ids, geoms):
            yield id_propriedade, geom_wkb
            emitidas += 1
            if limit and emitidas >= limit:
                return


def _buscar_propriedade_unica(
    parquet_path: str, id_coluna: str, geom_coluna: str, id_valor: str,
) -> Tuple[Any, bytes]:
    """Busca uma unica propriedade pelo ID via predicate pushdown do pyarrow
    (nao escaneia o parquet inteiro linha a linha, ao contrario de
    _iter_propriedades) -- usado no modo --id-propriedade."""
    dataset = ds.dataset(parquet_path, format="parquet")
    if id_coluna not in dataset.schema.names or geom_coluna not in dataset.schema.names:
        raise SystemExit(
            f"Coluna '{id_coluna}' ou '{geom_coluna}' nao encontrada no parquet. "
            f"Colunas disponiveis: {dataset.schema.names}"
        )
    tabela = dataset.to_table(columns=[id_coluna, geom_coluna], filter=ds.field(id_coluna) == id_valor)
    if tabela.num_rows == 0:
        raise SystemExit(f"Propriedade '{id_valor}' nao encontrada na coluna '{id_coluna}' de {parquet_path}.")
    if tabela.num_rows > 1:
        print(f"[ALERTA] {tabela.num_rows} linha(s) encontradas para '{id_valor}'; usando a primeira.")
    return tabela.column(id_coluna)[0].as_py(), tabela.column(geom_coluna)[0].as_py()


def _linha_resumo(id_propriedade: Any, resultado: Dict[str, Any]) -> Dict[str, Any]:
    """Reduz o resultado (um unico ano, ja filtrado por _preparar_pasta_ultimo_ano)
    a uma linha, com deficit de APP/RL e excedente florestal ja calculados."""
    prop_rows = resultado["propriedade"]
    if not prop_rows:
        raise ValueError("compute_zonal_history nao retornou nenhum ano.")

    prop = prop_rows[-1]
    app = resultado["app"][-1] if resultado["app"] else None
    rl = resultado["rl"][-1] if resultado["rl"] else None
    excedente = resultado["excedente_florestal"][-1] if resultado["excedente_florestal"] else None

    return {
        "id_propriedade": id_propriedade,
        "ano_referencia": prop["ano"],
        "area_propriedade_ha": prop["area_total_ha"],
        "area_natural_propriedade_ha": prop["area_natural_ha"],
        "pct_natural_propriedade": prop["pct_natural"],
        "area_app_ha": app["area_total_ha"] if app else None,
        "area_natural_app_ha": app["area_natural_ha"] if app else None,
        "deficit_app_ha": app["area_nao_natural_ha"] if app else None,
        "deficit_app_pct": (100 - app["pct_natural"]) if app and app["pct_natural"] is not None else None,
        "area_rl_ha": rl["area_total_ha"] if rl else None,
        "area_natural_rl_ha": rl["area_natural_ha"] if rl else None,
        "deficit_rl_ha": rl["area_nao_natural_ha"] if rl else None,
        "deficit_rl_pct": (100 - rl["pct_natural"]) if rl and rl["pct_natural"] is not None else None,
        "excedente_florestal_ha": excedente["area_natural_ha"] if excedente else None,
        "excedente_florestal_pct": excedente["pct_natural"] if excedente else None,
        "status": "ok",
        "erro": None,
    }


def _linhas_por_zona(id_propriedade: Any, resultado: Dict[str, Any]) -> List[Dict[str, Any]]:
    linhas = []
    for zona, rows in resultado.items():
        for r in rows or []:
            linhas.append({"id_propriedade": id_propriedade, "zona": zona, **r, "status": "ok", "erro": None})
    return linhas


def _processar_propriedade(
    id_propriedade: Any,
    geom_wkb: bytes,
    input_crs: str,
    raster_dir: str,
    path_app: Optional[str],
    path_rl: Optional[str],
    classes_naturais: Tuple[int, ...],
    serie_completa: bool,
) -> List[Dict[str, Any]]:
    """Roda inteiramente dentro do processo worker: decodifica o WKB,
    chama compute_zonal_history() e reduz o resultado a linha(s) de saida --
    nada disso volta a trafegar entre processos alem do resultado final."""
    try:
        geom = shapely.wkb.loads(geom_wkb)
        if geom is None or geom.is_empty:
            raise ValueError("geometria nula/vazia")
        if not geom.is_valid:
            geom = geom.buffer(0)

        resultado = compute_zonal_history(
            geometry=geom.__geo_interface__,
            raster_dir=raster_dir,
            input_crs=input_crs,
            path_app=path_app,
            path_rl=path_rl,
            classes_naturais=classes_naturais,
        )
    except Exception as exc:  # noqa: BLE001
        return [{"id_propriedade": id_propriedade, "status": "erro", "erro": f"{type(exc).__name__}: {exc}"}]

    if serie_completa:
        return _linhas_por_zona(id_propriedade, resultado)
    return [_linha_resumo(id_propriedade, resultado)]


def _mapear_com_limite(executor: ProcessPoolExecutor, fn, args_iter: Iterator[tuple], limite: int):
    """Envia tarefas ao executor mantendo no maximo `limite` em voo ao mesmo
    tempo, devolvendo cada resultado assim que fica pronto. Ao contrario de
    executor.map()/submit() em loop fechado -- que enfileiram o iteravel
    inteiro de uma vez -- isso mantem o pico de memoria ligado a `limite`,
    nao ao tamanho do dataset."""
    args_iter = iter(args_iter)
    em_voo = {executor.submit(fn, *args): None for args in itertools.islice(args_iter, limite)}

    while em_voo:
        concluidos, _ = wait(em_voo.keys(), return_when=FIRST_COMPLETED)
        for futuro in concluidos:
            del em_voo[futuro]
            yield futuro
            prox = next(args_iter, None)
            if prox is not None:
                em_voo[executor.submit(fn, *prox)] = None


def main() -> None:
    n_workers_default = max(1, (os.cpu_count() or 4) - 2)

    parser = argparse.ArgumentParser(
        description="Calcula deficit de APP, deficit de Reserva Legal e excedente florestal por propriedade "
                     "(streaming, baixo uso de RAM), usando apenas o ano mais recente da pasta de rasters."
    )
    parser.add_argument("--parquet-propriedades", required=True, help="Parquet (GeoParquet) com geometrias individuais das propriedades.")
    parser.add_argument("--id-propriedade", default=None, help="Processa APENAS esta propriedade (valor exato da coluna --id-coluna), em vez do parquet inteiro. Sem esta opcao, processa todas.")
    parser.add_argument("--id-coluna", default="landternure_code", help="Coluna de ID da propriedade (default: landternure_code).")
    parser.add_argument("--geom-coluna", default="geometry", help="Coluna de geometria no parquet (default: geometry).")
    parser.add_argument("--raster-dir", required=True, help="Pasta com a serie temporal de rasters de cobertura vegetal (um .tif por ano); so o ano mais recente e usado.")
    parser.add_argument("--path-app", default=None, help="Raster binario da APP delimitada da propriedade.")
    parser.add_argument("--path-rl", default=None, help="Raster binario da Reserva Legal delimitada da propriedade.")
    parser.add_argument("--classes-naturais", default="1", help="Codigos de classe considerados vegetacao natural, separados por virgula (default: 1).")
    parser.add_argument("--output", default="deficit_rl_app_por_propriedade.parquet", help="Caminho do parquet de saida.")
    parser.add_argument("--serie-completa", action="store_true", help="Gera uma linha por propriedade x zona, em vez do resumo com as colunas ja calculadas.")
    parser.add_argument("--workers", type=int, default=n_workers_default, help=f"Processos paralelos (default: nucleos disponiveis - 2 = {n_workers_default}).")
    parser.add_argument("--lote-leitura", type=int, default=2000, help="Propriedades lidas do parquet por vez (controla o pico de RAM do processo principal; default: 2000).")
    parser.add_argument("--flush-a-cada", type=int, default=5000, help="Propriedades processadas entre cada gravacao incremental no parquet de saida (default: 5000).")
    parser.add_argument("--limit", type=int, default=None, help="Processa apenas as N primeiras propriedades (para teste).")
    args = parser.parse_args()

    classes_naturais = _parse_classes_naturais(args.classes_naturais)
    colunas = _COLUNAS_ZONA if args.serie_completa else _COLUNAS_RESUMO

    raster_dir_filtrado, ano_usado = _preparar_pasta_ultimo_ano(args.raster_dir)
    print(f"[-] Ano mais recente encontrado em {args.raster_dir}: {ano_usado} (usando apenas esse raster).")
    print(f"[-] workers={args.workers} lote-leitura={args.lote_leitura} flush-a-cada={args.flush_a_cada}")

    try:
        input_crs = _ler_crs_geoparquet(args.parquet_propriedades, args.geom_coluna)
        print(f"[-] CRS de entrada (metadado GeoParquet): {input_crs}")

        # -------- Modo uma unica propriedade --------
        # Sincrono, sem ProcessPoolExecutor (nao vale a pena o overhead de
        # subir um pool de workers para processar uma linha so).
        if args.id_propriedade is not None:
            _worker_init()
            id_propriedade, geom_wkb = _buscar_propriedade_unica(
                args.parquet_propriedades, args.id_coluna, args.geom_coluna, args.id_propriedade,
            )
            print(f"[-] Propriedade encontrada: {id_propriedade!r}. Calculando...")
            inicio = time.time()
            linhas = _processar_propriedade(
                id_propriedade, geom_wkb, input_crs, raster_dir_filtrado,
                args.path_app, args.path_rl, classes_naturais, args.serie_completa,
            )
            df = _para_dataframe(linhas, colunas)
            pd.set_option("display.max_columns", None)
            pd.set_option("display.width", 200)
            print(df.to_string(index=False))
            df.to_parquet(args.output, index=False)
            n_erros = int((df["status"] == "erro").sum())
            print(f"\n[OK] {len(df)} linha(s) salvas em {args.output} ({n_erros} propriedade(s) com erro).")
            print(f"[-] Tempo total: {time.time() - inicio:.1f}s")
            return

        # -------- Modo todas as propriedades --------
        # Contagem de linhas vem do rodape do parquet (metadado), sem ler
        # nenhuma linha/geometria -- so para calcular a % de progresso.
        total_estimado = pq.ParquetFile(args.parquet_propriedades).metadata.num_rows
        if args.limit:
            total_estimado = min(total_estimado, args.limit)
        print(f"[-] Total estimado de propriedades: {total_estimado}")

        buffer: List[Dict[str, Any]] = []
        writer: Optional[pq.ParquetWriter] = None
        n_linhas = 0
        n_erros = 0
        processadas = 0
        inicio = time.time()

        def _flush() -> None:
            nonlocal writer, n_linhas, n_erros
            if not buffer:
                return
            df = _para_dataframe(buffer, colunas)
            tabela = pa.Table.from_pandas(df, preserve_index=False)
            if writer is None:
                writer = pq.ParquetWriter(args.output, tabela.schema)
            writer.write_table(tabela)
            n_linhas += len(buffer)
            n_erros += int((df["status"] == "erro").sum())
            buffer.clear()

        def _log_progresso() -> None:
            decorrido = time.time() - inicio
            taxa = processadas / decorrido if decorrido > 0 else 0.0
            pct = (100 * processadas / total_estimado) if total_estimado else 100.0
            if taxa > 0 and total_estimado > processadas:
                eta_min = (total_estimado - processadas) / taxa / 60
                eta_txt = f"ETA {eta_min:.1f} min"
            else:
                eta_txt = "ETA --"
            print(f"[-] {processadas}/{total_estimado} ({pct:.1f}%) | {taxa:.1f} propriedades/s | {eta_txt}")

        fonte = _iter_propriedades(args.parquet_propriedades, args.id_coluna, args.geom_coluna, args.lote_leitura, args.limit)

        def _gerar_argumentos():
            nonlocal processadas
            for id_propriedade, geom_wkb in fonte:
                if geom_wkb is None:
                    buffer.append({"id_propriedade": id_propriedade, "status": "erro", "erro": "geometria nula/vazia"})
                    processadas += 1
                    continue
                yield (
                    id_propriedade, geom_wkb, input_crs, raster_dir_filtrado,
                    args.path_app, args.path_rl, classes_naturais, args.serie_completa,
                )

        with ProcessPoolExecutor(max_workers=args.workers, initializer=_worker_init) as executor:
            for futuro in _mapear_com_limite(executor, _processar_propriedade, _gerar_argumentos(), limite=args.workers * 4):
                buffer.extend(futuro.result())
                processadas += 1
                if processadas % 500 == 0:
                    _log_progresso()
                if len(buffer) >= args.flush_a_cada:
                    _flush()

        _flush()
        if writer is not None:
            writer.close()

        _log_progresso()
        print(f"\n[OK] {n_linhas} linha(s) salvas em {args.output} ({n_erros} propriedade(s) com erro).")
        print(f"[-] Tempo total: {time.time() - inicio:.1f}s")
    finally:
        shutil.rmtree(raster_dir_filtrado, ignore_errors=True)


if __name__ == "__main__":
    main()
