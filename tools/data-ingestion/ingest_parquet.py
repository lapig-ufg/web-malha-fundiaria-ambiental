import duckdb
import os
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

def get_connection_string():
    return f"postgresql://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"

def ingest_data():
    # Caminho para os arquivos parquet
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(script_dir, '..', 'data')
    
    if not os.path.exists(data_dir):
        print(f"Pasta /{data_dir} não encontrada.")
        return

    files = [f for f in os.listdir(data_dir) if f.endswith('.parquet')]
    
    if not files:
        print(f"Nenhum arquivo .parquet encontrado na pasta /{data_dir}.")
        return

    # Conectar ao DuckDB (em memória)
    con = duckdb.connect()
    
    # Instalar e carregar extensões necessárias
    print("Instalando e carregando extensões do DuckDB...")
    con.execute("INSTALL spatial;")
    con.execute("LOAD spatial;")
    con.execute("INSTALL postgres;")
    con.execute("LOAD postgres;")
    
    # Criar string de conexão para o DuckDB
    pg_conn_str = f"host={DB_CONFIG['host']} port={DB_CONFIG['port']} dbname={DB_CONFIG['database']} user={DB_CONFIG['user']} password={DB_CONFIG['password']}"
    
    # Atachar o banco Postgres
    print(f"Conectando ao banco Postgres: {DB_CONFIG['database']} em {DB_CONFIG['host']}...")
    con.execute(f"ATTACH '{pg_conn_str}' AS pg (TYPE postgres);")
    
    for file_name in files:
        # Nome da tabela no Postgres (removendo .parquet)
        table_name = file_name.replace('.parquet', '')
        file_path = os.path.join(data_dir, file_name)
        
        print(f"\n--- Iniciando ingestão de {file_name} para a tabela {table_name} ---")
        
        # Identificar as colunas e definir mapeamento (minúsculo, gid, geom)
        cols_info = con.execute(f"DESCRIBE SELECT * FROM '{file_path}' LIMIT 0").fetchall()
        
        select_parts = []
        geom_col_original = None
        id_col_original = None
        
        # 1. Detectar candidatos a geometria e ID único
        for col in cols_info:
            name = col[0]
            dtype = col[1]
            # Detecta geometria por tipo ou nome
            if 'geometry' in dtype.lower() or name.lower() in ['geometry', 'geom']:
                geom_col_original = name
            # Detecta ID único (prioridade para geo_id, depois geocodigo)
            if name.lower() == 'geo_id':
                id_col_original = name
            elif name.lower() == 'geocodigo' and not id_col_original:
                id_col_original = name

        # 2. Construir SELECT com renomeação
        seen_names = set()
        for col in cols_info:
            name = col[0]
            target_name = name.lower()
            
            if name == geom_col_original:
                target_name = 'geom'
            elif name == id_col_original:
                target_name = 'gid'
            
            # Evitar duplicatas (ex: se ja existia uma coluna 'geom' e renomeamos outra)
            if target_name in seen_names:
                target_name = f"{target_name}_alt"
            
            select_parts.append(f'"{name}" AS "{target_name}"')
            seen_names.add(target_name)
        
        cols_str = ", ".join(select_parts)
        
        # Executar a cópia
        try:
            print(f"Transferindo dados de {file_name}...")
            # Criando a tabela a partir do Parquet com nomes já ajustados
            con.execute(f"CREATE TABLE IF NOT EXISTS pg.{table_name} AS SELECT {cols_str} FROM '{file_path}';")
            
            # Post-processamento via psycopg2 para garantir PostGIS, 2D e SRID 4674
            print(f"Ajustando para PostGIS 2D (MultiPolygon, 4674 - SIRGAS 2000)...")
            try:
                with psycopg2.connect(**DB_CONFIG) as conn:
                    with conn.cursor() as cur:
                        # 1. Ajustar geometria para MultiPolygon 2D e transformar para SRID 4674
                        cur.execute(f"""
                            ALTER TABLE "{table_name}" 
                            ALTER COLUMN "geom" TYPE geometry(MultiPolygon, 4674) 
                            USING ST_Multi(ST_Transform(ST_Force2D(ST_SetSRID("geom"::geometry, 102033)), 4674));
                        """)
                        # 2. Garantir que gid seja chave primária e incremental (SERIAL)
                        print(f"Garantindo coluna 'gid' como SERIAL PRIMARY KEY...")
                        cur.execute(f"""
                            DO $$ 
                            BEGIN 
                                IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                                               WHERE table_name = '{table_name}' AND column_name = 'gid') THEN
                                    ALTER TABLE "{table_name}" ADD COLUMN gid SERIAL PRIMARY KEY;
                                ELSE
                                    IF NOT EXISTS (SELECT 1 FROM pg_index i
                                                   JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey)
                                                   WHERE i.indrelid = '"{table_name}"'::regclass AND i.indisprimary) THEN
                                        ALTER TABLE "{table_name}" ADD PRIMARY KEY (gid);
                                    END IF;
                                END IF;
                            EXCEPTION WHEN OTHERS THEN 
                                RAISE NOTICE 'Não foi possível definir PK ou SERIAL em gid para {table_name}';
                            END $$;
                        """)
                    conn.commit()
            except Exception as pg_err:
                print(f"Aviso: Erro no ajuste PostGIS/PK: {pg_err}")
            
            print(f"Ingestão de {table_name} concluída com sucesso!")
        except Exception as e:
            print(f"Erro ao processar {file_name}: {e}")
            print("Tentando inserir em tabela existente...")
            try:
                con.execute(f"INSERT INTO pg.{table_name} SELECT {cols_str} FROM '{file_path}';")
                print(f"Dados de {table_name} inseridos com sucesso!")
            except Exception as e2:
                print(f"Falha definitiva ao processar {table_name}: {e2}")

    con.execute("DETACH pg;")
    print("\nProcesso concluído.")

def main():
    try:
        conn = get_connection()
        print("Conexão com o Postgres testada com sucesso!")
        conn.close()
        
        ingest_data()
        
    except Exception as e:
        print(f"Erro ao conectar ou processar: {e}")

if __name__ == "__main__":
    main()
