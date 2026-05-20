# Malha Fundiária Ambiental - Python Backend

This is the Python migration of the Malha Fundiária Ambiental server, built with **FastAPI**.

## Prerequisites

- Python 3.12+
- [uv](https://github.com/astral-sh/uv) (Fast Python package manager)

## Getting Started

### 1. Environment Configuration

Copy the example environment file from the original server (if applicable) or create a `.env` file in this directory with the necessary database and API credentials:

```bash
# Database
PG_USER=your_user
PG_PASSWORD=your_password
PG_HOST=your_host
PG_PORT=5432
PG_DATABASE_LAPIG=your_db
PG_DATABASE_GENERAL=your_db_general

# APIs
OWS_API=https://ows.lapig.iesa.ufg.br/api
OWS_HOST=https://ows.lapig.iesa.ufg.br

# Auth (Keycloak)
AUTH_URL=https://auth.lapig.iesa.ufg.br
AUTH_REALM=lapig
AUTH_ID=your_client_id
AUTH_SECRET=your_client_secret

# Security
RECAPTCHA_KEY=your_recaptcha_secret
```

### 2. Install Dependencies

Using `uv`, you can install dependencies and create a virtual environment in one command:

```bash
uv sync
```

### 3. Running the Server

To start the development server with hot-reload:

```bash
uv run python main.py
```

The server will be available at `http://localhost:3000` (or the port defined in `core/config.py`).

## Project Structure

- `main.py`: Application entry point and route registration.
- `api/routes/`: Modularized API endpoints. See [api/routes/README.md](api/routes/README.md) for routing architecture and parity guidelines.
- `core/`: Core configurations and settings management.
- `db/`: Database connection logic and SQL query templates.
- `models/`: Pydantic models and data structures. See [models/README.md](models/README.md) for OWS API schemas and descriptor documentation.
- `utils/`: Utility functions and helper classes.

## Features

- **Asynchronous I/O**: High-performance request handling using `FastAPI` and `asyncpg`.
- **Dynamic Descriptor**: Automatically builds map configuration from OWS API and local metadata.
- **Spatial Analysis**: Integrated endpoints for region search and statistical data.
- **Secure File Handling**: Validated upload and download processes with Keycloak integration.
