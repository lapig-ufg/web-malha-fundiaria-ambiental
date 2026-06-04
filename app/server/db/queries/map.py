def get_queries(params: dict = None):
    if params is None:
        params = {}
    
    key = params.get('key', '')
    type_param = params.get('type', 'bioma')

    queries = {
        'extent': lambda p: [
            {
                'source': 'general',
                'id': 'extent',
                'sql': f"SELECT geom_json as geojson FROM regions_geom WHERE type=${{type}} AND unaccent(value) ilike unaccent(${{key}}) LIMIT 1",
                'mantain': True
            }
        ],
        'search': lambda p: [
            {
                'source': 'general',
                'id': 'search',
                'sql': (
                    "With priority_search AS ("
                    " SELECT distinct concat_ws(' - ', text , uf) as text, value, type, 1 AS priority FROM regions_geom "
                    "WHERE unaccent(text) ILIKE unaccent(${key})  AND type NOT in ('country') "
                    "UNION ALL "
                    "SELECT distinct concat_ws(' - ', text , uf) as text, value, type, 2 AS priority FROM regions_geom "
                    "WHERE unaccent(text) ILIKE unaccent(${key}%) AND type NOT in ('country') ) "
                    "select * from priority_search order by priority asc limit 10"
                ),
                'mantain': True
            }
        ],
        'searchregion': lambda p: [
            {
                'source': 'general',
                'id': 'search',
                'sql': "SELECT text, value, type FROM regions_geom WHERE unaccent(value) ILIKE unaccent(${key}) AND type = (${type}) LIMIT 10",
                'mantain': True
            }
        ],
        'cdgeocmu': lambda p: [
            {
                'source': 'general',
                'id': 'search',
                'sql': "SELECT text, value, type, cd_geocmu FROM regions WHERE cd_geocmu=${key} LIMIT 10",
                'mantain': True
            }
        ],
        'cars': lambda p: [
            {
                'source': 'lapig',
                'id': 'search',
                'sql': "SELECT cod_car as text, area_ha, ST_AsGeoJSON(geom) as geojson FROM geo_car_imovel WHERE unaccent(cod_car) ILIKE unaccent(${key}%) order by area_ha DESC LIMIT 10",
                'mantain': True
            }
        ],
        'malha': lambda p: [
            {
                'source': 'lapig',
                'id': 'search',
                'sql': "SELECT landternure_code as text, landternure_code as value, 'malha_fundiaria' as type, ST_AsGeoJSON(geom) as geojson FROM malha_fundiaria_ambiental WHERE unaccent(landternure_code) ILIKE unaccent(${key}) || '%' LIMIT 5",
                'mantain': True
            }
        ],
        'estado': lambda p: [
            {
                'source': 'lapig',
                'id': 'search',
                'sql': "SELECT estado as text, uf as value, 'estado' as type, ST_AsGeoJSON(geom) as geojson FROM estados WHERE unaccent(estado) ILIKE unaccent(${key}) || '%' LIMIT 5",
                'mantain': True
            }
        ],
        'municipio': lambda p: [
            {
                'source': 'lapig',
                'id': 'search',
                'sql': "SELECT municipio as text, cd_geocmu as value, 'municipio' as type, ST_AsGeoJSON(geom) as geojson FROM municipios WHERE unaccent(municipio) ILIKE unaccent(${key}) || '%' LIMIT 5",
                'mantain': True
            }
        ],
        'bioma': lambda p: [
            {
                'source': 'lapig',
                'id': 'search',
                'sql': "SELECT bioma as text, bioma as value, 'bioma' as type, ST_AsGeoJSON(geom) as geojson FROM biomas WHERE unaccent(bioma) ILIKE unaccent(${key}%) LIMIT 10",
                'mantain': True
            }
        ],
        'ucs': lambda p: [
            {
                'source': 'general',
                'id': 'search',
                'sql': f"SELECT nome || ' - ' || uf as text, uf, cd_geocmu, ST_AsGeoJSON(geom) as geojson FROM ucs WHERE unaccent(nome) ILIKE unaccent('%{p.get('key', '')}%') order by nome ASC LIMIT 10",
                'mantain': True
            }
        ]
    }
    return queries

default_params = {
    'type': 'bioma',
    'region': 'Cerrado'
}
