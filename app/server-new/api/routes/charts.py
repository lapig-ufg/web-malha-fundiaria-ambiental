from fastapi import APIRouter, Request, Depends
from api.dependencies import data_injector
from utils.language import language as lang_util

router = APIRouter()

def number_format(numero):
    if numero is None:
        return "0,00"
    return "{:,.2f}".format(numero).replace(",", "X").replace(".", ",").replace("X", ".")

@router.get("/resumo", dependencies=[Depends(data_injector)])
async def handle_resumo(request: Request, lang: str = 'pt-br', card_resume: str = ''):
    query_result = request.state.query_result
    
    # language_ob = lang_util.get_lang(lang).get('right_sidebar', {})
    
    if card_resume == 'region':
        area = query_result['region'][0]['area_region'] if query_result.get('region') else 0
        return {"area": area}
    elif card_resume == 'pasture':
        area_pasture = query_result['pasture'][0]['value'] if query_result.get('pasture') else 0
        area_region = query_result['region'][0]['area_region'] if query_result.get('region') else 1
        percent = number_format((area_pasture / area_region) * 100) + "%"
        return {"area": area_pasture, "percentOfRegionArea": percent}
    elif card_resume == 'carbono':
        return query_result.get('pasture_carbon_somsc', [{}])[0]
    elif card_resume == 'pasture_quality':
        area_pasture = query_result['pasture'][0]['value'] if query_result.get('pasture') else 1
        area_region = query_result['region'][0]['area_region'] if query_result.get('region') else 1
        
        result = []
        for ob in query_result.get('pasture_quality', []):
            ob['percentAreaPasture'] = number_format((ob['value'] / area_pasture) * 100) + "%"
            ob['percentOfRegionArea'] = number_format((ob['value'] / area_region) * 100) + "%"
            result.append(ob)
        return result
    else:
        return {"data": "Invalid argument"}

@router.get("/pastureGraph", dependencies=[Depends(data_injector)])
async def handle_pasture_graph(request: Request, lang: str = 'pt-br'):
    # This involves complex graph building logic from charts.js
    # For now return the raw query results or a simplified version
    return request.state.query_result
