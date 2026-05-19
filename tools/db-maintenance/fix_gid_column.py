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

def fix_table():
    table_name = "malha_fundiaria_consolidada"
    
    try:
        print(f"Conectando ao banco para corrigir a tabela {table_name}...")
        with psycopg2.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cur:
                print(f"Verificando/Adicionando coluna 'gid' incremental...")
                cur.execute(f"""
                    DO $$ 
                    BEGIN 
                        -- Se a coluna gid não existir, adiciona como SERIAL PRIMARY KEY
                        IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                                       WHERE table_name = '{table_name}' AND column_name = 'gid') THEN
                            ALTER TABLE "{table_name}" ADD COLUMN gid SERIAL PRIMARY KEY;
                            RAISE NOTICE 'Coluna gid adicionada com sucesso como SERIAL PRIMARY KEY.';
                        ELSE
                            -- Se existir mas não for chave primária, tenta transformar em PK
                            IF NOT EXISTS (SELECT 1 FROM pg_index i
                                           JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey)
                                           WHERE i.indrelid = '"{table_name}"'::regclass AND i.indisprimary) THEN
                                ALTER TABLE "{table_name}" ADD PRIMARY KEY (gid);
                                RAISE NOTICE 'Coluna gid já existia, definida como PRIMARY KEY.';
                            ELSE
                                RAISE NOTICE 'Coluna gid já existe e é PRIMARY KEY.';
                            END IF;
                        END IF;
                    END $$;
                """)
            conn.commit()
            print(f"Correção concluída para {table_name}.")
            
    except Exception as e:
        print(f"Erro ao corrigir a tabela: {e}")

if __name__ == "__main__":
    fix_table()
