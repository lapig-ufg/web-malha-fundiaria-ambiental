from fastapi import APIRouter, Request, Depends
from api.dependencies import get_chart_data
from utils.language import language as lang_util

router = APIRouter()

def number_format(numero):
    if numero is None:
        return "0,00"
    return "{:,.2f}".format(numero).replace(",", "X").replace(".", ",").replace("X", ".")

def replacement_strings(template, replacements):
    import re
    if not template:
        return ""
    # Matching JS: .replace(/#([^#]+)#/g, ...)
    return re.sub(r'#([^#]+)#', lambda m: str(replacements.get(m.group(1), "")), template)

def build_graph_result(all_queries_result, chart_description):
    try:
        array_data = []
        
        # Collect all unique labels first to ensure consistent X-axis
        all_labels = set()
        for query in chart_description['idsOfQueriesExecuted']:
            query_ind = all_queries_result.get(query['idOfQuery'], [])
            for item in query_ind:
                label = item.get('label')
                if label is not None:
                    all_labels.add(int(label) if isinstance(label, (int, float)) else str(label))
        
        sorted_labels = sorted(list(all_labels))
        
        for query in chart_description['idsOfQueriesExecuted']:
            query_ind = all_queries_result.get(query['idOfQuery'], [])
            
            if chart_description['type'] == 'line':
                if isinstance(query['labelOfQuery'], str):
                    # Align data with sorted_labels
                    data_map = { (int(i['label']) if isinstance(i['label'], (int, float)) else str(i['label'])): float(i['value']) for i in query_ind if i.get('label') is not None }
                    data_points = [data_map.get(label, 0) for label in sorted_labels]
                    
                    color = query_ind[0].get('color', '#000') if query_ind else '#000'
                    
                    array_data.append({
                        "label": query['labelOfQuery'],
                        "data": data_points,
                        "fill": False,
                        "borderColor": color,
                        "tension": 0.4
                    })
                else:
                    # Handle dict labelOfQuery (classes)
                    labels_map = {
                        'class_1': 'Ausente',
                        'class_2': 'Intermediário',
                        'class_3': 'Severa'
                    }
                    for key_label_query, value_label_query in query['labelOfQuery'].items():
                        key_label = labels_map.get(key_label_query)
                        filtered = [a for a in query_ind if a.get('classe') == key_label]
                        
                        data_map = { (int(i['label']) if isinstance(i['label'], (int, float)) else str(i['label'])): float(i['value']) for i in filtered if i.get('label') is not None }
                        data_points = [data_map.get(label, 0) for label in sorted_labels]
                        
                        color = filtered[0].get('color', '#000') if filtered else '#000'
                        
                        array_data.append({
                            "label": value_label_query,
                            "data": data_points,
                            "fill": False,
                            "borderColor": color,
                            "tension": 0.4
                        })
            elif chart_description['type'] in ('pie', 'doughnut'):
                label = query['labelOfQuery'] if isinstance(query['labelOfQuery'], str) else query['idOfQuery']
                
                # For pie charts, labels come from the query items themselves
                pie_labels = []
                pie_data = []
                pie_colors = []
                
                for item in query_ind:
                    pie_labels.append(item.get('label'))
                    pie_data.append(float(item.get('value', 0)))
                    pie_colors.append(item.get('color', '#000'))
                
                # If this is the only query, we can return early or set up for multiple (unlikely for pie)
                if len(chart_description['idsOfQueriesExecuted']) == 1:
                    return {
                        "labels": pie_labels,
                        "datasets": [{
                            "label": label,
                            "data": pie_data,
                            "backgroundColor": pie_colors,
                            "hoverBackgroundColor": pie_colors
                        }]
                    }
            elif chart_description['type'] in ('bar', 'horizontalBar'):
                if isinstance(query['labelOfQuery'], str):
                    data_map = { (int(i['label']) if isinstance(i['label'], (int, float)) else str(i['label'])): float(i['value']) for i in query_ind if i.get('label') is not None }
                    data_points = [data_map.get(label, 0) for label in sorted_labels]
                    color = query_ind[0].get('color', '#000') if query_ind else '#000'

                    array_data.append({
                        "label": query['labelOfQuery'],
                        "data": data_points,
                        "backgroundColor": color,
                    })
                else:
                    for key_label_query, value_label_query in query['labelOfQuery'].items():
                        filtered = [a for a in query_ind if a.get('classe') == key_label_query]
                        data_map = { (int(i['label']) if isinstance(i['label'], (int, float)) else str(i['label'])): float(i['value']) for i in filtered if i.get('label') is not None }
                        data_points = [data_map.get(label, 0) for label in sorted_labels]
                        color = filtered[0].get('color', '#000') if filtered else '#000'

                        array_data.append({
                            "label": value_label_query,
                            "data": data_points,
                            "backgroundColor": color,
                        })
                        
        return {
            "labels": sorted_labels,
            "datasets": array_data
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Build Graph Error: {e}")
        return None

def build_table_data(all_queries_result, chart_description):
    try:
        data_info = []
        for query in chart_description['idsOfQueriesExecuted']:
            query_ind = all_queries_result.get(query['idOfQuery'], [])
            for i, item in enumerate(query_ind):
                val = float(item['value'])
                item['originalValue'] = val
                item['index'] = f"{i + 1}º"
                item['value'] = f"{number_format(val)} ha"
            data_info = query_ind # Matching JS: dataInfo = [...queryInd]
        return data_info
    except Exception as e:
        print(f"Build Table Error: {e}")
        return None

@router.get("/resumo")
async def handle_resumo(lang: str = 'pt', card_resume: str = '', query_result: dict = Depends(get_chart_data)):
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

@router.get("/pastureGraph")
async def handle_pasture_graph(lang: str = 'pt', typeRegion: str = '', textRegion: str = '', query_result: dict = Depends(get_chart_data)):
    lang_data = lang_util.get_lang(lang)
    language_ob = lang_data.get('right_sidebar', {}) if lang_data else {}
    
    replacements = {
        "typeRegionTranslate": language_ob.get('region_types', {}).get(typeRegion, typeRegion),
        "textRegionTranslate": textRegion,
    }
    
    pasture_card = language_ob.get("pastureGraph_card", {})
    p_and_l = pasture_card.get("pastureAndLotacaoBovina", {})
    p_qual = pasture_card.get("pastureQuality", {})
    p_carb = pasture_card.get("carbon", {})

    chart_result = [
        {
            "id": "pasture",
            "idsOfQueriesExecuted": [
                { "idOfQuery": 'pasture', "labelOfQuery": p_and_l.get('labelOfQuery', {}).get('pasture', 'pasture') },
                { "idOfQuery": 'lotacao_bovina_regions', "labelOfQuery": p_and_l.get('labelOfQuery', {}).get('lotacao_bovina_regions', 'lotacao_bovina_regions') },
            ],
            "title": p_and_l.get('title', 'Pasture'),
            "getText": lambda chart: replacement_strings(p_and_l.get('text', ''), replacements),
            "type": 'line',
            "options": { "legend": { "display": False } }
        },
        {
            "id": "pasture_quality",
            "idsOfQueriesExecuted": [
                { "idOfQuery": 'pasture_quality', "labelOfQuery": p_qual.get('labelOfQuery', {}).get('pasture_quality', 'pasture_quality') },
            ],
            "title": p_qual.get('title', 'Quality'),
            "getText": lambda res, q: replacement_strings(p_qual.get('text', ''), replacements),
            "type": 'line',
            "options": { "legend": { "display": False } }
        },
        {
            "id": "carbono",
            "idsOfQueriesExecuted": [
                { "idOfQuery": 'pasture_carbon', "labelOfQuery": p_carb.get('labelOfQuery', {}).get('carbon', 'carbon') },
            ],
            "title": p_carb.get('title', 'Carbon'),
            "getText": lambda chart: replacement_strings(p_carb.get('text', ''), replacements),
            "type": 'line',
            "options": { "legend": { "display": False } }
        },
    ]
    
    chart_final = []
    for chart in chart_result:
        chart['data'] = build_graph_result(query_result, chart)
        if chart['data']:
            chart['show'] = True
            if chart['id'] == 'pasture_quality':
                chart['text'] = chart['getText'](query_result, chart['idsOfQueriesExecuted'])
            else:
                chart['text'] = chart['getText'](chart)
        else:
            chart['data'] = {}
            chart['show'] = False
            chart['text'] = "erro."
        
        # Remove lambda before sending
        chart.pop('getText', None)
        chart_final.append(chart)
        
    return chart_final

@router.get("/area2")
async def handle_area2_data(lang: str = 'pt', typeRegion: str = '', textRegion: str = '', year: int = 2021, query_result: dict = Depends(get_chart_data)):
    lang_data = lang_util.get_lang(lang)
    language_ob = lang_data.get('right_sidebar', {}) if lang_data else {}
    
    replacements = {
        "typeRegionTranslate": language_ob.get('region_types', {}).get(typeRegion, typeRegion),
        "textRegionTranslate": textRegion,
    }
    
    area2_card = language_ob.get("area2_card", {}).get("pastureQualityPerYear", {})

    chart_result = [
        {
            "id": "pastureQualityPerYear",
            "idsOfQueriesExecuted": [
                { "idOfQuery": 'pasture_quality', "labelOfQuery": area2_card.get('labelOfQuery', {}).get('pasture_quality', 'pasture_quality') },
            ],
            "title": area2_card.get('title', 'Quality per Year'),
            "getText": lambda res, q: self_get_text(res, q, area2_card, replacements, year),
            "type": 'pie',
            "options": { "plugins": { "legend": { "labels": { "color": '#495057' } } } }
        }
    ]
    
    def self_get_text(queries_result, query, card, reps, yr):
        q_id = query[0]['idOfQuery']
        area_pasture = sum(float(x['value']) for x in queries_result.get(q_id, []))
        reps['areaPasture'] = number_format(area_pasture)
        reps['yearTranslate'] = yr
        return replacement_strings(card.get('text', ''), reps)

    chart_final = []
    for chart in chart_result:
        chart['data'] = build_graph_result(query_result, chart)
        if chart['data']:
            chart['show'] = True
            chart['text'] = self_get_text(query_result, chart['idsOfQueriesExecuted'], area2_card, replacements, year)
        else:
            chart['data'] = {}
            chart['show'] = False
            chart['text'] = "erro."
        
        chart.pop('getText', None)
        chart_final.append(chart)
        
    return chart_final

@router.get("/area3")
async def handle_area3_data(lang: str = 'pt', typeRegion: str = '', textRegion: str = '', query_result: dict = Depends(get_chart_data)):
    lang_data = lang_util.get_lang(lang)
    language_ob = lang_data.get('right_sidebar', {}) if lang_data else {}
    
    replacements = {
        "typeRegionTranslate": language_ob.get('region_types', {}).get(typeRegion, typeRegion),
        "textRegionTranslate": textRegion,
    }
    
    area3_card = language_ob.get("area3_card", {}).get("pastureRankingStates", {})

    chart_result = [
        {
            "id": "pastureRankings",
            "idsOfQueriesExecuted": [
                { "idOfQuery": 'estados', "labelOfQuery": area3_card.get('labelOfQuery', {}).get('estados', 'estados') },
            ],
            "title": area3_card.get('title', 'Rankings'),
            "getText": lambda chart: replacement_strings(area3_card.get('text', ''), replacements),
            "type": 'bar',
            "options": { "indexAxis": 'y', "plugins": { "legend": { "labels": { "color": '#495057' } } }, "scales": { "x": { "ticks": { "color": '#495057' }, "grid": { "color": '#ebedef' } }, "y": { "ticks": { "color": '#495057' }, "grid": { "color": '#ebedef' } } } }
        }
    ]
    
    chart_final = []
    for chart in chart_result:
        chart['data'] = build_graph_result(query_result, chart)
        if chart['data']:
            chart['show'] = True
            chart['text'] = replacement_strings(area3_card.get('text', ''), replacements)
        else:
            chart['data'] = {}
            chart['show'] = False
            chart['text'] = "erro."
        
        chart.pop('getText', None)
        chart_final.append(chart)
        
    return chart_final

@router.get("/areatable")
async def handle_table_rankings(lang: str = 'pt', typeRegion: str = '', valueRegion: str = '', textRegion: str = '', query_result: dict = Depends(get_chart_data)):
    lang_data = lang_util.get_lang(lang)
    language_ob = lang_data.get('right_sidebar', {}) if lang_data else {}
    
    replacements = {
        "typeRegionTranslate": language_ob.get('region_types', {}).get(typeRegion, typeRegion),
        "textRegionTranslate": textRegion,
    }
    
    area_table_card = language_ob.get("area_table_card", {})
    
    def get_fallback(card_id, default_title, default_cols):
        card = area_table_card.get(card_id, {})
        return {
            "title": card.get("title", default_title),
            "columnsTitle": card.get("columnsTitle", default_cols),
            "labelOfQuery": card.get("labelOfQuery", {}),
            "text": card.get("text", "")
        }

    c_city = get_fallback("pastureRankingsCities", "Cities", "#?City?UF?Value")
    c_state = get_fallback("pastureRankingsStates", "States", "#?State?Value")
    c_biome = get_fallback("pastureRankingsBiomes", "Biomes", "#?Biome?Value")

    tables_descriptor = [
        {
            "id": "pastureRankingsCities",
            "idsOfQueriesExecuted": [ { "idOfQuery": 'municipios', "labelOfQuery": c_city['labelOfQuery'].get('municipios', 'municipios') } ],
            "title": c_city['title'],
            "columnsTitle": c_city['columnsTitle'],
            "getText": lambda chart: replacement_strings(c_city['text'], replacements),
            "rows_labels": "index?city?uf?value",
        },
        {
            "id": "pastureRankingsStates",
            "idsOfQueriesExecuted": [ { "idOfQuery": 'estados', "labelOfQuery": c_state['labelOfQuery'].get('estados', 'estados') } ],
            "title": c_state['title'],
            "columnsTitle": c_state['columnsTitle'],
            "getText": lambda chart: replacement_strings(c_state['text'], replacements),
            "rows_labels": "index?uf?value",
        },
        {
            "id": "pastureRankingsBiomes",
            "idsOfQueriesExecuted": [ { "idOfQuery": 'biomas', "labelOfQuery": c_biome['labelOfQuery'].get('biomas', 'biomas') } ],
            "title": c_biome['title'],
            "columnsTitle": c_biome['columnsTitle'],
            "getText": lambda chart: replacement_strings(c_biome['text'], replacements),
            "rows_labels": "index?biome?value",
        }
    ]
    
    result_final = []
    for res in tables_descriptor:
        res['data'] = build_table_data(query_result, res)
        if res['data']:
            res['show'] = True
            res['text'] = replacement_strings(area_table_card.get(res['id'], {}).get('text', ''), replacements)
        else:
            res['data'] = {}
            res['show'] = False
            res['text'] = "erro."
            
        res.pop('getText', None)
        result_final.append(res)
        
    return result_final
