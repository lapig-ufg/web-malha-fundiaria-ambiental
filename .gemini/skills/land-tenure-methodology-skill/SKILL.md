---
name: land-tenure-methodology-skill
description: Access and navigate the project's external documentation (GitHub Pages) to extract project descriptions and methodological details. Use when building hotsite methodology pages, describing the project scope, or finding specific land tenure analysis procedures.
---

# Land Tenure Methodology Skill

This skill provides a workflow for gathering technical and descriptive information from the Malha Fundiária Ambiental project's external documentation.

## Primary Resource
The project's definitive methodology and technical descriptions are hosted at:
**https://boliveirageo.github.io/malhafundiariaambiental/**

## Workflow

### 1. Initial Access
Use `web_fetch` to retrieve the main page.
```bash
# Example call
web_fetch(prompt="Analyze https://boliveirageo.github.io/malhafundiariaambiental/ and extract the main project description and the link to the methodology section.")
```

### 2. Navigate via Hyperlinks
If the required information (e.g., specific data sources, classification criteria) is not on the main page, identify relevant links in the HTML and follow them with subsequent `web_fetch` calls.

### 3. Information Extraction
Focus on extracting details for:
- **Project Description**: High-level purpose and integrated geospatial infrastructure details.
- **Methodology**: Specific procedures for land structure organization, data sources (e.g., INCRA, SFB), and environmental indicator connection.
- **Technical Specs**: Datasets used, projections (SIRGAS 2000), and processing tools.

## Use Cases

### Build Hotsite Methodology
When tasked with updating `app/client/src/app/hotsite/pages/methods/`, use this skill to ensure the content reflects the latest documented procedures.

### Describe the Project
When generating project summaries or updating README/GEMINI files, use this skill to synchronize local descriptions with the external source of truth.

## Notes
- If `web_fetch` fails due to site structure, use `google_web_search` with the site URL as a constraint to find indexed pages.
- Always prefer the external documentation over outdated local READMEs if there is a conflict.
