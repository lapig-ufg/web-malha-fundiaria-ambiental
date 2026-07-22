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
        ],
        # Excedente Florestal por município (nacional, ano mais recente):
        # mesma fórmula do gráfico regional de Excedente Florestal
        # (natural_vegetation_regions.class_1 - APP/RL natural), agrupada
        # por município e unida à geometria de municipios.geom para
        # alimentar a camada de mapa (coroplético).
        'forest-surplus-municipios': lambda p: [
            {
                'source': 'lapig',
                'id': 'forest_surplus_municipios',
                'sql': """
                    WITH total AS (
                        SELECT
                            cd_mun,
                            CAST(COALESCE(SUM(class_1), 0) AS double precision) as total_class_1,
                            CAST(COALESCE(SUM(class_1), 0) + COALESCE(SUM(class_2), 0) AS double precision) as total_area
                        FROM natural_vegetation_regions
                        WHERE year = (SELECT MAX(year) FROM natural_vegetation_regions)
                        GROUP BY cd_mun
                    ), app_rl AS (
                        SELECT
                            cd_mun,
                            CAST(COALESCE(SUM(class_1), 0) AS double precision) as app_rl_class_1
                        FROM natural_vegetation_regions_app_rl_1985_2024
                        WHERE year = (SELECT MAX(year) FROM natural_vegetation_regions_app_rl_1985_2024)
                          AND categoria IN ('Área de preservação permanente', 'Reserva Legal')
                        GROUP BY cd_mun
                    )
                    SELECT
                        m.cd_geocmu as cd_mun,
                        m.municipio,
                        ST_AsGeoJSON(ST_SimplifyPreserveTopology(m.geom, 0.005)) as geojson,
                        ROUND(CAST((total.total_class_1 - COALESCE(app_rl.app_rl_class_1, 0)) AS numeric), 4) as excedente_ha,
                        ROUND(CAST(
                            (total.total_class_1 - COALESCE(app_rl.app_rl_class_1, 0))
                              / NULLIF(total.total_area, 0) * 100
                        AS numeric), 4) as excedente_pct
                    FROM municipios m
                    JOIN total ON total.cd_mun = m.cd_geocmu
                    LEFT JOIN app_rl ON app_rl.cd_mun = m.cd_geocmu
                """,
                'mantain': True
            }
        ],
        # Déficit de APP / Reserva Legal por município (nacional, ano mais
        # recente): % da área da categoria (APP ou RL) que NÃO é vegetação
        # natural (class_2), mesma fórmula usada nas abas APP/RL de
        # "Evolução da Vegetação Natural" (deficit = class_2 / (class_1 + class_2)).
        'deficit-app-municipios': lambda p: [
            {
                'source': 'lapig',
                'id': 'deficit_app_municipios',
                'sql': """
                    SELECT
                        m.cd_geocmu as cd_mun,
                        m.municipio,
                        ST_AsGeoJSON(ST_SimplifyPreserveTopology(m.geom, 0.005)) as geojson,
                        ROUND(CAST(COALESCE(SUM(v.class_2), 0) AS numeric), 4) as deficit_ha,
                        ROUND(CAST(
                            COALESCE(SUM(v.class_2), 0)
                              / NULLIF(COALESCE(SUM(v.class_1), 0) + COALESCE(SUM(v.class_2), 0), 0) * 100
                        AS numeric), 4) as deficit_pct
                    FROM municipios m
                    JOIN natural_vegetation_regions_app_rl_1985_2024 v ON v.cd_mun = m.cd_geocmu
                    WHERE v.categoria = 'Área de preservação permanente'
                      AND v.year = (SELECT MAX(year) FROM natural_vegetation_regions_app_rl_1985_2024)
                    GROUP BY m.cd_geocmu, m.municipio, m.geom
                """,
                'mantain': True
            }
        ],
        'deficit-rl-municipios': lambda p: [
            {
                'source': 'lapig',
                'id': 'deficit_rl_municipios',
                'sql': """
                    SELECT
                        m.cd_geocmu as cd_mun,
                        m.municipio,
                        ST_AsGeoJSON(ST_SimplifyPreserveTopology(m.geom, 0.005)) as geojson,
                        ROUND(CAST(COALESCE(SUM(v.class_2), 0) AS numeric), 4) as deficit_ha,
                        ROUND(CAST(
                            COALESCE(SUM(v.class_2), 0)
                              / NULLIF(COALESCE(SUM(v.class_1), 0) + COALESCE(SUM(v.class_2), 0), 0) * 100
                        AS numeric), 4) as deficit_pct
                    FROM municipios m
                    JOIN natural_vegetation_regions_app_rl_1985_2024 v ON v.cd_mun = m.cd_geocmu
                    WHERE v.categoria = 'Reserva Legal'
                      AND v.year = (SELECT MAX(year) FROM natural_vegetation_regions_app_rl_1985_2024)
                    GROUP BY m.cd_geocmu, m.municipio, m.geom
                """,
                'mantain': True
            }
        ]
    }
    return queries

default_params = {
    'type': 'bioma',
    'region': 'Cerrado'
}
