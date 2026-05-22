# Client Architecture (Malha Fundiária Ambiental)

The frontend is a single-page application (SPA) built with Angular 20. It is designed to be a high-performance map platform for visualizing and analyzing pasture data.

## Module Structure

The application is organized into several key modules:

- `AppModule`: The root module that bootstraps the application.
- `@core`: Contains shared services, components, models, and interceptors used throughout the app.
- `MapPlatformModule`: The main module for the map interface, containing sidebars, tools, and the map component itself.
- `HotsiteModule`: Contains pages for the landing site, about page, help, etc.
- `AnalysisModule`: Contains components for geospatial analysis features.

## Key Services (@core/services)

- `MapService`: A singleton service that maintains the OpenLayers `Map` instance. It provides a centralized API for adding/removing layers, managing interactions, and updating map state.
- `DescriptorService`: Responsible for fetching the layer descriptor from the backend and parsing it into a usable format for the UI.
- `LayerService`: Manages the state and visibility of map layers, coordinating between the `DescriptorService` and the `MapService`.
- `MapApiService`: Handles communication with the backend API for map-specific data (e.g., searching regions, fetching extent).
- `RegionFilterService`: Manages the selection and filtering of geographical regions (States, Biomes, Municipalities).

## Map Platform Components

- `MainComponent`: The layout wrapper for the map platform.
- `GeneralMapComponent`: The core component that hosts the OpenLayers map target.
- `LayersSidebarComponent`: Allows users to toggle layer visibility and change layer types.
- `AreaSidebarComponent`: Provides tools for selecting and filtering areas of interest.
- `StatisticsSidebarComponent`: Displays charts and data summaries for the selected area.
- `OptionsSidebarComponent`: Contains general map settings (e.g., scale).

## State Management

The application primarily uses Angular services with `RxJS` Observables to manage state. For example, `LayerService` might use a `BehaviorSubject` to track the current list of active layers.

## Styling

- Uses **SCSS** for styling.
- **PrimeNG** and **Angular Material** are used for UI components.
- **PrimeFlex** is used for layout and utility classes.
