from utils.language import language as lang_util
from models.layer import Layer
from utils.auxiliar import remove_null_properties

class Group:
    def __init__(self, language: str, params: dict, layertypes: dict):
        self.language_ob = lang_util.get_lang(language)
        self.id_group = params.get('idGroup')
        
        try:
            if params.get('labelGroup') == "translate":
                self.label_group = self.language_ob.get('descriptor_labels', {}).get('groups', {}).get(self.id_group, {}).get('labelGroup')
            else:
                self.label_group = params.get('labelGroup')
                
            self.group_expanded = params.get('groupExpanded', False)
            self.layers = []
            if 'layers' in params:
                self.layers = self.get_layers_array(language, params['layers'], layertypes)
        except Exception as e:
            print(f"Error in Group ID {self.id_group}: {e}")

    def get_layers_array(self, language, layers, layertypes):
        arr = []
        try:
            for layer_params in layers:
                layer_instance = Layer(language, layer_params, self.id_group, layertypes)
                arr.append(layer_instance.get_layer_instance())
        except Exception as e:
            print(f"Error while creating group object: {e}")
        return arr

    def get_group_instance(self):
        ob = {
            "idGroup": self.id_group,
            "labelGroup": self.label_group,
            "groupExpanded": self.group_expanded,
            "layers": self.layers
        }
        return remove_null_properties(ob)
