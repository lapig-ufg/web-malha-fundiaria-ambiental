# Malha Fundiária Ambiental - Overview

This project is a comprehensive geospatial platform for visualizing and analyzing environmental land registry data in Brazil. Originally built upon the "Atlas das Pastagens" foundation, it has evolved into a dedicated tool for environmental land governance.

## Directory Structure

- `app/client/`: An Angular 16 application that provides the user interface, map platform, and hotsite pages.
- `app/server/`: A Node.js (Express.js) application that serves the frontend, provides an API for data retrieval, and interacts with databases.
- `scripts/`: Python-based data ingestion pipeline for processing and loading large datasets.
- `data/`: Storage for source data files (e.g., large Parquet files).
- `docs/`: Technical documentation and metadata descriptions.

## Core Technologies

### Frontend (Client)
- **Framework**: Angular 16
- **Map Engine**: OpenLayers (`ol`, `ol-ext`)
- **UI Components**: PrimeNG, Angular Material
- **Geospatial Analysis**: Turf.js
- **Charts**: Chart.js
- **Internationalization**: ngx-translate

### Backend (Server)
- **Framework**: Express.js
- **Databases**: PostgreSQL/PostGIS (Spatial), MongoDB (Sessions)
- **Data Conversion**: `ogr2ogr`
- **File Handling**: `archiver`, `multer`
- **Configuration**: `dotenv`, `express-load`

### Ingestion Pipeline (Scripts)
- **Language**: Python 3.12+
- **Database Engine**: DuckDB (for fast Parquet processing)
- **GIS Tools**: GeoPandas, GeoAlchemy2, PostGIS
- **Package Manager**: `uv`

## High-Level Architecture

The application follows a modular architecture:

1.  **Ingestion Phase**: Python scripts process raw `.parquet` files from the `/data` directory using DuckDB and load them into a PostGIS-enabled PostgreSQL database.
2.  **Server Phase**: The Node.js server acts as an API gateway, handling requests for map descriptors, region searches, and statistical data. It interacts with PostGIS for spatial queries.
3.  **Client Phase**: The Angular application renders the map interface, manages user interactions, and displays dynamic charts and statistics.
