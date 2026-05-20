# Malha Fundiária Ambiental

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A comprehensive geospatial platform for visualizing and analyzing environmental land registry data in Brazil. This platform consolidates complex land tenure and environmental datasets to drive governance, technical analysis, and sustainable territory management.

Developed by the **Laboratório de Processamento de Imagens e Geoprocessamento (LAPIG)** at the **Universidade Federal de Goiás (UFG)**.

## 📌 Project Purpose

The primary goal of this application is to share and provide access to the data developed through the **Land Tenure Methodology**. It serves as an integrated geospatial infrastructure that connects land registry data ("Malha Fundiária") with environmental indicators, allowing users to:

- Visualize consolidated territorial structures.
- Analyze overlaps with protected areas (Units of Conservation, Indigenous Lands, etc.).
- Access environmental assets like permanent preservation areas (APP) and legal reserves (RL).
- Export qualified geospatial data for local and regional analysis.

## 🛠️ Tech Stack

### Frontend (Client)
- **Framework:** Angular 20
- **Mapping:** OpenLayers v10 (`ol`, `ol-ext`), Turf.js (client-side analysis)
- **UI Components:** PrimeNG v17, Angular Material v20, PrimeFlex
- **Internationalization:** `ngx-translate`
- **Charts:** Chart.js

### Backend (Server)
- **Runtime:** Node.js (Express.js)
- **Databases:** 
  - **PostgreSQL/PostGIS:** Primary spatial data storage.
  - **MongoDB:** Session and metadata management.

---

## 📐 Land Tenure Methodology

The platform is built upon a rigorous 6-step technical process:

1.  **Data Ingestion:** Collection of land and territorial bases (private properties, indigenous lands, conservation units).
2.  **Pre-processing:** Correction of geometric inconsistencies and removal of duplicates.
3.  **Hierarchization:** Definition of priorities between territorial layers using multi-criteria analysis (AHP).
4.  **Layer Reclassification:** Conversion of layers to a continuous raster grid where each pixel represents a priority class.
5.  **Overlap Analysis:** Resolution of conflicts by maintaining the highest priority land class in each pixel.
6.  **Environmental Integration:** Incorporation of environmental assets to allow for compliance analysis and statistics.

For more details, visit the [Full Methodology Documentation](https://boliveirageo.github.io/malhafundiariaambiental/).

---

## 🚀 Getting Started

### Prerequisites
- Node.js (v18+)
- Python (3.12+) with `uv`
- Docker (optional, for containerized deployment)
- PostgreSQL with PostGIS extension
- MongoDB

### Installation

#### 1. Backend (Server)
```bash
cd app/server
npm install
cp .env.example .env # Configure your DB credentials
npm start
```

#### 2. Frontend (Client)
```bash
cd app/client
npm install
npm start # Accessible at http://localhost:4200
```

## 📁 Repository Structure
- `app/client`: Angular frontend source code.
- `app/server`: Node.js backend source code.
- `docs/`: Technical documentation and data models.
- `docker/`: Deployment configurations.

---

## 📄 License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🤝 Contact
**Laboratório de Processamento de Imagens e Geoprocessamento (LAPIG)**
Universidade Federal de Goiás (UFG)
[lapig.iesa.ufg.br](https://lapig.iesa.ufg.br/)
