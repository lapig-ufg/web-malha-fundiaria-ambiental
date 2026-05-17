# Map Data Models

This directory contains the Python data models that represent the structures fetched from the external **OWS API**. These models define the schemas for layers, basemaps, and geographic limits used by the platform.

The models documented here are used to understand the data contract between the backend services and the geospatial data provider.

---

## Table of Contents

1. [Descriptor Orchestration](#descriptor-orchestration)
2. [Layers Model](#1-layers-model)
3. [Basemaps Model](#2-basemaps-model)
4. [Limits Model](#3-limits-model)
5. [Common Structures](#common-structures)

---

## Descriptor Orchestration

The platform's main configuration, called the **Descriptor**, is a hybrid structure created by merging local configuration files ("Skeletons") with dynamic data from the external OWS API ("Enrichment").

### 1. Local Configuration (Skeletons)
Located in `/app/server/descriptor/`, these JSON files define the hierarchy and UI organization:
- **Groups:** `/descriptor/groups/*.json` (e.g., `pasture.json`)
- **Basemaps:** `/descriptor/basemaps/*.json`
- **Limits:** `/descriptor/limits/*.json`

**Skeleton Structure Example:**
```json
{
  "idGroup": "pasture_group",
  "labelGroup": "translate",
  "groupExpanded": true,
  "layers": [
    {
      "idLayer": "pasture_layer",
      "labelLayer": "translate",
      "visible": true,
      "selectedType": "pasture_col9_s100",
      "types": ["pasture_col9_s100"] 
    }
  ]
}
```
*Note: The string `"translate"` indicates the label will be resolved via localization files.*

### 2. External Data (Enrichment)
The backend fetches a complete list of `layertypes` from the OWS API. Each object in this list contains technical details like `origin`, `metadata`, `filters`, and `download` options (as defined in the [Layers Model](#1-layers-model)).

### 3. The Merge Process
The `DescriptorBuilder` orchestrates the final object:
1. **Fetch:** Retrieves all `layertypes`, `basemaps`, and `limits` from the OWS API.
2. **Iterate:** Traverses the local Skeleton files.
3. **Match:** For every item in the `types` array of a layer, it finds the corresponding object in the OWS data where `valueType` matches.
4. **Resolve:** Replaces `"translate"` markers with actual localized strings.
5. **Combine:** Injects the full OWS object into the `types` array.

### 4. Final Result
The final Descriptor is sent to the frontend, providing a complete, ready-to-render map configuration with both organizational hierarchy and technical metadata.

---

## Common Structures

These sub-models are shared or similar across the different API endpoints.

### Origin
Defines the source and type of the map service.
```python
class Origin:
    sourceService: str  # e.g., "internal", "external"
    typeOfTMS: str      # e.g., "xyz", "wms"
    url: str | None     # Base URL for the service
    epsg: str | None    # Coordinate reference system (e.g., "EPSG:3857")
```

### Metadata
Contains descriptive information about the layer.
```python
class Metadata:
    title: str
    description: str
```

### WFS Map Card
Configures how feature information is displayed when clicking on the map.
```python
class WfsMapCard:
    show: bool
    attributes: list[DisplayMapCardAttribute] | None
    displayMapCardAttributes: list[DisplayMapCardAttributes] | None
```

### Display Map Card Attribute
Definition of a single attribute field in the map card.
```python
class DisplayMapCardAttribute:
    column: str
    label: str
    columnType: str
```

---

## 1. Layers Model

**Endpoint:** `https://ows.lapig.iesa.ufg.br/api/map/layers?lang=pt`

This model represents the main thematic layers of the platform, including their filters and download options.

### Class Definition

```python
class Layer:
    valueType: str
    type: str  # Always "layertype"
    origin: Origin
    typeLayer: str  # "vectorial" or "raster"
    viewValueType: str  # Display name
    typeLabel: str
    wfsMapCard: WfsMapCard
    download: Download
    regionFilter: bool
    filters: list[Filter] | None
    filterLabel: str | None
    filterSelected: str | None
    filterHandler: str | None
    visible: bool
    opacity: float
    metadata: list[Metadata]
    gallery: Gallery | None

class Download:
    csv: bool
    shp: bool
    gpkg: bool
    raster: str | bool
    layerTypeName: str | None

class Filter:
    valueFilter: str
    viewValueFilter: int | str

class Gallery:
    id_column: str
    tableName: str
```

### Example JSON

```json
{
  "valueType": "pasture_col9_s100",
  "type": "layertype",
  "origin": {
    "sourceService": "internal",
    "typeOfTMS": "xyz"
  },
  "typeLayer": "vectorial",
  "viewValueType": "Área de Pastagem",
  "typeLabel": "Tipo",
  "wfsMapCard": {
    "show": false,
    "attributes": [
      {
        "column": "area_ha",
        "label": "Área do polígono (ha)",
        "columnType": "double"
      },
      {
        "column": "year",
        "label": "Ano",
        "columnType": "string"
      }
    ]
  },
  "download": {
    "csv": true,
    "shp": false,
    "gpkg": true,
    "raster": false,
    "layerTypeName": "pasture_col9"
  },
  "regionFilter": true,
  "filters": [
    {
      "valueFilter": "year=2023",
      "viewValueFilter": 2023
    }
  ],
  "filterLabel": "Ano",
  "filterSelected": "year=2023",
  "filterHandler": "msfilter",
  "visible": false,
  "opacity": 1.0,
  "metadata": [
    {
      "title": "Metadados",
      "description": "Áreas de Pastagens do Brasil"
    }
  ]
}
```

---

## 2. Basemaps Model

**Endpoint:** `https://ows.lapig.iesa.ufg.br/api/map/basemaps?lang=pt`

Defines the background maps available in the platform.

### Class Definition

```python
class Basemap:
    valueType: str
    type: str  # Always "basemap"
    origin: Origin
    viewValueType: str
    wfsMapCard: WfsMapCard
    visible: bool
    opacity: float
    metadata: list[Metadata]
```

### Example JSON

```json
{
  "valueType": "mapbox",
  "type": "basemap",
  "origin": {
    "sourceService": "internal",
    "typeOfTMS": "xyz"
  },
  "viewValueType": "Geopolítico",
  "wfsMapCard": {
    "show": false,
    "attributes": []
  },
  "visible": true,
  "opacity": 1.0,
  "metadata": [
    {
      "title": "Descrição",
      "description": "Mapa base geopolítico provido pelo Mapbox."
    }
  ]
}
```

---

## 3. Limits Model

**Endpoint:** `https://ows.lapig.iesa.ufg.br/api/map/limits?lang=pt`

Represents administrative or geographic boundaries (e.g., States, Municipalities, Biomes).

### Class Definition

```python
class Limit:
    valueType: str
    type: str  # Always "limit"
    origin: Origin
    typeLayer: str
    viewValueType: str
    wfsMapCard: WfsMapCard
    layerLimits: bool
    visible: bool
    opacity: float
    metadata: list[Metadata]
```

### Example JSON

```json
{
  "valueType": "estados",
  "type": "limit",
  "origin": {
    "sourceService": "internal",
    "typeOfTMS": "xyz"
  },
  "typeLayer": "vectorial",
  "viewValueType": "Estados do Brasil",
  "wfsMapCard": {
    "show": false,
    "attributes": [
      {
        "column": "estado",
        "label": "Estado",
        "columnType": "string"
      }
    ]
  },
  "layerLimits": true,
  "visible": true,
  "opacity": 1.0,
  "metadata": [
    {
      "title": "Descrição",
      "description": "Limites dos Estados do Brasil - IBGE."
    }
  ]
}
```

---

## Notes on Internationalization

All three endpoints support the `lang` query parameter (e.g., `?lang=pt`, `?lang=en`). This affects:
- `viewValueType`
- `typeLabel`
- `filterLabel`
- `metadata` (titles and descriptions)
- `wfsMapCard` labels