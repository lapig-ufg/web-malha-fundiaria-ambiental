import os
import json
from utils.language import language as lang_util
from models.group import Group
from models.layer import Layer

class DescriptorBuilder:
    def __init__(self, app_path: str):
        self.descriptor_path = os.path.join(app_path, "../server/descriptor")

    def get_groups_order(self):
        return [
            "malha_fundiaria",
            "pasture",
            "campo",
            "inspecao_visual",
            "agropecuaria",
            "areas_declaradas",
            "infraestrutura",
            "areas_especiais",
            "imagens",
        ]

    def get_layers(self, language, layertypes):
        folder_path = os.path.join(self.descriptor_path, "groups")
        jsons_in_dir = [f for f in os.listdir(folder_path) if f.endswith('.json')]
        
        language_ob = lang_util.get_lang(language)
        groups = []
        order = self.get_groups_order()
        
        for element in order:
            for file in jsons_in_dir:
                if element.lower() in file.lower():
                    try:
                        with open(os.path.join(folder_path, file), 'r', encoding='utf-8') as f:
                            items = json.load(f)
                            for item in items:
                                group = Group(language_ob, item, layertypes).get_group_instance()
                                groups.append(group)
                    except Exception as e:
                        print(f"Error while fetching layers from {file}: {e}")
        return groups

    def get_basemaps(self, language, layertypes):
        folder_path = os.path.join(self.descriptor_path, "basemaps")
        jsons_in_dir = [f for f in os.listdir(folder_path) if f.endswith('.json')]
        
        language_ob = lang_util.get_lang(language)
        basemaps = []
        for file in jsons_in_dir:
            try:
                with open(os.path.join(folder_path, file), 'r', encoding='utf-8') as f:
                    items = json.load(f)
                    for item in items:
                        layer = Layer(language_ob, item, None, layertypes).get_layer_instance()
                        basemaps.append(layer)
            except Exception as e:
                print(f"Error while fetching basemaps from {file}: {e}")
        return basemaps

    def get_limits(self, language, layertypes):
        folder_path = os.path.join(self.descriptor_path, "limits")
        jsons_in_dir = [f for f in os.listdir(folder_path) if f.endswith('.json')]
        
        language_ob = lang_util.get_lang(language)
        limits = []
        for file in jsons_in_dir:
            try:
                with open(os.path.join(folder_path, file), 'r', encoding='utf-8') as f:
                    items = json.load(f)
                    for item in items:
                        layer = Layer(language_ob, item, None, layertypes).get_layer_instance()
                        limits.append(layer)
            except Exception as e:
                print(f"Error while fetching limits from {file}: {e}")
        return limits
