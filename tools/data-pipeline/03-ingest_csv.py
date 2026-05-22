import os
import pathlib
import sys
import argparse
import duckdb
import psycopg2
from dotenv import load_dotenv

# Carrega variáveis de ambiente do arquivo .env
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

def ingest_csv(file_path: pathlib.Path, table_name: str):
    if not file_path.exists():
        print(f"Erro: O arquivo '{file_path}' não foi encontrado.")
        return
    
    # Conectar ao DuckDB
    con = duckdb.connect()
    
    print("Carregando extensões DuckDB...")
    con.execute("INSTALL postgres; LOAD postgres;")
    
    pg_conn_str = f"host={DB_CONFIG['host']} port={DB_CONFIG['port']} dbname={DB_CONFIG['database']} user={DB_CONFIG['user']} password={DB_CONFIG['password']}"
    
    print(f"Conectando ao banco Postgres: {DB_CONFIG['database']} em {DB_CONFIG['host']}...")
    con.execute(f"ATTACH '{pg_conn_str}' AS pg (TYPE postgres);")
    
    try:
        print(f"Iniciando ingestão de {file_path.name} para a tabela pg.{table_name}...")
        
        # Ingestão direta do CSV
        # O DuckDB detecta automaticamente o delimitador e os tipos de dados
        con.execute(f"CREATE TABLE IF NOT EXISTS pg.{table_name} AS SELECT * FROM read_csv_auto('{file_path}');")
        
        print(f"Ingestão de {table_name} concluída com sucesso!")
        
    except Exception as e:
        print(f"Erro durante a ingestão: {e}")
    finally:
        try:
            con.execute("DETACH pg;")
        except:
            pass

def main():
    parser = argparse.ArgumentParser(description='Ingere um arquivo CSV no Postgres via DuckDB.')
    parser.add_argument('file_path', type=str, help='Caminho para o arquivo CSV a ser ingerido.')
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
        
        ingest_csv(file_path, args.table_name)
        
    except Exception as e:
        print(f"Erro de conexão ou processamento: {e}")

if __name__ == "__main__":
    main()
