from utils.language import language as lang_util
from utils.auxiliar import remove_null_properties

class Layer:
    def __init__(self, language: str, params: dict, id_group: str, all_layers_t: dict):
        self.language = language
        self.language_ob = lang_util.get_lang(language)
        self.id_group = id_group
        self.id_layer = params.get('idLayer')
        
        self.layer_types = []
        if 'types' in params:
            self.layer_types = self.get_layer_types_array(params['types'], all_layers_t)
            
        if self.id_layer in ['limits', 'basemaps']:
            try:
                self.label_layer = self.language_ob.get('descriptor_labels', {}).get(self.id_layer, {}).get('labelLayer')
            except Exception:
                self.label_layer = params.get('labelLayer')
            
            if not self.label_layer or self.label_layer == 'translate':
                self.label_layer = self.id_layer
        else:
            if params.get('labelLayer', '').lower() == "translate":
                try:
                    self.label_layer = self.language_ob.get('descriptor_labels', {}).get('groups', {}).get(self.id_group, {}).get('layers', {}).get(self.id_layer, {}).get('labelLayer')
                except Exception:
                    self.label_layer = self.id_layer
                
                if not self.label_layer:
                    self.label_layer = self.id_layer
            else:
                self.label_layer = params.get('labelLayer', self.id_layer)
        
        self.visible = params.get('visible', False)
        self.selected_type = params.get('selectedType')
        if not self.selected_type and self.layer_types:
            self.selected_type = self.layer_types[0].get('valueType')

    def get_layer_types_array(self, layertypes, alllayertypes):
        layertypes_v = []
        for user_selected in layertypes:
            for k in alllayertypes:
                ob = next((obj for obj in alllayertypes[k] if obj.get('valueType', '').upper() == user_selected.upper()), None)
                if ob:
                    layertypes_v.append(ob.copy())
        return layertypes_v

    def get_layer_instance(self):
        ob = {
            "idLayer": self.id_layer,
            "labelLayer": self.label_layer,
            "visible": self.visible,
            "selectedType": self.selected_type,
            "types": self.layer_types
        }
        return remove_null_properties(ob)
