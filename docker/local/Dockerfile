# Multi-stage image for running the whole app (Angular client + FastAPI server)
# with a single `docker compose up`, without needing a pre-built app/client/dist.
#
# The production image at docker/prod/Dockerfile expects CI to build the client
# beforehand (see .github/workflows/deploy.yml). This one builds it itself, so
# it's meant for local/dev use via ../../docker-compose.yml.

# ---- Stage 1: build the Angular client ----
FROM node:22-bookworm-slim AS client-build

WORKDIR /build/client

COPY app/client/package.json app/client/package-lock.json ./
RUN npm ci

COPY app/client/ ./
RUN npm run build -- --configuration production

# ---- Stage 2: FastAPI server + built client ----
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

LABEL maintainer="LAPIG/UFG"

# GDAL is needed for the geospatial routes (zonal statistics, COG rendering, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gdal-bin \
    libgdal-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /APP/web-malha-fundiaria-ambiental

ENV UV_COMPILE_BYTECODE=1
ENV PYTHONUNBUFFERED=1

# Copy the whole repo (server code, descriptor JSON, locales, tools, etc.)
COPY . .

# Drop in the client build produced by stage 1, matching CLIENT_DIR in
# app/server/core/config.py (../client/dist/malha-fundiaria-ambiental/)
COPY --from=client-build /build/client/dist ./app/client/dist

WORKDIR /APP/web-malha-fundiaria-ambiental/app/server
RUN uv sync --frozen

EXPOSE 3000

CMD ["uv", "run", "main.py"]
