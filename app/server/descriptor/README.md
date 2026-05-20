# Map Descriptor Configuration

This directory contains the JSON configuration files that define the structure and layers of the map. The backend server uses these files to build a "descriptor" object sent to the frontend.

## Directory Structure

- `groups/`: Contains JSON files defining thematic layer groups (e.g., Land Tenure, Pasture).
- `basemaps/`: Defines available background maps (Google, Mapbox, etc.).
- `limits/`: Defines boundary or administrative limit layers.

## How it Works

The `DescriptorBuilder` class (`app/server-new/utils/descriptor_builder.py`) scans these directories and parses the JSON files.

1.  **Groups Loading:** The server loads files in the `groups/` folder based on a specific order defined in `DescriptorBuilder.get_groups_order()`. Currently, only files matching these names (case-insensitive) are processed: `malha_fundiaria`, `pasture`, `campo`, `inspecao_visual`, `agropecuaria`, `areas_declaradas`, `infraestrutura`, `areas_especiais`, `imagens`.
2.  **Basemaps and Limits Loading:** All JSON files in the `basemaps/` and `limits/` folders are loaded.
3.  **Layer Resolution:** For each layer defined in a group, the server looks up its details (origin URL, type, etc.) in a list of `layertypes`.
4.  **LayerTypes:** These are fetched dynamically from the Lapig OWS API and can be augmented in `app/server-new/api/routes/map.py`.

## JSON Schema

### Groups (`groups/*.json`)
Files in this folder should contain an array of Group objects:

```json
[
  {
    "idGroup": "group_identifier",
    "labelGroup": "translate",
    "groupExpanded": false,
    "layers": [
      {
        "idLayer": "layer_identifier",
        "labelLayer": "translate",
        "visible": true,
        "selectedType": "value_type_string",
        "types": ["value_type_string"]
      }
    ]
  }
]
```

- `idGroup`: Unique identifier for the group.
- `labelGroup`: Use `"translate"` to look up the label in the frontend's localization files, or provide a string.
- `groupExpanded`: Boolean indicating if the group should be open by default.
- `layers`: Array of Layer objects.
- `idLayer`: Unique identifier for the layer.
- `labelLayer`: Use `"translate"` or a string.
- `visible`: Default visibility on the map.
- `selectedType`: The `valueType` that is selected by default.
- `minZoom`: (Optional) Minimum zoom level for the layer to be visible.
- `types`: An array of `valueType` strings that correspond to types defined in the OWS API or hardcoded in the server.

### Basemaps and Limits (`basemaps/*.json`, `limits/*.json`)
These files contain an array of Layer objects (without the `idGroup` wrapper).
