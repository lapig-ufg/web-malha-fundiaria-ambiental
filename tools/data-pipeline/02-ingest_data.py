import os
import pathlib
import sys
import argparse
import duckdb
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DB_CONFIG = {
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "host": os.getenv("DB_HOST"),
    "port": os.getenv("DB_PORT"),
    "database": os.getenv("DB_NAME")
}

def get_connection():
    return psycopg2.connect(**DB_CONFIG)

def ingest_data(file_path: pathlib.Path, table_name: str):
    if not file_path.exists():
        print(f"Erro: O arquivo '{file_path}' não foi encontrado.")
        return
    
    # Conectar ao DuckDB
    con = duckdb.connect()
    
    print("Carregando extensões DuckDB...")
    con.execute("INSTALL spatial; LOAD spatial;")
    con.execute("INSTALL postgres; LOAD postgres;")
    
    pg_conn_str = f"host={DB_CONFIG['host']} port={DB_CONFIG['port']} dbname={DB_CONFIG['database']} user={DB_CONFIG['user']} password={DB_CONFIG['password']}"
    
    print(f"Conectando ao banco Postgres: {DB_CONFIG['database']} em {DB_CONFIG['host']}...")
    con.execute(f"ATTACH '{pg_conn_str}' AS pg (TYPE postgres);")
    
    try:
        # Detectar a coluna de geometria para o ajuste posterior
        cols_info = con.execute(f"DESCRIBE SELECT * FROM '{file_path}'").fetchall()
        geom_col = None
        for col in cols_info:
            name = col[0]
            dtype = col[1]
            if 'geometry' in dtype.lower() or name.lower() in ['geometry', 'geom']:
                geom_col = name
                break

        print(f"Iniciando ingestão de {file_path.name} para a tabela pg.{table_name}...")
        
        # Ingestão direta - mantém todos os nomes de colunas originais
        con.execute(f"CREATE TABLE IF NOT EXISTS pg.{table_name} AS SELECT * FROM '{file_path}';")
        
        if geom_col:
            print(f"Ajustando coluna '{geom_col}' para geometria 2D...")
            try:
                with psycopg2.connect(**DB_CONFIG) as conn:
                    with conn.cursor() as cur:
                        # Força 2D e garante que seja do tipo geometry
                        cur.execute(f"""
                            ALTER TABLE "{table_name}" 
                            ALTER COLUMN "{geom_col}" TYPE geometry 
                            USING ST_Force2D("{geom_col}"::geometry);
                        """)
                    conn.commit()
                print(f"Ajuste de geometria concluído.")
            except Exception as pg_err:
                print(f"Aviso: Erro ao ajustar geometria no Postgres: {pg_err}")
        
        print(f"Ingestão de {table_name} concluída com sucesso!")
        
    except Exception as e:
        print(f"Erro durante a ingestão: {e}")
    finally:
        con.execute("DETACH pg;")

def main():
    parser = argparse.ArgumentParser(description='Ingere um arquivo (Parquet, etc) no Postgres via DuckDB.')
    parser.add_argument('file_path', type=str, help='Caminho para o arquivo a ser ingerido.')
    parser.add_argument('table_name', type=str, help='Nome da tabela no banco de dados.')
    
    if len(sys.argv) < 3:
        parser.print_help()
        return

    args = parser.parse_args()
    file_path = pathlib.Path(args.file_path)
    
    try:
        # Teste de conexão rápida
        conn = get_connection()
        conn.close()
        
        ingest_data(file_path, args.table_name)
        
    except Exception as e:
        print(f"Erro de conexão ou processamento: {e}")

if __name__ == "__main__":
    main()
