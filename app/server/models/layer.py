from utils.auxiliar import remove_null_properties

class Layer:
    def __init__(self, language_ob: dict, params: dict, id_group: str, all_layers_t: dict):
        self.language_ob = language_ob
        self.params = params
        self.id_group = id_group
        self.id_layer = params.get('idLayer')
        
        self.layer_types = []
        if 'types' in params:
            self.layer_types = self.get_layer_types_array(params['types'], all_layers_t)
            
        label_layer_param = params.get('labelLayer')
        
        # Robust labelLayer translation lookup
        # 1. Try top-level lookup (like user snippet: descriptor_labels.[id_layer].labelLayer)
        top_level_label = self.language_ob.get('descriptor_labels', {}).get(self.id_layer, {}).get('labelLayer')
        
        # 2. Try nested lookup (descriptor_labels.groups.[id_group].layers.[id_layer].labelLayer)
        nested_label = None
        if self.id_group:
             nested_label = self.language_ob.get('descriptor_labels', {}).get('groups', {}).get(self.id_group, {}).get('layers', {}).get(self.id_layer, {}).get('labelLayer')

        # Prioritize translation if 'translate' is requested, otherwise use params or idLayer
        if label_layer_param and str(label_layer_param).lower() == "translate":
            # Prefer top-level then nested
            self.label_layer = top_level_label if top_level_label else nested_label
            # Final fallback to idLayer
            if not self.label_layer or str(self.label_layer).lower() == 'translate':
                self.label_layer = self.id_layer
        else:
            # If a specific label was provided in params, use it, but still try to translate if it matches a key
            self.label_layer = label_layer_param if label_layer_param else (top_level_label if top_level_label else (nested_label if nested_label else self.id_layer))
        
        self.visible = params.get('visible', False)
        self.selected_type = params.get('selectedType')
        self.min_zoom = params.get('minZoom')
        if not self.selected_type and self.layer_types:
            self.selected_type = self.layer_types[0].get('valueType')

    def get_layer_types_array(self, layertypes, alllayertypes):
        layertypes_v = []
        for user_selected in layertypes:
            for k in alllayertypes:
                ob = next((obj for obj in alllayertypes[k] if obj.get('valueType', '').upper() == user_selected.upper()), None)
                if ob:
                    typed_ob = ob.copy()
                    
                    # Merge properties from the layer definition in the JSON descriptor
                    # This allows specifying styles and projections per layer in the JSON
                    if 'cogStyle' in self.params:
                        typed_ob['cogStyle'] = self.params['cogStyle']
                    
                    if 'projection' in self.params:
                        typed_ob['projection'] = self.params['projection']

                    if 'legend' in self.params:
                        typed_ob['legend'] = self.params['legend']

                    if 'filterHandler' in self.params:
                        typed_ob['filterHandler'] = self.params['filterHandler']

                    if 'regionFilter' in self.params:
                        typed_ob['regionFilter'] = self.params['regionFilter']

                    layertypes_v.append(typed_ob)
        return layertypes_v

    def get_layer_instance(self):
        ob = {
            "idLayer": self.id_layer,
            "labelLayer": self.label_layer,
            "visible": self.visible,
            "selectedType": self.selected_type,
            "minZoom": self.min_zoom,
            "types": self.layer_types
        }

        # Merge any extra parameters from the JSON descriptor
        for key, value in self.params.items():
            if key not in ob and key not in ['labelLayer', 'types', 'filterHandler', 'regionFilter']:
                ob[key] = value

        return remove_null_properties(ob)
