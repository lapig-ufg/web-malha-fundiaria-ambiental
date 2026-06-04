import os
import glob
import sys

import geopandas as gpd
import numpy as np
import rasterio
from rasterio.mask import mask
import pandas as pd
import datetime

def criar_matriz_codificada_temporal(raster_files, geom_geojson, classe_vegetacao):
    """
    1. Abre as 21 imagens apenas na região da propriedade (crop).
    2. Aplica a codificação exponencial (potências de 2) para cada ano.
    3. Consolida tudo em uma ÚNICA matriz 2D codificada.
    """
    matriz_codificada_final = None
    pixel_size_x = None
    pixel_size_y = None
    nodata_val = None
    
    print(f"[-] Criando imagem codificada (Potências de 2) para os {len(raster_files)} anos...")
    
    for idx, img_path in enumerate(raster_files):
        with rasterio.open(img_path) as src:
            # Recorta apenas o pedaço da propriedade
            imagem_recortada, transform = mask(src, [geom_geojson], crop=True)
            
            if pixel_size_x is None:
                pixel_size_x = abs(transform[0])
                pixel_size_y = abs(transform[4])
                nodata_val = src.nodata
            
            banda = imagem_recortada[0]
            
            # Cria a máscara booleana onde tem vegetação natural
            mascara_veg = (banda == classe_vegetacao)
            if nodata_val is not None:
                mascara_veg &= (banda != nodata_val)
            
            # Aplica a regra: Ano 1 = 1 (2^0), Ano 2 = 2 (2^1), Ano 3 = 4 (2^2), etc.
            # O operador bitwise shift (1 << idx) é o equivalente ultra-rápido a 2**idx
            peso_do_ano = 1 << idx
            
            # Inicializa a matriz final com zeros no formato correto (int32 ou int64 para não estourar os bits)
            if matriz_codificada_final is None:
                matriz_codificada_final = np.zeros_like(banda, dtype=np.int64)
            
            # Onde for vegetação, soma-se o peso binário daquele ano específico
            matriz_codificada_final[mascara_veg] += peso_do_ano
            
    area_pixel = pixel_size_x * pixel_size_y
    return matriz_codificada_final, area_pixel, nodata_val

def pipeline_raster_codificado(parquet_path, id_propriedade, raster_dir, classe_vegetacao=1):
    """
    Pipeline principal: Filtra o Parquet, gera a imagem codificada e realiza
    a decodificação bitwise para calcular as áreas anuais na velocidade da luz.
    """
    print(f"[-] Carregando GeoParquet e localizando a propriedade ID: {id_propriedade}...")
    gdf = gpd.read_parquet(parquet_path)
    
    if "landternure_code" not in gdf.columns:
        gdf["landternure_code"] = gdf.index
        
    propriedade = gdf[gdf["landternure_code"] == id_propriedade]
    if propriedade.empty:
        raise ValueError(f"Propriedade com o ID {id_propriedade} não foi encontrada.")
    
    # Coleta e ordena as 21 imagens
    raster_files = sorted(glob.glob(os.path.join(raster_dir, "*.tif*")))
    if len(raster_files) == 0:
        raise FileNotFoundError(f"Nenhuma imagem raster (.tif) encontrada em {raster_dir}")
        
    anos_mapeados = [os.path.basename(f).replace('.tif', '').replace('.tiff', '') for f in raster_files]
    
    # Alinha CRS
    with rasterio.open(raster_files[0]) as src:
        raster_crs = src.crs.to_string()
        
    propriedade_reprojetada = propriedade.to_crs(raster_crs)
    geom_geojson = propriedade_reprojetada.geometry.iloc[0].__geo_interface__
    
    # PASSO 1: Geração da Imagem Codificada Única na RAM
    imagem_codificada, area_pixel, nodata_val = criar_matriz_codificada_temporal(raster_files, geom_geojson, classe_vegetacao)
    
    print(f"[-] Imagem unificada gerada com sucesso.")
    print(f"[-] Iniciando extração das áreas por ano através da imagem codificada...")
    
    resultados = []
    
    # PASSO 2: Decodificação Bitwise (Operação matemática pura na imagem codificada)
    for idx, ano_nome in enumerate(anos_mapeados):
        peso_do_ano = 1 << idx
        
        # O operador '&' (Bitwise AND) verifica se o bit correspondente ao ano está ativo naquele pixel.
        # Se o resultado for maior que zero, significa que havia vegetação naquele ano.
        pixels_do_ano = (imagem_codificada & peso_do_ano) > 0
        
        # Remove áreas de nodata se aplicável
        if nodata_val is not None:
            pixels_do_ano &= (imagem_codificada != nodata_val)
            
        total_pixels = np.sum(pixels_do_ano)
        area_hectares = (total_pixels * area_pixel) / 10000.00
        
        resultados.append({
            "ano_arquivo": ano_nome,
            "area_vegetacao_natural_ha": area_hectares,
            "pixels_contados": int(total_pixels)
        })
        
    return pd.DataFrame(resultados)

# NOTE: the __main__ block has been removed. The canonical implementation
# lives at app/server/utils/zonal_statistics.py (compute_zonal_history) and
# is invoked via the /service/zonal/jobs endpoint. The scripts folder will
# be deleted in production.