import os
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    APP_NAME: str = "Malha Fundiária Ambiental"
    NODE_ENV: str = "dev"
    
    CLIENT_DIR: str = "/../client/dist/plataform-base/"
    LANGUAGE_DIR: str = "../client/src/assets/locales/"
    LANG_DIR: str = "/lang"
    LOG_DIR: str = "/log/"
    TMP: str = "/tmp/"
    
    MAX_AREA: int = 9500
    
    HOTSITE_DIR: str = ""
    PLATAFORMS_FOLDER_LOCALHOST: str = "/plataforms_files/"
    FIELD_DIR: str = ""
    UPLOAD_DIR: str = ""
    DOWNLOAD_DIR: str = ""
    
    PG_USER: str = ""
    PG_HOST: str = ""
    PG_DATABASE_LAPIG: str = ""
    PG_DATABASE_GENERAL: str = ""
    PG_PASSWORD: str = ""
    PG_PORT: int = 5432
    PG_DEBUG: bool = True
    
    PORT: int = 3000
    OWS_HOST: str = ""
    OWS_API: str = ""
    
    APP_PRODUCAO: str = ""
    
    @property
    def app_root(self) -> str:
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    @property
    def base_files_dir(self) -> str:
        if self.NODE_ENV == 'prod':
            return self.APP_PRODUCAO
        return os.path.join(self.app_root, self.PLATAFORMS_FOLDER_LOCALHOST)

    @property
    def field_dir_path(self) -> str:
        if self.NODE_ENV == 'prod':
            return os.path.join(self.APP_PRODUCAO, self.FIELD_DIR)
        return os.path.join(self.app_root, self.PLATAFORMS_FOLDER_LOCALHOST, self.FIELD_DIR)

    @property
    def upload_dir_path(self) -> str:
        if self.NODE_ENV == 'prod':
            return os.path.join(self.APP_PRODUCAO, self.UPLOAD_DIR)
        return os.path.join(self.app_root, self.PLATAFORMS_FOLDER_LOCALHOST, self.UPLOAD_DIR)

    @property
    def download_dir_path(self) -> str:
        if self.NODE_ENV == 'prod':
            return os.path.join(self.APP_PRODUCAO, self.DOWNLOAD_DIR)
        return os.path.join(self.app_root, self.PLATAFORMS_FOLDER_LOCALHOST, self.DOWNLOAD_DIR)

    @property
    def hotsite_dir_path(self) -> str:
        if self.NODE_ENV == 'prod':
            return os.path.join(self.APP_PRODUCAO, self.HOTSITE_DIR)
        return self.HOTSITE_DIR

    class Config:
        env_file = ".env"

settings = Settings()
