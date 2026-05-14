# Gemini CLI Instructions - Malha Fundiária Ambiental

This file provides architectural context and development guidelines for the "Malha Fundiária Ambiental" project.

> **Note:** This project is a new initiative focused on environmental land registry, built upon the foundation of the "Atlas das Pastagens Brasileiras" (Brazilian Pasture Atlas).

## Project Overview

The project is a comprehensive geospatial platform for visualizing and analyzing environmental land registry data in Brazil.
 It consolidates land registry data ("Malha Fundiária") and provides tools for region filtering, statistical analysis, and data export.

### Tech Stack

- **Frontend:**
  - **Framework:** Angular 16
  - **Mapping:** OpenLayers (`ol`, `ol-ext`), Turf.js (client-side analysis)
  - **UI Components:** PrimeNG, Angular Material, PrimeFlex
  - **Charts:** Chart.js
  - **Internationalization:** `ngx-translate`
- **Backend:**
  - **Runtime:** Node.js
  - **Framework:** Express.js
  - **Databases:** PostgreSQL with PostGIS extension (Primary spatial data), MongoDB (Sessions/Metadata)
  - **Dependency Injection:** `express-load`
  - **Tools:** `ogr2ogr` (data conversion), `duckdb` (via Python scripts for ingestion)
- **Data Ingestion:**
  - **Language:** Python 3.12+
  - **Tools:** `uv` (package management), `DuckDB`, `psycopg2`, `geopandas`
- **Infrastructure:** Docker (separate Dockerfiles for dev and prod)

## Directory Structure

- `/app/client`: Angular frontend application. (See [client_architecture.md](docs/client_architecture.md))
- `/app/server`: Node.js backend application. (See [server_architecture.md](docs/server_architecture.md))
- `/scripts`: Python scripts for data ingestion. (See [data_ingestion.md](docs/data_ingestion.md))
- `/data`: Source data files. (See [dataset_metadata.md](docs/dataset_metadata.md))
- `/docs`: Detailed architectural and metadata documentation. (See [app_overview.md](docs/app_overview.md))
- `/docker`: Docker configuration files.

## Getting Started

### Backend Setup (Server)
1.  Navigate to `app/server`.
2.  Install dependencies: `npm install`.
3.  Configure environment: Copy `.env.example` to `.env` and fill in the database credentials.
4.  Run the server: `npm start` or `node app.js`.

### Frontend Setup (Client)
1.  Navigate to `app/client`.
2.  Install dependencies: `npm install`.
3.  Run the dev server: `npm start` (serves on `http://localhost:4200` with proxy to backend).
4.  Build for production: `npm run build`.

### Data Ingestion (Python)
1.  Navigate to `scripts`.
2.  Ensure `uv` is installed.
3.  Run ingestion: `uv run main.py`.
    *   *Note: This script ingests `.parquet` files from the `/data` directory into PostGIS.*

## Development Conventions

### General
- **Internationalization:** All user-facing strings in the client should use `ngx-translate`.
- **Environment Variables:** Always use `.env` for secrets and environment-specific configs. Do not commit `.env` files.

### Client (Angular)
- **Mapping Logic:** Encapsulate map interactions in `MapService`. Use OpenLayers primitives where possible.
- **State Management:** Prefer RxJS `BehaviorSubject` in services over complex state management libraries for simple states.
- **Styling:** Use SCSS and PrimeFlex utility classes.

### Server (Node.js)
- **Layer Descriptor:** The "descriptor" (map configuration) is built dynamically. See `app/server/utils/descriptorBuilder.js` (inferred) and `app/server/descriptor/` JSON files.
- **SQL Queries:** Organized by domain in `app/server/database/queries/`. Always use parameterized queries to prevent SQL injection.
- **Proxying:** Use the built-in proxy controller for external OWS requests to avoid CORS issues.

## Important Links & APIs
- **OWS API:** `https://ows.lapig.iesa.ufg.br/api`
- **Map Services:** `https://ows.lapig.iesa.ufg.br/ows`
- **S3 Storage:** `https://s3.lapig.iesa.ufg.br/storage/`
