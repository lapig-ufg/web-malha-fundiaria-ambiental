import json
import logging
import os
from core.config import settings

logger = logging.getLogger(__name__)

class Language:
    def get_lang(self, lang: str):
        # Normalize lang (e.g., pt-br -> pt)
        lang_code = lang.split('-')[0] if '-' in lang else lang
        file_path = os.path.join(settings.LANGUAGE_DIR, f"{lang_code}.json")
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Erro ao carregar arquivo de idioma {file_path}: {e}", exc_info=True)
            return {}

language = Language()
