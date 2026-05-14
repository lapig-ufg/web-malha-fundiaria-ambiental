# Data Ingestion Pipeline

The project uses a high-performance Python-based pipeline to ingest large geospatial datasets into the PostgreSQL/PostGIS database.

## Overview

The ingestion process is designed to handle multi-gigabyte `.parquet` files efficiently. It leverages **DuckDB** for fast column-wise reading and the **PostgreSQL extension for DuckDB** to transfer data directly to the database.

## Key Components

- **Source Data**: Located in the `/data` directory as `.parquet` files.
- **Ingestion Scripts**: Located in the `/scripts` directory.
- **Core Script**: `main.py` handles the logic for connecting to databases, processing geometries, and managing the transfer.

## Workflow

1.  **Environment Setup**:
    - Uses `uv` for dependency management.
    - Configuration is loaded from `.env` (database credentials).

2.  **DuckDB Ingestion**:
    - The script initializes an in-memory DuckDB instance.
    - It installs and loads `spatial` and `postgres` extensions for DuckDB.
    - It attaches the target PostgreSQL database using the `ATTACH` command.

3.  **Data Processing**:
    - Files are read from `/data`.
    - Column names are normalized to lowercase.
    - The `geom` or `geometry` column is identified and renamed to `geom`.
    - An identifier column (like `geo_id` or `geocodigo`) is identified and renamed to `gid`.

4.  **Database Transfer**:
    - Data is transferred from DuckDB to PostgreSQL using `CREATE TABLE AS SELECT` or `INSERT INTO`.
    - Geometries are transformed from their original projection (typically **ESRI:102033 - South America Albers**) to **SIRGAS 2000 (SRID 4674)** using PostGIS functions:
      ```sql
      ALTER TABLE "{table_name}" 
      ALTER COLUMN "geom" TYPE geometry(MultiPolygon, 4674) 
      USING ST_Multi(ST_Transform(ST_Force2D(ST_SetSRID("geom"::geometry, 102033)), 4674));
      ```
    - A `SERIAL PRIMARY KEY` is added to the `gid` column if it doesn't already exist.

## Performance Optimization

- **DuckDB**: Provides extremely fast reading of Parquet files compared to standard Python libraries.
- **Direct Transfer**: The DuckDB-Postgres extension minimizes data movement through the Python layer.
- **Batched Inserts**: If the direct table creation fails, the script falls back to batched inserts.

## How to Run

1. Ensure the PostgreSQL database is running and PostGIS is enabled.
2. Navigate to the `/scripts` folder.
3. Run:
   ```bash
   uv run main.py
   ```
