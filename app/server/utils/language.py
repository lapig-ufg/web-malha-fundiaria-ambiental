import json
import os
from core.config import settings

class Language:
    def get_lang(self, lang: str):
        # Normalize lang (e.g., pt-br -> pt)
        lang_code = lang.split('-')[0] if '-' in lang else lang
        file_path = os.path.join(settings.LANGUAGE_DIR, f"{lang_code}.json")
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading language file {file_path}: {e}")
            return {}

language = Language()
