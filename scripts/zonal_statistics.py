import os
import re
import glob

import geopandas as gpd
import numpy as np
import rasterio
from rasterio.mask import mask
import pandas as pd
import datetime

_REGEX_ANO = re.compile(r"(19|20)\d{2}")


def _extrair_ano_do_nome(caminho_arquivo):
    """Extrai o ano (4 dígitos, 19xx/20xx) do nome do arquivo via regex."""
    m = _REGEX_ANO.search(os.path.basename(caminho_arquivo))
    if not m:
        raise ValueError(
            f"Não foi possível extrair um ano do nome '{os.path.basename(caminho_arquivo)}'. "
            f"Renomeie o arquivo incluindo o ano (ex.: 'brazil_coverage_1985.tif')."
        )
    return int(m.group(0))


def _validar_geometria(propriedade, id_propriedade, raster_crs, raster_bounds, parquet_path):
    """Valida e reprojeta a geometria da propriedade para o CRS do raster."""
    geom = propriedade.geometry.iloc[0]

    if geom is None or geom.is_empty:
        raise ValueError(f"A propriedade {id_propriedade} tem geometria NULA ou VAZIA.")

    if not geom.is_valid:
        print(f"[ALERTA] Geometria de {id_propriedade} inválida. Corrigindo com buffer(0)...")
        propriedade = propriedade.copy()
        propriedade["geometry"] = propriedade.geometry.buffer(0)
        geom = propriedade.geometry.iloc[0]
        if geom.is_empty:
            raise ValueError(f"Não foi possível corrigir a geometria de {id_propriedade}.")

    if propriedade.crs is None:
        raise ValueError(f"O parquet '{parquet_path}' não tem CRS definido.")

    geom_reproj = propriedade.to_crs(raster_crs).geometry.iloc[0]
    xmin, ymin, xmax, ymax = geom_reproj.bounds

    if not all(np.isfinite([xmin, ymin, xmax, ymax])):
        raise ValueError(f"Geometria de {id_propriedade} ficou com coordenadas NaN/inf após reprojetar.")

    if (xmax < raster_bounds.left or xmin > raster_bounds.right or
            ymax < raster_bounds.bottom or ymin > raster_bounds.top):
        raise ValueError(
            f"Geometria de {id_propriedade} NÃO INTERSECTA a extensão do raster.\n"
            f"  Propriedade: ({xmin:.2f}, {ymin:.2f}, {xmax:.2f}, {ymax:.2f})\n"
            f"  Raster:      ({raster_bounds.left:.2f}, {raster_bounds.bottom:.2f}, "
            f"{raster_bounds.right:.2f}, {raster_bounds.top:.2f})"
        )

    return geom_reproj


def pipeline_raster_codificado(parquet_path, id_propriedade, raster_dir, classe_vegetacao=1):
    """
    Calcula a área natural por ano lendo diretamente as imagens originais.
    Sem codificação bitwise — o cálculo é feito pixel a pixel nas imagens originais,
    de forma vetorizada via np.stack + np.isin.
    """
    print(f"[-] Carregando GeoParquet e localizando a propriedade ID: {id_propriedade}...")
    gdf = gpd.read_parquet(parquet_path)

    if 'landternure_code' not in gdf.columns:
        gdf['landternure_code'] = gdf.index

    propriedade = gdf[gdf['landternure_code'] == id_propriedade]
    if propriedade.empty:
        raise ValueError(f"Propriedade com o ID {id_propriedade} não foi encontrada.")
    if len(propriedade) > 1:
        print(f"[ALERTA] {len(propriedade)} linhas para {id_propriedade}; usando a primeira.")

    # 1) Coletar arquivos e ordenar pelo ano extraído do nome
    raster_files_raw = glob.glob(os.path.join(raster_dir, "*.tif"))
    raster_files = [
        f for f in raster_files_raw
        if os.path.splitext(f)[1].lower() in (".tif", ".tiff")
    ]
    if not raster_files:
        raise FileNotFoundError(
            f"Nenhum raster {(".tif", ".tiff")} encontrado em:\n{raster_dir}"
        )

    arquivos_anos = sorted(
        ((_extrair_ano_do_nome(f), f) for f in raster_files), key=lambda x: x[0]
    )
    anos_lista = [a for a, _ in arquivos_anos]
    if len(set(anos_lista)) != len(anos_lista):
        repetidos = sorted({a for a in anos_lista if anos_lista.count(a) > 1})
        raise ValueError(f"Anos duplicados nos nomes de arquivo: {repetidos}.")

    print(f"[-] {len(arquivos_anos)} arquivos → anos {anos_lista[0]} a {anos_lista[-1]}.")

    # 2) CRS e bounds de referência = primeiro raster da série
    with rasterio.open(arquivos_anos[0][1]) as src_ref:
        raster_crs    = src_ref.crs
        raster_bounds = src_ref.bounds
        nodata_ref    = src_ref.nodata

    # 3) Validar e reprojetar geometria da propriedade
    geom_reproj  = _validar_geometria(
        propriedade, id_propriedade, raster_crs, raster_bounds, parquet_path
    )
    geom_geojson = geom_reproj.__geo_interface__
    print(f"[-] Área vetorial da propriedade: {geom_reproj.area / 10_000:.2f} ha")

    # 4) Ler cada imagem original, recortar NO POLÍGONO EXATO da propriedade
    #    mask() com invert=False retorna (dados, transform) onde pixels FORA do
    #    polígono recebem o valor nodata. Usamos também a máscara booleana
    #    (indexes=1 retorna a máscara junto) para delimitar exatamente quais
    #    pixels estão dentro da propriedade — isso é o que o MapBiomas faz.
    print(f"[-] Lendo {len(arquivos_anos)} imagens originais e recortando na propriedade...")
    bandas, mascaras_dentro, pixel_area_ha = [], [], None

    for ano, caminho in arquivos_anos:
        with rasterio.open(caminho) as src:
            if src.crs != raster_crs:
                raise ValueError(
                    f"CRS inconsistente: '{os.path.basename(caminho)}' tem {src.crs}, "
                    f"esperado {raster_crs}."
                )
            # filled=False retorna um MaskedArray onde pixels fora do polígono
            # ficam mascarados — garante que só pixels DENTRO da propriedade entram no cálculo
            chunk_masked, transform = mask(
                src, [geom_geojson], crop=True, filled=False
            )

        if pixel_area_ha is None:
            pixel_area_ha = (abs(transform[0]) * abs(transform[4])) / 10_000.0
            #pixel_area_ha = (30 * 30) / 10_000.0
           
        # chunk_masked[0] é MaskedArray: .data = valores, .mask = True fora do polígono
        bandas.append(chunk_masked[0].data)
        mascaras_dentro.append(~chunk_masked[0].mask)  # True = dentro do polígono

    # 5) Empilhar em array 3D (n_anos, h, w)
    chunk_3d   = np.stack(bandas,         axis=0)  # valores originais MapBiomas
    dentro_3d  = np.stack(mascaras_dentro, axis=0)  # True = pixel dentro da propriedade
    anos       = np.array(anos_lista)

    # 6) Cálculo vetorizado nas imagens ORIGINAIS
    print(f"[-] Calculando área natural para {len(anos)} anos nas imagens originais...")

    # Pixel válido = dentro do polígono E não é nodata
    valido_3d = dentro_3d.copy()
    if nodata_ref is not None:
        valido_3d &= (chunk_3d != nodata_ref)

    # Pixels com classe natural dentro do polígono exato
    natural_3d = np.isin(chunk_3d, (1,)) & valido_3d

    # Área: denominador agora é apenas os pixels DENTRO da propriedade
    total_valido_ha = valido_3d.sum(axis=(1, 2))  * pixel_area_ha
    natural_ha      = natural_3d.sum(axis=(1, 2)) * pixel_area_ha
    nao_natural_ha  = total_valido_ha - natural_ha
    pct_natural     = np.where(
        total_valido_ha > 0, 100 * natural_ha / total_valido_ha, np.nan
    )

    df = pd.DataFrame({
        "ano_arquivo": anos,
        "area_vegetacao_natural_ha": np.round(natural_ha,      4),
        #"area_nao_natural_ha":       np.round(nao_natural_ha,  4),
        #"area_total_ha":             np.round(total_valido_ha, 4),
        #"pct_natural":               np.round(pct_natural,     4),
        "pixels_contados":           natural_3d.sum(axis=(1, 2)).astype(int),
    })

    return df.reset_index(drop=True)

# NOTE: the __main__ block has been removed. The canonical implementation
# lives at app/server/utils/zonal_statistics.py (compute_zonal_history) and
# is invoked via the /service/zonal/jobs endpoint. The scripts folder will
# be deleted in production.
