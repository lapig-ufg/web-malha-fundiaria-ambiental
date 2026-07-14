import os
import zipfile
from pathlib import Path
from minio import Minio
from minio.error import S3Error
from tqdm import tqdm
from loguru import logger
from multiprocessing import Pool

# Configurações de diretório
DATA_DIR = "/home/tiago/Documentos/Github/web-malha-fundiaria-ambiental/data"
BUCKET_NAME = "malha-fundiaria"
PREFIX = "vegetation/"

# Adiciona o arquivo de log
logger.add(Path(__file__).parent / 'download.log')

def get_minio_client():
    """
    Instancia o cliente MinIO. 
    Fazemos isso dentro da função para evitar erros de concorrência (pickling) 
    quando usamos multiprocessing.
    """
    return Minio(
        "s3.lapig.iesa.ufg.br",
        access_key="",
        secret_key="",
        secure=True
    )

def is_data_populated(directory):
    """
    Verifica se a pasta existe e possui pelo menos um arquivo/diretório dentro.
    """
    path = Path(directory)
    if not path.exists():
        logger.info(f"Diretório {directory} não existe. Criando diretório...")
        path.mkdir(parents=True, exist_ok=True)
        return False
    return any(path.iterdir())

def download_and_extract(object_name):
    """
    Faz o download de um objeto zip do MinIO e o descompacta.
    Recebe apenas o nome do objeto (string) para facilitar o multiprocessamento.
    """
    try:
        client = get_minio_client()
        filename = Path(object_name).name
        local_zip_path = Path(DATA_DIR) / filename
        
        # 1. Faz o download do arquivo zip
        client.fget_object(
            bucket_name=BUCKET_NAME,
            object_name=object_name,
            file_path=str(local_zip_path)
        )
        
        # 2. Descompacta o arquivo baixado
        with zipfile.ZipFile(local_zip_path, 'r') as zip_ref:
            zip_ref.extractall(DATA_DIR)
            
        # 3. Remove o arquivo zip para economizar espaço
        if os.path.isfile(local_zip_path):
            os.remove(local_zip_path)
            
        return {'file': object_name, 'status': 'ok', 'error': ''}
        
    except Exception as e:
        return {'file': object_name, 'status': 'error', 'error': str(e)}

def main():
    if is_data_populated(DATA_DIR):
        logger.info(f"A pasta {DATA_DIR} já está povoada. Nenhuma ação de download necessária.")
        print(f"A pasta {DATA_DIR} já possui dados. Script encerrado.")
        return

    logger.info(f"A pasta {DATA_DIR} está vazia. Iniciando busca no MinIO...")
    
    try:
        client = get_minio_client()
        objects = client.list_objects(BUCKET_NAME, prefix=PREFIX, recursive=True)
        
        # Extrai apenas os NOMES dos objetos para passar para o Pool (strings)
        zip_objects_names = [obj.object_name for obj in objects if obj.object_name.endswith('.zip')]
        
        if not zip_objects_names:
            logger.warning("Nenhum arquivo .zip foi encontrado no bucket/prefixo especificado.")
            print("Nenhum arquivo .zip encontrado.")
            return
            
        print(f"Encontrados {len(zip_objects_names)} arquivos .zip. Iniciando processamento paralelo (16 workers)...")
        
        results = []
        
        # Inicia o Pool de processos
        with Pool(16) as p:
            # imap_unordered é ótimo com tqdm pois a barra avança assim que qualquer worker terminar
            for result in tqdm(p.imap_unordered(download_and_extract, zip_objects_names), total=len(zip_objects_names), desc="Processando arquivos"):
                results.append(result)
                
        # Verifica se ocorreu algum erro e registra
        errors = [r for r in results if r['status'] == 'error']
        if errors:
            logger.warning(f"Processo concluído com {len(errors)} erros. Verifique os logs detalhados.")
            for err in errors:
                logger.error(f"Erro em {err['file']}: {err['error']}")
        else:
            logger.info("Todos os arquivos foram baixados e extraídos com sucesso!")
            
    except S3Error as e:
        logger.error(f"Erro de comunicação com o MinIO: {e}")
        print(f"Erro de S3: {e}")
    except Exception as e:
        logger.exception(f"Erro inesperado no processo principal: {e}")

if __name__ == "__main__":
    main()