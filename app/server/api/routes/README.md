# API Routes & Parity

This directory contains the modularized route definitions for the FastAPI backend. 

## Routing Architecture

To maintain a clean and consistent API structure, routing is managed using a combination of **FastAPI APIRouter** in these files and **Global Prefixes** in `app/server-new/main.py`.

### Prefix Management
Most routers are included in `main.py` with a `/service` prefix. 

**Standard Pattern:**
1.  In `main.py`: `app.include_router(http.router, prefix="/service/http")`
2.  In `http.py`: `@router.post("/get")`
3.  **Resulting URL:** `/service/http/get`

> **Warning:** Do NOT repeat the prefix inside the individual route files (e.g., avoiding `@router.post("/service/http/get")`) as this creates redundant paths like `/service/http/service/http/get`.

## API Parity Guidelines

This backend is a migration of the original Node.js server. **Strict parity is mandatory** to ensure the Angular frontend functions without modification.

### Key Parity Requirements

1.  **URL Matching**: Every route must match the original endpoint exactly.
    *   *Example:* The OWS domain endpoint must be `/service/map/getowsdomain`, matching the old server, even if a name like `/host` seems more modern.
2.  **HTTP Method Matching**: Always use the same HTTP method as the original server.
    *   *Example:* `/service/http/get` MUST be a `POST` request because the frontend sends a body with the target URL.
3.  **Root Routes**: Some routes are served directly from the root without the `/service` prefix.
    *   *Example:* The `/ows` proxy route is registered in `main.py` without a prefix to allow `http://localhost:3000/ows`.

### Route Reference Table

| New Route File | Prefix in `main.py` | Key Endpoints | Original Node Route |
| :--- | :--- | :--- | :--- |
| `map.py` | `/service/map` | `/descriptor`, `/getowsdomain` | Matches exactly |
| `charts.py` | `/service/charts` | `/resumo`, `/pastureGraph` | Matches exactly |
| `http.py` | `/service/http` | `/get` (POST) | `/service/http/get` |
| `contact.py` | `/service/contact` | `/create` (POST) | `/service/contact/create` |
| `download.py` | `/service/download` | `/` (POST) | `/service/download` |
| `upload.py` | `/service/upload` | `/savegeom`, `/savefile` | Matches exactly |
| `proxy.py` | *None* | `/ows` | `/ows` |

## Data Injection & Middleware

Routes that require spatial data from the database (like `extent`, `search`, or `charts`) use the `data_injector` dependency. This replicates the `express-load` middleware from the old server, populating `request.state.query_result` with the results of pre-defined SQL queries.

```python
@router.get("/resumo", dependencies=[Depends(data_injector)])
async def handle_resumo(request: Request):
    data = request.state.query_result
    # ... logic
```
