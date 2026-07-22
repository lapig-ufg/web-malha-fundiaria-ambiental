from fastapi import APIRouter, Request, Depends
import httpx
from core.config import settings
from utils.descriptor_builder import DescriptorBuilder
from api.dependencies import get_map_data
import os
import json

router = APIRouter()

descriptor_builder = DescriptorBuilder(settings.app_root)

async def fetch_layer_types(language: str, type_name: str = 'layers'):
    url = f"{settings.OWS_API}/map/{type_name}?lang={language}"
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error fetching layer types: {e}")
            return {}

@router.get("/descriptor")
async def get_descriptor(lang: str = 'pt-br'):
    layertypes = await fetch_layer_types(lang, 'layers')
    basemaps_types = await fetch_layer_types(lang, 'basemaps')
    limits_types = await fetch_layer_types(lang, 'limits')

    # Ensure standard basemaps are present in basemaps_types for mapping
    standard_basemaps = [
        "mapbox", "mapbox-dark", "google", "google-hybrid", 
        "roads", "estradas", "bing", "relevo"
    ]

    if not isinstance(basemaps_types, dict):
        basemaps_types = {}

    if 'basemaps' not in basemaps_types:
        basemaps_types['basemaps'] = []

    existing_basemap_values = {b.get('valueType') for b in basemaps_types['basemaps']}

    for b_value in standard_basemaps:
        if b_value not in existing_basemap_values:
            basemaps_types['basemaps'].append({
                "valueType": b_value,
                "type": "basemap",
                "origin": {"sourceService": "internal", "typeOfTMS": "xyz"},
                "viewValueType": b_value.capitalize(),
                "visible": False,
                "opacity": 1.0
            })

    # Hardcode new COG layer type
    is_en = lang.startswith('en')
    
    view_value_type = "Environmental Land Tenure" if is_en else "Malha Fundiária Ambiental"
    metadata_title = "Metadata" if is_en else "Metadados"
    metadata_description = "Consolidated Environmental Land Tenure (COG 10m)." if is_en else "Malha Fundiária Ambiental consolidada (COG 10m)."
    
    legend_data = [
        (1, "#0000cd", "Massa d'água", "Water body"),
        (2, "#6c747e", "Malha Urbana", "Urban area"),
        (3, "#833dc9", "Território Indígena Homologado", "Homologated Indigenous Territory"),
        (4, "#64efef", "Unidade de Conservação de Proteção Integral", "Strictly Protected Conservation Unit"),
        (5, "#cd73a0", "Área Militar", "Military area"),
        (6, "#fdae61", "Imóvel Privado (SIGEF/SNCI)", "Private Property (SIGEF/SNCI)"),
        (7, "#a8e16e", "Assentamento", "Settlement"),
        (8, "#17af05", "Glebas Públicas - FPND", "Public Lands - FPND"),
        (9, "#efef4d", "Unidade de Conservação de Uso Sustentável", "Sustainable Use Conservation Unit"),
        (10, "#dc1010", "Glebas Públicas", "Public Lands"),
        (11, "#4587ca", "Quilombola Declarado", "Declared Quilombola"),
        (12, "#3333e6", "Território Indígena Não Homologado", "Non-homologated Indigenous Territory"),
        (13, "#44ce44", "Quilombola Não Declarado", "Non-declared Quilombola"),
        (14, "#cf3ccf", "Cadastro Ambiental Rural sem sobreposição", "Rural Environmental Registry without overlap"),
        (15, "#ff636a", "Cadastro Ambiental Rural com sobreposição", "Rural Environmental Registry with overlap"),
        (20, "#e6e9b4", "Área de Preservação Permanente", "Permanent Preservation Area"),
        (21, "#1e570d", "Reserva Legal", "Legal Reserve"),
        (22, "#dfdfde", "Vazio Fundiário", "Land Vacancy")
    ]
    
    cog_legend = [
        { "value": val, "color": color, "label": label_en if is_en else label_pt }
        for val, color, label_pt, label_en in legend_data
    ]

    cog_layer = {
        "valueType": "malha_fundiaria_cog",
        "type": "layertype",
        "origin": {
            "sourceService": "internal",
            "typeOfTMS": "cog",
            "url": "https://s3.lapig.iesa.ufg.br/malha-fundiaria/v3/brasil_malhafundiaria_ambiental_10m_v3_cog.tif",
            "epsg": "ESRI:102033"
        },
        "typeLayer": "raster",
        "viewValueType": view_value_type,
        "typeLabel": "COG",
        "wfsMapCard": {
            "show": False,
            "attributes": []
        },
        "download": {
            "csv": False,
            "shp": False,
            "gpkg": False,
            "raster": True,
            "parquet": True,
            "layerTypeName": "malha_fundiaria_cog",
            "url": "https://s3.lapig.iesa.ufg.br/malha-fundiaria/brasil_malhafundiaria_ambiental_10m_v2_cog.tif",
            "urls": {
                "raster": "https://s3.lapig.iesa.ufg.br/malha-fundiaria/brasil_malhafundiaria_ambiental_10m_v3b_.tif",
                "parquet": "https://s3.lapig.iesa.ufg.br/malha-fundiaria/brasil_malhafundiaria_ambiental_10m_v3b_{region}.parquet"
            }
        },
        "regionFilter": False,
        "visible": True,
        "opacity": 1.0,
        "metadata": [
            {
                "title": metadata_title,
                "description": metadata_description
            },
            {"title": "Descrição", "description": "Malha Fundiária Ambiental"},
            {"title": "Formato", "description": "Geotiff (tiff) e GeoParquet (.parquet)."},
            {"title": "Região", "description": "Todo o território nacional do Brasil.O download no formato Geoparquet é disponibilizado por estado"},
            {"title": "Período", "description": "Abril/2024"},
            {"title": "Sistemas de Referência e Coordenadas", "description": "Superfície de referência SAD69, Sistema de Coordenada Plana (metros)."},
            {"title": "Projeção cartográfica", "description": "Albers Equal Area Conic."},
            {"title": "Codificação de caractere", "description": "Latin 1"},
            {"title": "Fonte", "description": ""},
            {"title": "URL", "description": "<a class='link-details' target='_blank' href='https://malhafundiaria.lapig.iesa.ufg.br'>https://malhafundiaria.lapig.iesa.ufg.br</a>"}
        ],
        "cogStyle": {
          "color": [
            "case",
            [
              "==",
              [
                "band",
                1
              ],
              0
            ],
            [
              0,
              0,
              0,
              0
            ],
            [
              "palette",
              [
                "band",
                1
              ],
              [
                [0, 0, 0, 0],
                [0, 0, 205],
                [108, 116, 126],
                [131, 61, 201],
                [100, 239, 239],
                [205, 115, 160],
                [253, 174, 97],
                [168, 225, 110],
                [23, 175, 5],
                [239, 239, 77],
                [220, 16, 16],
                [69, 135, 202],
                [51, 51, 230],
                [68, 206, 68],
                [207, 60, 207],
                [255, 99, 106],
                [0, 0, 0, 0],
                [0, 0, 0, 0],
                [0, 0, 0, 0],
                [0, 0, 0, 0],
                [230, 233, 180],
                [30, 87, 13],
                [223, 223, 222]
              ]
            ]
          ]
        },
        "legend": cog_legend
    }

    # Hardcode a new "Excedente Florestal por Município" choropleth layer.
    # Unlike the OWS-backed layers above, this one is rendered client-side
    # as a GeoJSON vector layer (see LayerService.createLayer's 'geojson'
    # case) fed by our own /service/map/forest-surplus-municipios endpoint
    # — there is no MapServer/OWS tile source for it.
    forest_surplus_title = "Excess Vegetation by Municipality" if is_en else "Excedente Florestal por Município"
    forest_surplus_type_label = "Excess Vegetation Percentage" if is_en else "Porcentagem de Excedente Florestal"
    forest_surplus_description = (
        "Natural vegetation area exceeding the legally-protected (APP + Legal Reserve) area, "
        "as a % of each municipality's total area (most recent year)."
        if is_en else
        "Área de vegetação natural que excede a área legalmente protegida (APP + Reserva Legal), "
        "como % da área total de cada município (ano mais recente)."
    )

    forest_surplus_bins = [
        (-1e9, 0, "#b71c1c", "< 0% (déficit)" if not is_en else "< 0% (deficit)"),
        (0, 10, "#fdae61", "0 – 10%"),
        (10, 25, "#ffffbf", "10 – 25%"),
        (25, 40, "#a6d96a", "25 – 40%"),
        (40, 60, "#1a9850", "40 – 60%"),
        (60, 1e9, "#006837", "> 60%"),
    ]
    forest_surplus_legend = [
        {"min": lo, "max": hi, "color": color, "label": label}
        for lo, hi, color, label in forest_surplus_bins
    ]

    forest_surplus_layer = {
        "valueType": "excedente_florestal_municipios",
        "type": "layertype",
        "origin": {
            "sourceService": "internal",
            "typeOfTMS": "geojson",
            "url": "/service/map/forest-surplus-municipios",
        },
        "choroplethField": "excedente_pct",
        "typeLayer": "vector",
        "viewValueType": forest_surplus_title,
        "typeLabel": forest_surplus_type_label,
        "wfsMapCard": {
            "show": False,
            "attributes": []
        },
        "download": {
            "csv": False,
            "shp": False,
            "gpkg": False,
            "raster": False,
            "parquet": False,
            "layerTypeName": "excedente_florestal_municipios",
        },
        "regionFilter": False,
        "visible": False,
        "opacity": 0.8,
        "metadata": [
            {
                "title": metadata_title,
                "description": forest_surplus_description,
            },
            {"title": "Descrição", "description": "Excedente Florestal por Município"},
            {"title": "Região", "description": "Todo o território nacional do Brasil"},
            {"title": "Período", "description": "Abril/2024"},
            {"title": "Base do Cálculo", "description": "Área total de vegetação natural das propriedades por município, subtraídas as áreas de vegetação natural das APPs e Reservas Legais."},
            {"title": "Fonte", "description": ""},
            {"title": "URL", "description": "<a class='link-details' target='_blank' href='https://malhafundiaria.lapig.iesa.ufg.br'>https://malhafundiaria.lapig.iesa.ufg.br</a>"}
        ],
        "legend": forest_surplus_legend,
    }

    # Déficit de APP / Reserva Legal por Município: two more município
    # choropleths, same GeoJSON-vector mechanism as forest_surplus_layer
    # above. Color scale is inverted vs. Excedente Florestal — here HIGH
    # values are bad (more non-natural area inside a legally-protected
    # zone), so red = high deficit, green = low deficit.
    deficit_bins = [
        (0, 10, "#1a9850", "0 – 10%"),
        (10, 25, "#a6d96a", "10 – 25%"),
        (25, 40, "#ffffbf", "25 – 40%"),
        (40, 60, "#fdae61", "40 – 60%"),
        (60, 1e9, "#d73027", "> 60%"),
    ]
    deficit_legend = [
        {"min": lo, "max": hi, "color": color, "label": label}
        for lo, hi, color, label in deficit_bins
    ]
    deficit_type_label = "Deficit Percentage" if is_en else "Porcentagem de Déficit"

    def _build_deficit_layer(value_type: str, url: str, title_pt: str, title_en: str, description_pt: str, description_en: str, extra_metadata: list = None) -> dict:
        return {
            "valueType": value_type,
            "type": "layertype",
            "origin": {
                "sourceService": "internal",
                "typeOfTMS": "geojson",
                "url": url,
            },
            "choroplethField": "deficit_pct",
            "typeLayer": "vector",
            "viewValueType": title_en if is_en else title_pt,
            "typeLabel": deficit_type_label,
            "wfsMapCard": {
                "show": False,
                "attributes": []
            },
            "download": {
                "csv": False,
                "shp": False,
                "gpkg": False,
                "raster": False,
                "parquet": False,
                "layerTypeName": value_type,
            },
            "regionFilter": False,
            "visible": False,
            "opacity": 0.8,
            "metadata": [
                {
                    "title": metadata_title,
                    "description": description_en if is_en else description_pt,
                },
                *(extra_metadata or []),
            ],
            "legend": deficit_legend,
        }

    deficit_app_layer = _build_deficit_layer(
        "deficit_app_municipios",
        "/service/map/deficit-app-municipios",
        "Déficit de APP por Município",
        "APP Deficit by Municipality",
        "Área dentro da Área de Preservação Permanente (APP) que não é vegetação natural, como % da área total de APP de cada município (ano mais recente).",
        "Area within the Permanent Preservation Area (APP) that is not natural vegetation, as a % of each municipality's total APP area (most recent year).",
        extra_metadata=[
            {"title": "Descrição", "description": "Déficit de APP"},
            {"title": "Região", "description": "Todo o território nacional do Brasil"},
            {"title": "Período", "description": "Abril/2024"},
            {"title": "Base do Cálculo", "description": "Diferença entre a área de vegetação natural e as áreas de não vegetação natural na APP"},
            {"title": "Fonte", "description": ""},
            {"title": "URL", "description": "<a class='link-details' target='_blank' href='https://malhafundiaria.lapig.iesa.ufg.br'>https://malhafundiaria.lapig.iesa.ufg.br</a>"},
        ],
    )

    deficit_rl_layer = _build_deficit_layer(
        "deficit_rl_municipios",
        "/service/map/deficit-rl-municipios",
        "Déficit de Reserva Legal por Município",
        "Legal Reserve Deficit by Municipality",
        "Área dentro da Reserva Legal que não é vegetação natural, como % da área total de Reserva Legal de cada município (ano mais recente).",
        "Area within the Legal Reserve that is not natural vegetation, as a % of each municipality's total Legal Reserve area (most recent year).",
        extra_metadata=[
            {"title": "Descrição", "description": "Déficit de Reserva Legal"},
            {"title": "Região", "description": "Todo o território nacional do Brasil"},
            {"title": "Período", "description": "Abril/2024"},
            {"title": "Base do Cálculo", "description": "Diferença entre a área de vegetação natural e as áreas de não vegetação natural na Reserva Legal"},
            {"title": "Fonte", "description": ""},
            {"title": "URL", "description": "<a class='link-details' target='_blank' href='https://malhafundiaria.lapig.iesa.ufg.br'>https://malhafundiaria.lapig.iesa.ufg.br</a>"},
        ],
    )

    # layertypes is a dict organized by thematic keys. Let's add ours.
    if isinstance(layertypes, dict):
        layertypes['malha_fundiaria'] = [cog_layer, forest_surplus_layer, deficit_app_layer, deficit_rl_layer]

    result = {
        "groups": descriptor_builder.get_layers(lang, layertypes),
        "basemaps": descriptor_builder.get_basemaps(lang, basemaps_types),
        "limits": descriptor_builder.get_limits(lang, limits_types),
    }
    return result

def _municipio_rows_to_geojson(rows: list, extra_props: list) -> dict:
    """
    Build a GeoJSON FeatureCollection from município rows shaped like
    {cd_mun, municipio, geojson, ...extra_props} — shared by the
    município-level choropleth endpoints below.
    """
    features = []
    for row in rows:
        raw_geojson = row.get('geojson')
        if not raw_geojson:
            continue
        try:
            geometry = json.loads(raw_geojson)
        except (TypeError, ValueError):
            continue
        properties = {"cd_mun": row.get('cd_mun'), "municipio": row.get('municipio')}
        for key in extra_props:
            properties[key] = row.get(key)
        features.append({"type": "Feature", "geometry": geometry, "properties": properties})
    return {"type": "FeatureCollection", "features": features}

@router.get("/forest-surplus-municipios")
async def get_forest_surplus_municipios(query_result: dict = Depends(get_map_data)):
    """
    Excedente Florestal por município (nacional, ano mais recente), como
    GeoJSON — consumida pela camada de mapa coroplética
    (excedente_florestal_municipios), não pelo gráfico de estatísticas.
    """
    rows = query_result.get('forest_surplus_municipios', [])
    return _municipio_rows_to_geojson(rows, ['excedente_ha', 'excedente_pct'])

@router.get("/deficit-app-municipios")
async def get_deficit_app_municipios(query_result: dict = Depends(get_map_data)):
    """Déficit de APP por município (% da área de APP que não é vegetação natural), como GeoJSON."""
    rows = query_result.get('deficit_app_municipios', [])
    return _municipio_rows_to_geojson(rows, ['deficit_ha', 'deficit_pct'])

@router.get("/deficit-rl-municipios")
async def get_deficit_rl_municipios(query_result: dict = Depends(get_map_data)):
    """Déficit de Reserva Legal por município (% da área de RL que não é vegetação natural), como GeoJSON."""
    rows = query_result.get('deficit_rl_municipios', [])
    return _municipio_rows_to_geojson(rows, ['deficit_ha', 'deficit_pct'])

@router.get("/extent")
async def get_extent(query_result: dict = Depends(get_map_data)):
    # matching JS controller: { type: 'Feature', geometry: JSON.parse(queryResult[0].geojson) }
    extent_data = query_result.get('extent')
    if extent_data and len(extent_data) > 0:
        return {
            "type": "Feature",
            "geometry": json.loads(extent_data[0]['geojson'])
        }
    return {}

@router.get("/search")
async def get_search(query_result: dict = Depends(get_map_data)):
    search_data = query_result.get('search', [])
    ini_results = []
    for row in search_data:
        row.pop('priority', None)
        ini_results.append(row)

    # Deduplicate based on 'value'
    seen = set()
    result = []
    for item in ini_results:
        if item['value'] not in seen:
            seen.add(item['value'])
            result.append(item)

    return {"search": result}

@router.get("/malha")
async def get_malha(query_result: dict = Depends(get_map_data)):
    search_data = query_result.get('search', [])
    ini_results = []
    for row in search_data:
        row.pop('priority', None)
        ini_results.append(row)

    # Deduplicate based on 'value'
    seen = set()
    result = []
    for item in ini_results:
        if item['value'] not in seen:
            seen.add(item['value'])
            result.append(item)

    return {"search": result}

@router.get("/estado")
async def get_estado(query_result: dict = Depends(get_map_data)):
    return {"search": query_result.get('search', [])}

@router.get("/municipio")
async def get_municipio(query_result: dict = Depends(get_map_data)):
    return {"search": query_result.get('search', [])}

@router.get("/bioma")
async def get_bioma(query_result: dict = Depends(get_map_data)):
    return {"search": query_result.get('search', [])}

@router.get("/getowsdomain")
async def get_host():
    return [f"{settings.OWS_HOST}/ows"]
