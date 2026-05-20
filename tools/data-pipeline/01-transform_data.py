import duckdb
import os
import sys

def process_data():
    # Paths
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(script_dir, '..', 'data')
    input_parquet = os.path.join(data_dir, 'balanco_passivo_ambiental_br_v3.parquet')
    codes_csv = os.path.join(data_dir, 'codes.csv')
    output_parquet = os.path.join(data_dir, 'new_data.parquet')

    if not os.path.exists(input_parquet):
        print(f"Input file not found: {input_parquet}")
        return

    if not os.path.exists(codes_csv):
        print(f"Codes CSV not found: {codes_csv}")
        return

    print("Initializing DuckDB...")
    con = duckdb.connect()

    # Load codes and create lookup tables
    # Skip first 6 lines of codes.csv to get to the header
    print("Loading codes.csv...")
    con.execute(f"""
        CREATE TABLE codes AS 
        SELECT * FROM read_csv('{codes_csv}', skip=6, header=True, all_varchar=True, sample_size=-1, ignore_errors=True, null_padding=True);
    """)

    # Create unique mapping for states (UF -> Nome_UF)
    con.execute("""
        CREATE TABLE state_mapping AS 
        SELECT DISTINCT CAST(UF AS VARCHAR) as uf_code, Nome_UF FROM codes WHERE UF IS NOT NULL;
    """)

    # Create unique mapping for municipalities (Código Município Completo -> Nome_Município)
    con.execute("""
        CREATE TABLE mun_mapping AS 
        SELECT DISTINCT CAST("Código Município Completo" AS VARCHAR) as mun_code, Nome_Município FROM codes WHERE "Código Município Completo" IS NOT NULL;
    """)

    print(f"Processing {input_parquet}...")
    
    # Transformation logic:
    # 1. GEOCODIGO (code) -> municipality (name)
    # 2. CD_UF (code) -> state (name)
    # 3. Ativo -> has_asset (Com Ativo -> true, else -> false)
    # 4. geo_id -> gid
    # 5. geometry -> geom
    # 6. Remove perc_ativo and area_ha_teste
    
    query = f"""
        COPY (
            SELECT 
                m.Nome_Município as municipality,
                s.Nome_UF as state,
                CAST(p.CD_UF AS VARCHAR) as cd_geouf,
                CAST(p.GEOCODIGO AS VARCHAR) as cd_geomu,
                CASE WHEN p.Ativo = 'Com Ativo' THEN true ELSE false END as has_asset,
                p.geo_id as gid,
                p.geometry as geom,
                -- Selecting other columns that were not explicitly mentioned to be removed
                -- Excluding perc_ativo and area_ha_teste
                p.* EXCLUDE (GEOCODIGO, CD_UF, Ativo, geo_id, geometry, perc_ativo, area_ha_teste)
            FROM read_parquet('{input_parquet}') p
            LEFT JOIN state_mapping s ON CAST(p.CD_UF AS VARCHAR) = s.uf_code
            LEFT JOIN mun_mapping m ON CAST(p.GEOCODIGO AS VARCHAR) = m.mun_code
        ) TO '{output_parquet}' (FORMAT 'PARQUET');
    """

    try:
        con.execute(query)
        print(f"Success! Processed data saved to {output_parquet}")
    except Exception as e:
        print(f"Error during processing: {e}")
    finally:
        con.close()

if __name__ == "__main__":
    process_data()
