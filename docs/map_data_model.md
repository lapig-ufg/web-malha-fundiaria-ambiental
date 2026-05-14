# Malha Fundiária Ambiental - Data Model

The application revolves around the visualization and analysis of geospatial layers across different regions of Brazil.

## Map Layers (Descriptors)

The map configuration is driven by a "descriptor" object. This object defines which layers are available, how they are grouped in the UI, and where their data comes from.

### Layer Hierarchy
- **Groups**: High-level categories (e.g., Agropecuária, Pastagem, Infraestrutura).
- **Layers**: Specific datasets within a group (e.g., Lotação Bovina, Floresta Plantada).
- **Layer Types**: The technical implementation of a layer. A single layer can have multiple types (e.g., different years or different data sources for the same phenomenon).

### Data Sources
Layers are typically served as:
- **WMS/WMTS**: For tiled map visualization.
- **GeoJSON**: For vector data (often used for search results or small datasets).

## Geographical Regions

The application supports filtering and analysis by different regional levels:
- **Country**: Brazil as a whole.
- **Biomes**: Amazônia, Cerrado, Caatinga, Mata Atlântica, Pampa, Pantanal.
- **States (UF)**: The 27 Brazilian federative units.
- **Municipalities**: Over 5,000 local administrative units.

### Region Geometry
Geometries for these regions are stored in the PostgreSQL database, typically in a table like `regions_geom`. The `map.js` query utility uses these geometries to:
- Zoom to a selected region (fetching the extent).
- Perform spatial intersections for statistics.

## Internationalization

Layer labels and UI text are translated using `ngx-translate` on the client. The backend also supports multiple languages by passing a `lang` parameter to descriptor and search requests, ensuring that labels (like group names) are returned in the requested language.

## Statistics and Charts

When a region is selected, the application fetches statistical data (e.g., pasture area over time).
- **Backend**: Executes SQL queries (in `database/queries/charts.js`) against the PostgreSQL database.
- **Frontend**: Receives the data and uses `Chart.js` to render interactive charts in the `StatisticsSidebar`.
