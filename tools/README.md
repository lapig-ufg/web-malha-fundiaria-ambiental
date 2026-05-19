# Project Tools & Utilities

This directory contains a collection of independent Python scripts used for data management, database maintenance, and API utilities for the Malha Fundiária project.

## Directory Structure

- **`/api-utils`**: Tools for interacting with or mapping APIs.
  - `model_generator.py`: Generates Python class models from API JSON responses.
- **`/data-ingestion`**: Scripts for importing data into the system.
  - `ingest_parquet.py`: Ingests `.parquet` files from the `/data` directory into PostGIS using DuckDB.
- **`/db-maintenance`**: Scripts for one-time fixes or database adjustments.
  - `fix_gid_column.py`: Ensures the `gid` column exists and is set as a SERIAL PRIMARY KEY in specific tables.
- **`/descriptors`**: Utilities for managing and comparing map configuration descriptors.
  - `compare_servers.py`: Compares map descriptors between old (Node.js) and new (Python) server implementations.

## Setup

These scripts use `uv` for dependency management. To run any script, ensure you are in the `tools` directory and have `uv` installed.

1.  **Environment Variables:** Copy `.env.example` to `.env` in this directory and configure your database credentials.
2.  **Running a script:** Use `uv run` to execute a script with its dependencies:
    ```bash
    uv run data-ingestion/ingest_parquet.py
    ```

## Development

Each script is designed to be independent. When adding a new utility:
1. Create a meaningful subdirectory (or use an existing one).
2. Ensure the script handles its own configuration (e.g., loading `.env`).
3. Update this README if necessary.
