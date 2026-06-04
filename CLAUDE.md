# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this project is

A geospatial web platform (LAPIG/UFG) that visualizes Brazilian land-tenure and environmental data: an Angular 20 SPA, a Python/FastAPI backend, and a Parquet-to-PostGIS ingestion pipeline. Live at `malhafundiaria.lapig.ufg.br`. Forked from "Atlas das Pastagens".

## Quick start

The repo has **three independent sub-projects** — no monorepo tooling ties them together.

### Client (`app/client/`, Angular 20)

```bash
cd app/client
npm install
npm start            # ng serve, http://localhost:4200, proxies /service and /ows to :3000
npm run build        # production build to dist/malha-fundiaria-ambiental/
npm test             # Karma + Jasmine (no test files currently exist)
```

EditorConfig: 2-space indent, single quotes for TS (see `app/client/.editorconfig`).
No ESLint/Prettier configured.

### Server (`app/server/`, Python FastAPI)

```bash
cd app/server
uv sync              # Python 3.14+, deps via pyproject.toml
cp .env.example .env # fill in PG, OWS_API, OWS_HOST, AUTH_* (Keycloak), RECAPTCHA_KEY
uv run python main.py  # uvicorn on :3000, reload=True
```

The server **serves the built Angular bundle as static files** from `app/client/dist` (see `main.py` lines 39-59), so the FastAPI process is the only deployable artifact.

### Tools (`tools/`) and scripts (`scripts/`)

Standalone Python utilities (data-pipeline ingestion, api-utils model generation, descriptor diff against the old Node server, tif-explorer, zonal statistics).

```bash
cd tools && uv sync && uv run <script-path>
cd scripts && uv run <script>     # no project file, uses system Python
```

### Full local stack

1. `cd app/server && uv run python main.py` (port 3000)
2. `cd app/client && npm start` (port 4200) — Angular dev server proxies `/service/*` and `/ows` to the FastAPI server.

### Tests / lint

There are **no configured Python tests or lint tools**. Client has Karma+Jasmine wired up but no specs. CI does not run any tests — it only builds (`npm run build -- --configuration production`) and deploys.

## Repository layout

```
app/client/          Angular 20 SPA — see docs/client_architecture.md
app/server/          FastAPI backend (Python) — see docs/server_architecture.md
scripts/             One-off Python data utilities (no project file)
tools/               Reusable Python tools — see tools/README.md
docker/prod/         Production Dockerfile (assumes client dist/ pre-built)
docs/                Architecture, descriptor model, layer-management, data model
```

## Architecture at a glance

**Single deployable:** FastAPI process serves both the API (`/service/*`, `/ows`, `/tms`) and the compiled Angular SPA (catch-all in `main.py`).

**State management (no NgRx):** singleton Angular services with `BehaviorSubject` — `DescriptorService` (the whole map config), `RegionFilterService` (selected geography), `LocalizationService` (language in `localStorage`).

**Hybrid descriptor model:** a "Descriptor" is built per request by merging (a) local JSON skeletons in `app/server/descriptor/{groups,basemaps,limits}/` with (b) live layer metadata from an **external OWS API** at LAPIG. Client `DescriptorService` re-fetches on language change. See `docs/layer_management_guide.md`.

**Map data flow:**

- `LayerService` builds OpenLayers `TileLayer`s for `wmts`/`xyz`/`cog` source types; cycles through 4 OWS hosts (`OWS_O1..O4`) round-robin.
- Region filtering is enforced client-side via MapServer `MSFILTER` strings appended to tile URLs.
- A 10 m COG (`malha_fundiaria_cog`) is hard-coded in `app/server/api/routes/map.py` and rendered with `WebGLTile` + `GeoTIFF` in the browser.

**Database:** PostgreSQL/PostGIS only. Two `asyncpg` pools (`PG_DATABASE_LAPIG`, `PG_DATABASE_GENERAL`) defined in `app/server/db/session.py`. `motor` (MongoDB) is in `pyproject.toml` but **not used in the current Python server** — legacy from the Node migration. Bulk data: MinIO/S3 at `s3.lapig.iesa.ufg.br`. Geometries stored in SIRGAS 2000 (SRID 4674); sources ship in ESRI:102033 (transformation handled in `tools/data-pipeline/`).

**i18n:** `ngx-translate` + `pt|en` locale files in `app/client/src/assets/locales/`. Default `pt`. The server reads the same locale files to resolve `"translate"` markers in descriptor JSON.

## Critical non-obvious rules

1. **API parity is mandatory** (`app/server/api/routes/README.md`). Routes must match the legacy Node server exactly — same URL, same HTTP method, even when it looks weird. Example: `/service/map/getowsdomain` (not `/host`), `/service/http/get` is POST (body carries the target URL), `/ows` is root-mounted (no `/service` prefix). **Do not repeat the prefix inside route files.**

2. **The backend is mid-migration.** `app/server/README.md` is current (FastAPI/uv). The top-level `README.md` and `docs/server_architecture.md` still describe the legacy Node/Express server. When in doubt, follow the FastAPI code, not the old docs. Use `tools/descriptors/compare_servers.py` to diff descriptors between old (`:3001`) and new (`:3000`) servers.

3. **Descriptor group load order is hard-coded** in `DescriptorBuilder.get_groups_order()` — not alphabetical. New group JSON files are only picked up if their filename matches that allowlist. Currently: `malha_fundiaria`, `pasture`, `campo`, `inspecao_visual`, `agropecuaria`, `areas_declaradas`, `infraestrutura`, `areas_especiais`, `imagens`.

4. **SQL parameter style is custom, not parameterized.** `app/server/db/session.py:prepare_query` does naive `str.replace` of `${name}` / `${name}%` / `%${name}%` tokens. Values are uppercased to match Brazilian state codes (`'BA'`, `'SP'`); `unaccent` and `ILIKE` are used heavily. The Python server is a byte-for-byte port of the old Node SQL — preserve that semantics when editing queries.

5. **Adding a layer is a 4-step process** (`docs/layer_management_guide.md`): ingest → add to a JSON in `app/server/descriptor/groups/` → add labels to `app/client/src/assets/locales/{pt,en}.json` under `descriptor_labels` → restart server. Use `"translate"` in the JSON; the actual strings live in the locale files.

6. **The OWS API is a runtime dependency.** There is no offline snapshot. If `OWS_API` is unreachable, `/service/map/descriptor` returns 500. `app/server/api/routes/map.py` does try/except for individual layer-type fetches but the overall response will be partial.

7. **The Dockerfile expects `app/client/dist` to be pre-built by CI** (`.github/workflows/deploy.yml` runs `ng build` before the Docker build). Don't try to build the Angular app inside the container.

8. **No lint, no Python tests, no pre-commit hooks.** Don't go looking for `.eslintrc`, `pytest.ini`, or `ruff.toml` — they don't exist.

9. **`data/` is gitignored** — large parquet sources live there but are not in the repo. `scripts/download.py` and `scripts/download_parquet.py` fetch from MinIO.

10. **Mixed standalone + NgModule components** in the client. New code may be either, but the legacy feature modules (`map-platform`, `hotsite`) use classic `NgModule`-declared components.

11. **`uvicorn.run(..., reload=True)` is on by default in `main.py`.** Convenient for dev; consider turning off in production.

12. **CORS is wide open** (`allow_origins=["*"]`) in `main.py` — fine for a public map, flag before tightening.

## Where to read more

- `app/server/README.md` — FastAPI backend setup, env vars, project structure
- `app/server/api/routes/README.md` — routing architecture and **API parity contract** (read before touching any route)
- `app/server/descriptor/README.md` — descriptor JSON schema, group load order
- `app/server/models/README.md` — OWS API Pydantic schemas (`Layer`, `Basemap`, `Limit`)
- `app/server/descriptor/groups/*.json` — current map configuration
- `docs/app_overview.md` — high-level architecture (note: backend section is stale)
- `docs/client_architecture.md` — Angular module map
- `docs/server_architecture.md` — old Node server architecture (legacy reference)
- `docs/layer_management_guide.md` — **how to add/modify/remove a layer end-to-end**
- `docs/map_data_model.md` — descriptor/group/layer/type model and chart data flow
- `docs/data_ingestion.md` — Parquet → PostGIS pipeline, ESRI:102033 → SIRGAS 4674 transformation
- `docs/dataset_metadata.md` — schemas of the 3 source parquet files (bilingual)
- `tools/README.md` — developer utilities
- `app/client/src/app/@core/services/descriptor.service.ts` — client-side state of the entire map config
- `app/client/src/app/@core/services/map.service.ts` — OpenLayers wrapper, projection registrations
- `app/client/src/app/@core/services/layer.service.ts` — OL `TileLayer` factory + round-robin OWS hosts
