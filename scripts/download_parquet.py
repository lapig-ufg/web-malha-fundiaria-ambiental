from pathlib import Path
from minio import Minio
from minio.error import S3Error
from loguru import logger

# Configurações de diretório e alvo
DATA_DIR = "/home/tiago/Documents/Github/web-malha-fundiaria-ambiental/data"
BUCKET_NAME = "malha-fundiaria"
TARGET_FILENAME = "balanco_passivo_ambiental_br_v3.parquet"

# Configuração do cliente MinIO
client = Minio(
    "s3.lapig.iesa.ufg.br",
    access_key="",  # Substitua pelas credenciais reais se necessário
    secret_key="",  # Substitua pelas credenciais reais se necessário
    secure=True
)

# Salva o log na mesma pasta do script para evitar erros de permissão de escrita
logger.add(Path(__file__).parent / 'download.log')

def main():
    # Garante que a pasta /data exista
    local_dir = Path(DATA_DIR)
    local_dir.mkdir(parents=True, exist_ok=True)
    local_file_path = local_dir / TARGET_FILENAME

    print(f"Buscando o arquivo '{TARGET_FILENAME}' no bucket '{BUCKET_NAME}'...")
    logger.info(f"Iniciando busca do arquivo {TARGET_FILENAME}")

    try:
        # Lista os objetos para encontrar o caminho exato (independente de estar na raiz ou em subpastas)
        objects = client.list_objects(BUCKET_NAME, recursive=True)
        exact_object_name = None

        for obj in objects:
            if obj.object_name.endswith(TARGET_FILENAME):
                exact_object_name = obj.object_name
                break

        if not exact_object_name:
            msg = f"O arquivo '{TARGET_FILENAME}' não foi encontrado no bucket '{BUCKET_NAME}'."
            logger.error(msg)
            print(f"Erro: {msg}")
            return

        print(f"Arquivo localizado em: '{exact_object_name}'. Iniciando download...")
        logger.info(f"Fazendo download de {exact_object_name} para {local_file_path}")

        # Faz o download direto do arquivo .parquet
        client.fget_object(
            bucket_name=BUCKET_NAME,
            object_name=exact_object_name,
            file_path=str(local_file_path)
        )

        print(f" Sucesso! Arquivo baixado e salvo em: {local_file_path}")
        logger.info("Download concluído com sucesso.")

    except S3Error as e:
        logger.error(f"Erro de comunicação com o MinIO: {e}")
        print(f"Erro de S3: {e}")
    except Exception as e:
        logger.exception(f"Erro inesperado: {e}")
        print(f"Erro inesperado: {e}")

if __name__ == "__main__":
    main()