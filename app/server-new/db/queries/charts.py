def get_region_filter(type_reg, key):
    key_lower = str(key).lower()
    if type_reg == 'country':
        return "true"
    elif type_reg == 'city':
        return f"cd_geocmu='{key_lower}'"
    elif type_reg == 'state':
        return f"uf='{key_lower}'"
    elif type_reg == 'region':
        return f"lower(regiao)='{key_lower}'"
    elif type_reg == 'biome':
        return f"lower(bioma) = '{key_lower}'"
    elif type_reg == 'fronteira':
        if key_lower == 'amz_legal':
            return "amaz_legal = 1"
        elif key_lower == 'matopiba':
            return "matopiba = 1"
        elif key_lower == 'arcodesmat':
            return "arcodesmat = 1"
    return "true"

def get_year_filter(year):
    if year:
        return f"year = {year}"
    return "year = 2020"

def get_queries(params: dict = None):
    if params is None:
        params = {}
    
    region_filter = get_region_filter(params.get('typeRegion'), params.get('valueRegion'))
    year_filter = get_year_filter(params.get('year'))

    queries = {
        'resumo': lambda p: [
            {
                'source': 'lapig',
                'id': 'region',
                'sql': f"SELECT CAST(SUM(pol_ha) as double precision) as area_region FROM new_regions WHERE {region_filter}"
            },
            {
                'source': 'lapig',
                'id': 'pasture',
                'sql': f" SELECT CAST(sum(a.st_area_ha) as double precision) as value FROM pasture_col9 a WHERE {region_filter} AND {year_filter}",
                'mantain': True
            },
            {
                'source': 'lapig',
                'id': 'pasture_quality',
                'sql': f" SELECT b.name as classe, b.color, CAST(sum(a.st_area_ha) as double precision) as value FROM pasture_vigor_col9 a INNER JOIN graphic_colors as b on cast(a.classe as varchar) = b.class_number AND b.table_rel = 'pasture_quality' WHERE {region_filter} AND {year_filter} GROUP BY 1,2;",
                'mantain': True
            },
            {
                'source': 'lapig',
                'id': 'pasture_carbon_somsc',
                'sql': f"select min(c.value_min), avg(value_mean) as mean, (avg(value_mean) * (SELECT sum(area_ha) FROM pasture_col9 WHERE {region_filter} AND {year_filter})) as total from pasture_carbon_somsc_statistic_2022 c WHERE {region_filter} AND {year_filter}",
                'mantain': True
            },
            {
                'source': 'lapig',
                'id': 'pasture_carbon_somsc_mean',
                'sql': f"select avg(value_mean) as value from pasture_carbon_somsc_statistic_2022 WHERE {region_filter} AND {year_filter}",
                'mantain': True
            }
        ],
        'pastureGraph': lambda p: [
            {
                'source': 'lapig',
                'id': 'pasture',
                'sql': f"SELECT a.year::int as label, b.color, b.name as classe, sum(a.st_area_ha) as value, (SELECT CAST(SUM(pol_ha) as double precision) FROM new_regions WHERE {region_filter}) as area_mun FROM pasture_col9 a INNER JOIN graphic_colors b on b.table_rel = 'pasture' WHERE {region_filter} GROUP BY 1,2,3 ORDER BY 1 ASC;",
                'mantain': True
            },
            {
                'source': 'lapig',
                'id': 'lotacao_bovina_regions',
                'sql': f"SELECT a.year::int as label, b.color, b.name as classe, sum(a.ua) as value, (SELECT CAST(SUM(pol_ha) as double precision) FROM regions WHERE {region_filter}) as area_mun FROM lotacao_bovina_regions a INNER JOIN graphic_colors as b on b.table_rel = 'rebanho_bovino' WHERE {region_filter} GROUP BY 1,2,3 ORDER BY 1 ASC;",
                'mantain': True
            },
            {
                'source': 'lapig',
                'id': 'pasture_quality',
                'sql': f"SELECT a.year::int as label,b.color, b.name as classe, sum(a.st_area_ha) as value, (SELECT CAST(SUM(pol_ha) / 1000 as double precision) FROM regions WHERE {region_filter}) as area_mun FROM pasture_vigor_col9 a INNER JOIN graphic_colors as b on cast(a.classe as varchar) = b.class_number AND b.table_rel = 'pasture_quality' WHERE {region_filter} GROUP BY 1,2,3 ORDER BY 1 ASC;",
                'mantain': True
            },
            {
                'source': 'lapig',
                'id': 'pasture_carbon',
                'sql': f"SELECT a.year::int as label, b.color, b.name as classe, sum(value_sum) as value FROM pasture_carbon_somsc_statistic_2022 a INNER JOIN graphic_colors as b on b.table_rel = 'pasture_carbon' WHERE {region_filter} GROUP BY 1,2,3 ORDER BY 1 ASC;",
            }
        ],
        'area2': lambda p: [
            {
                'source': 'lapig',
                'id': 'pasture_quality',
                'sql': f"SELECT b.name as label, b.color, sum(a.st_area_ha) as value, (SELECT CAST(SUM(pol_ha) as double precision) FROM regions WHERE {region_filter}) as area_mun FROM pasture_vigor_col9 as A INNER JOIN graphic_colors as B on cast(a.classe as varchar) = b.class_number AND b.table_rel = 'pasture_quality' WHERE {region_filter} AND {year_filter} GROUP BY 1,2 ORDER BY 3 DESC",
                'mantain': True
            },
        ]
    }
    return queries

default_params = {}
