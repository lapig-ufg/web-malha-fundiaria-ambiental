import pandas as pd
import geopandas as gpd
import os
import pathlib

def transform():
    # Caminhos dos arquivos
    data_dir = pathlib.Path(__file__).parent.parent.parent / 'data'
    parquet_path = data_dir / 'balanco_passivo_ambiental_br_v3.parquet'
    excel_path = data_dir / 'RELATORIO_DTB_BRASIL_2024_MUNICIPIOS.xls'
    output_path = data_dir / 'balanco_passivo_ambiental_br_v3_transformed.parquet'

    print(f"Lendo arquivo Parquet: {parquet_path.name}...")
    # Lendo o parquet com geopandas
    gdf = gpd.read_parquet(parquet_path)

    print(f"Lendo arquivo Excel: {excel_path.name}...")
    # Lendo o excel (o cabeçalho está na linha 6, que é index 6 para pandas pular as primeiras)
    df_codes = pd.read_excel(excel_path, header=6)

    # Selecionando colunas relevantes do Excel e renomeando para facilitar o merge
    # 'UF' -> state_code
    # 'Nome_UF' -> state
    # 'Código Município Completo' -> municipality_code
    # 'Nome_Município' -> municipality
    df_codes = df_codes[['UF', 'Nome_UF', 'Código Município Completo', 'Nome_Município']]
    df_codes.columns = ['state_code', 'state', 'municipality_code', 'municipality']

    # Garantindo que os códigos sejam strings para o merge, removendo possíveis espaços
    gdf['municipality_code'] = gdf['municipality_code'].astype(str).str.strip()
    gdf['state_code'] = gdf['state_code'].astype(str).str.strip()
    
    df_codes['municipality_code'] = df_codes['municipality_code'].astype(str).str.strip()
    df_codes['state_code'] = df_codes['state_code'].astype(str).str.strip()

    # Removendo duplicatas do excel se houver (para evitar explosão no merge)
    df_codes = df_codes.drop_duplicates(subset=['municipality_code'])

    print("Realizando o merge para adicionar nomes de município e estado...")
    # Merge para adicionar nomes. Usamos left join para manter todos os dados do GeoDataFrame original.
    # Primeiro merge para o município (que já traz o estado se o mapeamento estiver completo)
    # Mas como o código do município é único e completo, podemos usar ele.
    gdf = gdf.merge(df_codes[['municipality_code', 'municipality', 'state']], on='municipality_code', how='left')

    # Renomeando 'geometry' para 'geom'
    print("Renomeando coluna 'geometry' para 'geom'...")
    gdf = gdf.rename(columns={'geometry': 'geom'})
    # Geopandas precisa saber qual é a nova coluna de geometria ativa
    gdf = gdf.set_geometry('geom')

    print(f"Salvando resultado em: {output_path.name}...")
    gdf.to_parquet(output_path)

    print("Transformação concluída com sucesso!")

if __name__ == "__main__":
    transform()
