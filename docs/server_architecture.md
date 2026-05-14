# Server Architecture (Malha Fundiária Ambiental)

The backend is a Node.js application built with the Express.js framework. It serves as an API gateway, data orchestrator, and static file server for the Angular client.

## Core Structure

The server uses `express-load` to automatically load and inject dependencies into the `app` object. The loading order is:

1.  `config.js`: Loads environment variables and application settings.
2.  `database/`: Initializes database clients (PostgreSQL and MongoDB).
3.  `middleware/`: Registers global and route-specific middleware (CORS, compression, body-paser, etc.).
4.  `controllers/`: Contains the business logic for handling requests.
5.  `routes/`: Defines the API endpoints and maps them to controllers.
6.  `utils/`: Shared utility functions.

## Key Components

### Controllers
- `map.js`: Handles map-related requests like fetching the layer descriptor and searching for regions.
- `charts.js`: Processes requests for statistical data and formats it for Chart.js.
- `upload.js`: Manages user file uploads (e.g., shapefiles) and converts them to GeoJSON using `ogr2ogr`.
- `download.js`: Handles data export requests, creating ZIP archives of requested data.
- `proxy.js`: Proxies requests to external OWS services to handle CORS and potentially cache responses.

### Data Layer
- `database/client.js`: Managed the connection pool for PostgreSQL (using `pg`).
- `database/queries/`: Contains SQL query templates organized by domain (e.g., `map.js`, `charts.js`).
- `descriptor/`: A directory containing JSON files that define the structure and groupings of map layers.

### Descriptor Building Logic
The server dynamically builds the "descriptor" sent to the client. It:
1.  Reads local JSON files in `descriptor/groups/`.
2.  Fetches technical layer details (URLs, styles, names) from an external **OWS API** (defined by `OWS_API` in `.env`).
3.  Merges these sources to create a complete map configuration object.

## Database Interaction
- **PostgreSQL**: Used for most spatial queries and relational data. Uses `unaccent` and `ILIKE` for flexible searching.
- **MongoDB**: Used for session management and potentially other document-based data (referenced in `package.json` and `app.js`).

## Deployment and Scaling
- The application can be run in a cluster mode using `app-cluster.js` to utilize multiple CPU cores.
- Environment-specific configurations are handled via `.env` files and `config.js`.
