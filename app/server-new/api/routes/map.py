from fastapi import APIRouter, Request, Depends
import httpx
from core.config import settings
from utils.descriptor_builder import DescriptorBuilder
from api.dependencies import data_injector
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
            "layerTypeName": "malha_fundiaria_cog"
        },
        "regionFilter": False,
        "visible": True,
        "opacity": 1.0,
        "metadata": [
            {
                "title": "Metadados",
                "description": "Malha Fundiária Ambiental consolidada (COG 10m)."
            }
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

@router.get("/extent", dependencies=[Depends(data_injector)])
async def get_extent(request: Request):
    query_result = request.state.query_result
    # matching JS controller: { type: 'Feature', geometry: JSON.parse(queryResult[0].geojson) }
    if query_result and len(query_result) > 0:
        return {
            "type": "Feature",
            "geometry": json.loads(query_result[0]['geojson'])
        }
    return {}

@router.get("/search", dependencies=[Depends(data_injector)])
async def get_search(request: Request):
    query_result = request.state.query_result
    ini_results = []
    for row in query_result:
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
