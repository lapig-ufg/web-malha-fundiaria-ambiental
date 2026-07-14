"""
zonal_area_natural_propriedade_app_rl_pasta.py
==============================================================================
Calcula a AREA NATURAL e NAO NATURAL dentro de UMA PROPRIEDADE, por ano,
separadamente para PROPRIEDADE INTEIRA, APP e RESERVA LEGAL -- lendo os
anos do MapBiomas a partir de ARQUIVOS .tif SEPARADOS EM UMA PASTA (nao
de um VRT), com o mesmo calculo VETORIZADO da versao com VRT.

DIFERENCA EM RELACAO A VERSAO COM VRT
------------------------------------------------------------------------
Um VRT multibanda GARANTE, por construcao, que todas as "bandas" (anos)
compartilham o mesmo CRS/resolucao/origem de pixel, e ja entrega um unico
array 3D pronto para o calculo vetorizado. Com arquivos .tif separados,
essa garantia nao existe -- este script recria isso explicitamente:

1. EXTRACAO ROBUSTA DO ANO: o ano e extraido do NOME do arquivo via regex
   (primeiro numero de 4 digitos 19xx/20xx), nao pela ordem alfabetica do
   glob -- evita a serie sair fora de ordem com nomenclatura inconsistente.
2. VALIDACAO DE CRS EM TODOS OS ARQUIVOS (serie + APP + RL) contra uma
   referencia (o primeiro arquivo da serie).
3. VALIDACAO DE GRADE POR ANO: apos recortar a propriedade em cada
   arquivo, confere se o shape/transform bate com o do primeiro ano
   processado (que tambem serve de referencia para checar APP e RL).
4. Uma vez que todas as bandas anuais sao lidas e validadas, sao
   empilhadas em um UNICO array 3D (`np.stack`) -- a partir daqui o
   calculo e IDENTICO (e igualmente vetorizado) ao da versao com VRT.

SAIDA
------------------------------------------------------------------------
Formato longo: ano; tipo; area_natural_ha; area_nao_natural_ha;
area_total_ha; pct_natural -- tipo in {"Propriedade", "APP", "Reserva_Legal"}.
==============================================================================
"""

import os
import re
import glob
import numpy as np
import geopandas as gpd
import rasterio
from rasterio.mask import mask
import pandas as pd
import datetime


_REGEX_ANO = re.compile(r"(19|20)\d{2}")  # primeiro ano de 4 digitos (1900-2099) no nome


def _extrair_ano_do_nome(caminho_arquivo):
    nome = os.path.basename(caminho_arquivo)
    m = _REGEX_ANO.search(nome)
    if not m:
        raise ValueError(
            f"Nao foi possivel extrair um ano (4 digitos, 19xx/20xx) do nome do "
            f"arquivo '{nome}'. Renomeie o arquivo incluindo o ano (ex.: "
            f"'brazil_coverage_1985.tif')."
        )
    return int(m.group(0))


def _validar_e_reprojetar_geometria(propriedade, id_propriedade, raster_crs, raster_bounds,
                                     parquet_path):
    geom = propriedade.geometry.iloc[0]

    if geom is None or geom.is_empty:
        raise ValueError(f"A propriedade {id_propriedade} tem geometria NULA ou VAZIA no parquet.")

    if not geom.is_valid:
        print(f"[ALERTA] Geometria de {id_propriedade} e' INVALIDA. Corrigindo com buffer(0)...")
        propriedade = propriedade.copy()
        propriedade["geometry"] = propriedade.geometry.buffer(0)
        geom = propriedade.geometry.iloc[0]
        if geom.is_empty:
            raise ValueError(f"Nao foi possivel corrigir a geometria de {id_propriedade}.")

    if propriedade.crs is None:
        raise ValueError(
            f"O parquet '{parquet_path}' nao tem CRS definido. Defina com "
            f"gdf.set_crs('EPSG:XXXX', allow_override=True) antes de prosseguir."
        )

    geom_reproj = propriedade.to_crs(raster_crs).geometry.iloc[0]
    xmin, ymin, xmax, ymax = geom_reproj.bounds

    if not all(np.isfinite([xmin, ymin, xmax, ymax])):
        raise ValueError(
            f"Geometria de {id_propriedade} ficou com coordenadas NAO-FINITAS (NaN/inf) "
            f"apos reprojetar de {propriedade.crs} para {raster_crs}. "
            f"Bounds originais: {propriedade.geometry.iloc[0].bounds}."
        )

    if (xmax < raster_bounds.left or xmin > raster_bounds.right or
            ymax < raster_bounds.bottom or ymin > raster_bounds.top):
        raise ValueError(
            f"Geometria de {id_propriedade} NAO INTERSECTA a extensao do raster.\n"
            f"  Propriedade: ({xmin:.2f}, {ymin:.2f}, {xmax:.2f}, {ymax:.2f})\n"
            f"  Raster:      ({raster_bounds.left:.2f}, {raster_bounds.bottom:.2f}, "
            f"{raster_bounds.right:.2f}, {raster_bounds.top:.2f})"
        )

    return geom_reproj


def _checar_grade_igual(shape_a, transform_a, shape_b, transform_b, rotulo_a, rotulo_b):
    if shape_a != shape_b or not transform_a.almost_equals(transform_b, precision=1e-6):
        raise ValueError(
            f"O recorte de '{rotulo_b}' NAO bate com o recorte de referencia '{rotulo_a}' "
            f"(shape {shape_b} vs {shape_a}). Os arquivos nao compartilham exatamente a "
            f"mesma grade espacial (CRS/resolucao/origem de pixel)."
        )


def calcular_area_natural_propriedade_app_rl_pasta(
    parquet_path, id_propriedade, raster_dir, path_app, path_rl,
    classes_naturais=(1,), coluna_id="landternure_code", all_touched=False,
    padrao_arquivos="*.tif*",
    extensoes_validas=(".tif", ".tiff"),
):
    """Area natural/nao-natural por ano, para Propriedade, APP e Reserva Legal,
    lendo os anos a partir de arquivos .tif separados em `raster_dir`."""
    print(f"[-] Localizando propriedade ID: {id_propriedade}...")
    gdf = gpd.read_parquet(parquet_path)
    if coluna_id not in gdf.columns:
        gdf[coluna_id] = gdf.index

    propriedade = gdf[gdf[coluna_id] == id_propriedade]
    if propriedade.empty:
        raise ValueError(f"Propriedade {id_propriedade} nao foi encontrada.")
    if len(propriedade) > 1:
        print(f"[ALERTA] {len(propriedade)} linhas para {id_propriedade}; usando a primeira.")

    # 1) Coletar e ordenar arquivos pelo ANO extraido do nome
    # NOTA: filtra por extensao real (.tif/.tiff) para excluir arquivos
    # auxiliares como .tif.aux.xml (gerados por QGIS/ArcGIS), que tambem
    # seriam capturados pelo padrao '*.tif*' e causariam anos duplicados.
    raster_files_raw = glob.glob(os.path.join(raster_dir, padrao_arquivos))
    raster_files = [
        f for f in raster_files_raw
        if os.path.splitext(f)[1].lower() in extensoes_validas
    ]
    if not raster_files:
        raise FileNotFoundError(
            f"Nenhum raster {extensoes_validas} encontrado em {raster_dir}. "
            f"({len(raster_files_raw)} arquivo(s) encontrado(s) pelo glob, mas nenhum com "
            f"extensao valida -- verifique se ha arquivos .tif na pasta.)"
        )

    arquivos_anos = sorted(
        ((_extrair_ano_do_nome(f), f) for f in raster_files), key=lambda x: x[0]
    )
    anos_lista = [a for a, _ in arquivos_anos]
    if len(set(anos_lista)) != len(anos_lista):
        repetidos = sorted({a for a in anos_lista if anos_lista.count(a) > 1})
        raise ValueError(f"Anos duplicados detectados a partir dos nomes de arquivo: {repetidos}.")

    print(f"[-] {len(arquivos_anos)} arquivos -> anos {anos_lista[0]} a {anos_lista[-1]}.")

    if not os.path.exists(path_app):
        raise FileNotFoundError(f"Raster de APP nao encontrado: {path_app}")
    if not os.path.exists(path_rl):
        raise FileNotFoundError(f"Raster de RL nao encontrado: {path_rl}")

    # 2) CRS de referencia = CRS do primeiro raster da serie
    with rasterio.open(arquivos_anos[0][1]) as src_ref:
        raster_crs = src_ref.crs
        raster_bounds = src_ref.bounds
        nodata_ref = src_ref.nodata

    # 3) Validar CRS de todos os arquivos (serie + APP + RL) contra a referencia
    print("[-] Validando CRS de todos os arquivos contra a referencia...")
    for f in [p for _, p in arquivos_anos] + [path_app, path_rl]:
        with rasterio.open(f) as src:
            if src.crs != raster_crs:
                raise ValueError(
                    f"CRS inconsistente: '{os.path.basename(f)}' tem CRS {src.crs}, "
                    f"diferente da referencia {raster_crs} (primeiro arquivo da serie)."
                )
    print("[OK] Todos os arquivos compartilham o mesmo CRS.")

    # 4) Validar/reprojetar geometria da propriedade
    geom_reproj = _validar_e_reprojetar_geometria(
        propriedade, id_propriedade, raster_crs, raster_bounds, parquet_path
    )
    geom_geojson = geom_reproj.__geo_interface__
    area_geom_ha = geom_reproj.area / 10_000.0
    print(f"[-] Area da propriedade (vetorial): {area_geom_ha:,.2f} ha")

    # 5) Recortar APP e RL uma unica vez (nao mudam entre anos)
    print("[-] Recortando APP e RL na extensao da propriedade...")
    with rasterio.open(path_app) as src_app:
        chunk_app, transform_app = mask(src_app, [geom_geojson], crop=True, all_touched=all_touched)
        nodata_app = src_app.nodata
    with rasterio.open(path_rl) as src_rl:
        chunk_rl, transform_rl = mask(src_rl, [geom_geojson], crop=True, all_touched=all_touched)
        nodata_rl = src_rl.nodata

    shape_app, shape_rl = chunk_app.shape[1:], chunk_rl.shape[1:]

    # 6) Ler CADA ano, validar grade contra a referencia e empilhar em 3D
    print(f"[-] Lendo e validando {len(arquivos_anos)} anos...")
    bandas_por_ano = []
    shape_referencia = transform_referencia = pixel_area_ha = None
    nodata_mb = nodata_ref

    for ano, caminho in arquivos_anos:
        with rasterio.open(caminho) as src_mb:
            if src_mb.nodata != nodata_ref:
                print(f"[ALERTA] nodata do ano {ano} ({src_mb.nodata}) difere da referencia "
                      f"({nodata_ref}). Usando o nodata da referencia para todos os anos.")
            chunk_mb, transform_mb = mask(src_mb, [geom_geojson], crop=True, all_touched=all_touched)

        banda = chunk_mb[0]
        shape_mb = banda.shape

        if shape_referencia is None:
            shape_referencia = shape_mb
            transform_referencia = transform_mb
            pixel_area_ha = (abs(transform_mb[0]) * abs(transform_mb[4])) / 10_000.0
            _checar_grade_igual(shape_referencia, transform_referencia,
                                 shape_app, transform_app, f"MapBiomas {ano}", "APP")
            _checar_grade_igual(shape_referencia, transform_referencia,
                                 shape_rl, transform_rl, f"MapBiomas {ano}", "Reserva Legal")
        else:
            _checar_grade_igual(shape_referencia, transform_referencia, shape_mb, transform_mb,
                                 f"MapBiomas {arquivos_anos[0][0]}", f"MapBiomas {ano}")

        bandas_por_ano.append(banda)

    chunk_mb_3d = np.stack(bandas_por_ano, axis=0)  # (n_anos, h, w)
    anos = np.array(anos_lista)

    mask_app = (chunk_app[0] == 1)
    if nodata_app is not None:
        mask_app &= (chunk_app[0] != nodata_app)
    mask_rl = (chunk_rl[0] == 1)
    if nodata_rl is not None:
        mask_rl &= (chunk_rl[0] != nodata_rl)

    area_total_app_ha = mask_app.sum() * pixel_area_ha
    area_total_rl_ha = mask_rl.sum() * pixel_area_ha
    print(f"[-] Area de APP dentro da propriedade: {area_total_app_ha:,.2f} ha")
    print(f"[-] Area de RL dentro da propriedade:  {area_total_rl_ha:,.2f} ha")

    # --- CALCULO VETORIZADO (todas as bandas de uma vez, sem loop Python) ---
    print(f"[-] Calculando area natural para {len(anos)} anos (vetorizado)...")

    valido_3d = np.ones_like(chunk_mb_3d, dtype=bool)
    if nodata_mb is not None:
        valido_3d &= (chunk_mb_3d != nodata_mb)
    natural_3d = np.isin(chunk_mb_3d, classes_naturais) & valido_3d

    def _areas(mask_2d_ou_none):
        if mask_2d_ou_none is None:
            valido, natural = valido_3d, natural_3d
        else:
            valido = valido_3d & mask_2d_ou_none
            natural = natural_3d & mask_2d_ou_none
        total_valido_ha = valido.sum(axis=(1, 2)) * pixel_area_ha
        natural_ha = natural.sum(axis=(1, 2)) * pixel_area_ha
        return natural_ha, total_valido_ha - natural_ha

    nat_prop, naonat_prop = _areas(None)
    nat_app, naonat_app = _areas(mask_app)
    nat_rl, naonat_rl = _areas(mask_rl)

    df = pd.concat([
        pd.DataFrame({"ano": anos, "tipo": "Propriedade",
                      "area_natural_ha": nat_prop, "area_nao_natural_ha": naonat_prop,
                      "area_total_ha": area_geom_ha}),
        pd.DataFrame({"ano": anos, "tipo": "APP",
                      "area_natural_ha": nat_app, "area_nao_natural_ha": naonat_app,
                      "area_total_ha": area_total_app_ha}),
        pd.DataFrame({"ano": anos, "tipo": "Reserva_Legal",
                      "area_natural_ha": nat_rl, "area_nao_natural_ha": naonat_rl,
                      "area_total_ha": area_total_rl_ha}),
    ], ignore_index=True)

    df["pct_natural"] = np.where(
        df["area_total_ha"] > 0, 100 * df["area_natural_ha"] / df["area_total_ha"], np.nan
    )
    cols_num = ["area_natural_ha", "area_nao_natural_ha", "area_total_ha", "pct_natural"]
    df[cols_num] = df[cols_num].round(4)

    problemas = df[(df["area_natural_ha"] + df["area_nao_natural_ha"]) > df["area_total_ha"] + 1e-6]
    if not problemas.empty:
        print(f"\n[AVISO] {len(problemas)} linha(s) com natural+nao_natural > total. "
              f"Verifique alinhamento/nodata.\n{problemas.to_string(index=False)}")

    return df.sort_values(["tipo", "ano"]).reset_index(drop=True)


if __name__ == "__main__":
    CAMINHO_PARQUET = "C:/Users/Bernard/Documents/malhafundiariaambiental/datasets/DADOS_FINAIS/balanco_ativo/balanco_passivo_ambiental_br_v5.parquet"
    DIRETORIO_RASTERS = "C:/Users/Bernard/Documents/malhafundiariaambiental/datasets/DADOS_FINAIS/imagens_mapbiomas/data/teste/"
    PATH_APP = "C:/Users/Bernard/Documents/malhafundiariaambiental/datasets/DADOS_FINAIS/imagens_mapbiomas/alinhamento/img_area_preservacao_permanente.tif"
    PATH_RL = "C:/Users/Bernard/Documents/malhafundiariaambiental/datasets/DADOS_FINAIS/imagens_mapbiomas/alinhamento/img_reserva_legal.tif"

    ID_DA_PROPRIEDADE_ALVO = 'GO-5203203-B3F7BC3DC1FF4498A408F0458A482207'

    # (1,) se ja reclassificado em binario; lista maior se classes originais
    # do MapBiomas, ex.: (1, 3, 4, 5, 6, 11, 12, 32, 49, 50)
    CLASSES_NATURAIS = (1,)

    PATH_SAIDA_CSV = "C:/Users/Bernard/Documents/malhafundiariaambiental/datasets/DADOS_FINAIS/area_natural_propriedade_app_rl_pasta_teste.csv"

    startproc = datetime.datetime.now()
    print("Iniciando processamento a partir de pasta de rasters (Propriedade + APP + RL)...", startproc)

    df_resultado = calcular_area_natural_propriedade_app_rl_pasta(
        parquet_path=CAMINHO_PARQUET,
        id_propriedade=ID_DA_PROPRIEDADE_ALVO,
        raster_dir=DIRETORIO_RASTERS,
        path_app=PATH_APP,
        path_rl=PATH_RL,
        classes_naturais=CLASSES_NATURAIS,
    )

    endproc = datetime.datetime.now()

    if not df_resultado.empty:
        print(f"\n[+] Evolucao Temporal da Area Natural ({ID_DA_PROPRIEDADE_ALVO}):")
        print(df_resultado.to_string(index=False))
        df_resultado.to_csv(PATH_SAIDA_CSV, sep=";", index=False)
        print(f"\n[OK] Resultado salvo em: {PATH_SAIDA_CSV}")

    print("\nFinalizando processamento...", endproc)
    print("Tempo total de processamento...", endproc - startproc)