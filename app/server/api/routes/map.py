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
    cog_layer = {
        "valueType": "malha_fundiaria_cog",
        "type": "layertype",
        "origin": {
            "sourceService": "internal",
            "typeOfTMS": "cog",
            "url": "https://s3.lapig.iesa.ufg.br/malha-fundiaria/brasil_malhafundiaria_ambiental_10m_v2_cog.tif",
            "epsg": "ESRI:102033"
        },
        "typeLayer": "raster",
        "viewValueType": "Malha Fundiária Ambiental",
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
            "layerTypeName": "malha_fundiaria_cog",
            "url": "https://s3.lapig.iesa.ufg.br/malha-fundiaria/brasil_malhafundiaria_ambiental_10m_v2_cog.tif"
        },
        "regionFilter": False,
        "visible": True,
        "opacity": 1.0,
        "metadata": [
            {
                "title": "Metadados",
                "description": "Malha Fundiária Ambiental consolidada (COG 10m)."
            }
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
        "legend": [
          { "value": 1, "color": "#0000cd", "label": "Massa d'água" },
          { "value": 2, "color": "#6c747e", "label": "Malha Urbana" },
          { "value": 3, "color": "#833dc9", "label": "TI Homologada" },
          { "value": 4, "color": "#64efef", "label": "UC Proteção Integral" },
          { "value": 5, "color": "#cd73a0", "label": "Área Militar" },
          { "value": 6, "color": "#fdae61", "label": "Imóvel Privado (SIGEF/SNCI)" },
          { "value": 7, "color": "#a8e16e", "label": "Assentamento" },
          { "value": 8, "color": "#17af05", "label": "Glebas Públicas - FPND" },
          { "value": 9, "color": "#efef4d", "label": "UC Uso Sustentável" },
          { "value": 10, "color": "#dc1010", "label": "Glebas Públicas" },
          { "value": 11, "color": "#4587ca", "label": "Quilombola Declarado" },
          { "value": 12, "color": "#3333e6", "label": "TI Não Homologada" },
          { "value": 13, "color": "#44ce44", "label": "Quilombola Não Declarado" },
          { "value": 14, "color": "#cf3ccf", "label": "CAR sem sobreposição" },
          { "value": 15, "color": "#ff636a", "label": "CAR com sobreposição" },
          { "value": 20, "color": "#e6e9b4", "label": "Área de Preservação Permanente" },
          { "value": 21, "color": "#1e570d", "label": "Reserva Legal" },
          { "value": 22, "color": "#dfdfde", "label": "Vazio Fundiário" }
        ]
    }
    
    # layertypes is a dict organized by thematic keys. Let's add ours.
    if isinstance(layertypes, dict):
        layertypes['malha_fundiaria'] = [cog_layer]
    
    result = {
        "groups": descriptor_builder.get_layers(lang, layertypes),
        "basemaps": descriptor_builder.get_basemaps(lang, basemaps_types),
        "limits": descriptor_builder.get_limits(lang, limits_types),
    }
    return result

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
@router.get("/getowsdomain")
async def get_host():
    return [f"{settings.OWS_HOST}/ows"]
