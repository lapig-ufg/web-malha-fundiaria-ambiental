# Use a Python base image with uv installed
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

LABEL maintainer="Tiago Gonçalves <tiagogoncalves@discente.ufg.br>"

# Install system dependencies (GDAL is often needed for LAPIG projects)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gdal-bin \
    libgdal-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /APP/web-malha-fundiaria-ambiental

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV NODE_ENV=prod

# Copy project files
# We expect app/client/dist to be already built by the CI
COPY . .

# Install backend dependencies
WORKDIR /APP/web-malha-fundiaria-ambiental/app/server
RUN uv sync --frozen

# Expose the port defined in app/server/core/config.py
EXPOSE 3000

# Command to run the application
CMD ["uv", "run", "main.py"]
