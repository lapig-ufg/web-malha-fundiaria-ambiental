# Layer Management Guide

This document explains how layers are managed in the Malha Fundiária Ambiental project, covering the entire lifecycle from data ingestion to client-side display.

## Architecture Overview

The system uses a **Descriptor-based architecture** to manage map layers. A "Descriptor" is a JSON object that defines the hierarchy of groups and layers, along with their metadata and available visualization types.

### 1. Data Ingestion (PostgreSQL/PostGIS)
Spatial data is stored in a **PostgreSQL** database with the **PostGIS** extension.
- **Scripts:** Data is typically ingested using Python scripts located in the `/scripts` directory.
- **Source:** Ingestion scripts often process `.parquet` files and load them into PostGIS tables.
- **Metadata:** Database tables should follow project naming conventions and include necessary spatial indexes.

### 2. Backend Configuration (Descriptor)
 The server dynamically builds the map configuration (Descriptor) by merging local JSON definitions with external OWS API data.

- **JSON Definitions:** Found in `app/server/descriptor/groups/`. Each file (e.g., `pasture.json`, `infraestrutura.json`) defines a set of groups and the layers within them.
- **Group Ordering:** The order in which groups appear in the UI is defined in `app/server/utils/descriptorBuilder.js` within the `getGroupsOrder` method.
- **Descriptor Builder:** `app/server/utils/descriptorBuilder.js` reads the JSON files and instantiates `Group` and `Layer` models.
- **External Integration:** The `map.js` controller fetches detailed layer definitions (capabilities, URLs) from an external OWS API (`process.env.OWS_API`) and merges them into the local descriptor.

### 3. Frontend Integration (Angular & OpenLayers)
The client application consumes the Descriptor and translates it into OpenLayers map layers.

- **`DescriptorService`:** Fetches the descriptor from the server (`/service/map/descriptor`) and manages its state. It uses a `dirtyBit` system to signal changes (visibility, transparency, type) to other components.
- **`LayerService`:** A factory service that creates OpenLayers `TileLayer` instances (supporting WMTS and XYZ) based on the definitions in the Descriptor.
- **`GeneralMapComponent`:** The main map component that:
    - Subscribes to the `DescriptorService`.
    - Initializes layers on the map via `MapService`.
    - Handles reactive updates when the Descriptor changes.
- **`MapService`:** Provides a high-level API for interacting with the OpenLayers `Map` object (adding/removing/updating layers).

### 4. UI & Translations
- **`LayersSidebarComponent`:** Renders the layer hierarchy in the left sidebar, allowing users to interact with layers.
- **Translations:** UI labels for groups and layers should be configured as `"translate"` in the JSON descriptor. The actual labels are defined in `app/client/src/assets/locales/` (`en.json` and `pt.json`).

---

## How to Add a New Layer

Follow these steps to add a new layer to the platform:

### Step 1: Ingest Spatial Data
1.  Prepare your spatial data (e.g., in `.parquet` or `.shp` format).
2.  Use or create an ingestion script in `/scripts` to load the data into the PostGIS database.
3.  Ensure the layer is registered and served via a MapServer/OWS service (internal or external).

### Step 2: Update Descriptor
1.  Open or create a JSON file in `app/server/descriptor/groups/` (e.g., `new_layers.json`).
2.  Add the layer definition:
    ```json
    {
      "idGroup": "my_new_group",
      "labelGroup": "translate",
      "layers": [
        {
          "idLayer": "my_new_layer",
          "labelLayer": "translate",
          "visible": false,
          "types": ["layer_type_name_from_ows_api"]
        }
      ]
    }
    ```
3.  If you created a new group, add its ID to the `getGroupsOrder` array in `app/server/utils/descriptorBuilder.js`.

### Step 3: Add Translations
1.  Open `app/client/src/assets/locales/en.json` and `app/client/src/assets/locales/pt.json`.
2.  Add the labels for your new group and layer:
    ```json
    "descriptor_labels": {
      "groups": {
        "my_new_group": {
          "labelGroup": "My New Group",
          "layers": {
            "my_new_layer": {
              "labelLayer": "My New Layer"
            }
          }
        }
      }
    }
    ```

### Step 4: Verify
1.  Restart the backend server.
2.  Refresh the client application.
3.  Check the "Layers" sidebar to see your new group and layer.

---

## How to Modify/Remove a Layer

- **To Modify:** Update the corresponding entry in the JSON files in `app/server/descriptor/groups/` or the translation files in `app/client/src/assets/locales/`.
- **To Remove:** Delete the layer entry from the JSON file. If a group becomes empty, you can also remove the group entry.
