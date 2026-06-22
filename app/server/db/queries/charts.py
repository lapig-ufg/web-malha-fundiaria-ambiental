def get_region_filter(type_reg, key):
    key_lower = str(key).lower()
    if type_reg == 'country':
        return "true"
    elif type_reg == 'city':
        return f"cd_geocmu='{key_lower}'"
    elif type_reg == 'state':
        return f"lower(uf)='{key_lower}'"
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

def get_region_filter_coverage(type_reg, key):
    key_lower = str(key).lower()
    if type_reg == 'country':
        return "true"
    elif type_reg == 'city':
        return f"cd_mun='{key_lower}'"
    elif type_reg == 'state':
        return f"lower(uf)='{key_lower}'"
    elif type_reg == 'biome':
        return f"lower(bioma) = '{key_lower}'"
    return "true"

def get_region_filter_mfa(type_reg, key):
    key_lower = str(key).lower()
    if type_reg == 'country':
        return "true"
    elif type_reg == 'city':
        return f"municipality_code='{key_lower}'"
    elif type_reg == 'state':
        return f"municipality_code IN (SELECT DISTINCT cd_geocmu FROM new_regions WHERE lower(uf) = '{key_lower}')"
    elif type_reg == 'biome':
        return f"municipality_code IN (SELECT DISTINCT cd_geocmu FROM new_regions WHERE lower(bioma) = '{key_lower}')"
    elif type_reg == 'region':
        return f"municipality_code IN (SELECT DISTINCT cd_geocmu FROM new_regions WHERE lower(regiao) = '{key_lower}')"
    elif type_reg == 'fronteira':
        if key_lower == 'amz_legal':
            return "municipality_code IN (SELECT DISTINCT cd_geocmu FROM new_regions WHERE amaz_legal = 1)"
        elif key_lower == 'matopiba':
            return "municipality_code IN (SELECT DISTINCT cd_geocmu FROM new_regions WHERE matopiba = 1)"
        elif key_lower == 'arcodesmat':
            return "municipality_code IN (SELECT DISTINCT cd_geocmu FROM new_regions WHERE arcodesmat = 1)"
    return "true"

def get_year_filter(year):
    if year:
        return f"year = {year}"
    return "year = 2020"

def get_queries(params: dict = None):
    if params is None:
        params = {}

    region_filter = get_region_filter(params.get('typeRegion'), params.get('valueRegion'))
    region_filter_coverage = get_region_filter_coverage(params.get('typeRegion'), params.get('valueRegion'))
    region_filter_mfa = get_region_filter_mfa(params.get('typeRegion'), params.get('valueRegion'))
    year_filter = get_year_filter(params.get('year'))

    type_region = params.get('typeRegion')
    comparison_col = 'uf' if type_region == 'country' else 'municipio'
    comparison_col_coverage = 'uf' if type_region == 'country' else 'municipio'

    queries = {
        'resumo': lambda p: [
            {
                'source': 'lapig',
                'id': 'property_count',
                'sql': f"SELECT COUNT(*) as property_count FROM malha_fundiaria_ambiental WHERE {region_filter_mfa}"
            },
            {
                'source': 'lapig',
                'id': 'region',
                'sql': f"SELECT CAST(SUM(pol_ha) as double precision) as area_region FROM new_regions WHERE {region_filter}"
            },
            {
                'source': 'lapig',
                'id': 'coverage_natural',
                'sql': f"""
                    SELECT
                        'app' as label,
                        '#228B22' as color,
                        COALESCE(SUM(app_class_1), 0) as value
                    FROM land_tenure_vegetation_2024
                    WHERE {region_filter_coverage}
                    UNION ALL
                    SELECT
                        'rl' as label,
                        '#006400' as color,
                        COALESCE(SUM(rl_class_1), 0) as value
                    FROM land_tenure_vegetation_2024
                    WHERE {region_filter_coverage}
                    UNION ALL
                    SELECT
                        'mfa' as label,
                        '#4169E1' as color,
                        COALESCE(SUM(mfa_class_1), 0) as value
                    FROM land_tenure_vegetation_2024
                    WHERE {region_filter_coverage}
                """,
                'mantain': True
            },
            {
                'source': 'lapig',
                'id': 'coverage_comparison_app',
                'sql': f"""
                    SELECT UPPER({comparison_col_coverage}) as label, 'natural' as classe, '#228B22' as color, SUM(app_class_1) as value FROM land_tenure_vegetation_2024 WHERE {region_filter_coverage} GROUP BY 1, 2, 3
                    UNION ALL
                    SELECT UPPER({comparison_col_coverage}) as label, 'non_natural' as classe, '#8B4513' as color, SUM(app_class_2) as value FROM land_tenure_vegetation_2024 WHERE {region_filter_coverage} GROUP BY 1, 2, 3
                    ORDER BY 1, 2
                """,
                'mantain': True
            },
            {
                'source': 'lapig',
                'id': 'coverage_comparison_rl',
                'sql': f"""
                    SELECT UPPER({comparison_col_coverage}) as label, 'natural' as classe, '#228B22' as color, SUM(rl_class_1) as value FROM land_tenure_vegetation_2024 WHERE {region_filter_coverage} GROUP BY 1, 2, 3
                    UNION ALL
                    SELECT UPPER({comparison_col_coverage}) as label, 'non_natural' as classe, '#8B4513' as color, SUM(rl_class_2) as value FROM land_tenure_vegetation_2024 WHERE {region_filter_coverage} GROUP BY 1, 2, 3
                    ORDER BY 1, 2
                """,
                'mantain': True
            },
            {
                'source': 'lapig',
                'id': 'coverage_comparison_mfa',
                'sql': f"""
                    SELECT UPPER({comparison_col_coverage}) as label, 'natural' as classe, '#228B22' as color, SUM(mfa_class_1) as value FROM land_tenure_vegetation_2024 WHERE {region_filter_coverage} GROUP BY 1, 2, 3
                    UNION ALL
                    SELECT UPPER({comparison_col_coverage}) as label, 'non_natural' as classe, '#8B4513' as color, SUM(mfa_class_2) as value FROM land_tenure_vegetation_2024 WHERE {region_filter_coverage} GROUP BY 1, 2, 3
                    ORDER BY 1, 2
                """,
                'mantain': True
            }
        ],
        'vegetation_evolution': lambda p: [
            {
                'source': 'lapig',
                'id': 'vegetation_evolution',
                'sql': f"""
                    SELECT
                        year as label,
                        '#228B22' as color,
                        CAST(COALESCE(SUM(class_1), 0) AS double precision)
                          / NULLIF(CAST(COALESCE(SUM(class_1), 0) + COALESCE(SUM(class_2), 0) AS double precision), 0)
                          * 100 as value
                    FROM natural_vegetation_regions
                    WHERE {region_filter_coverage}
                    GROUP BY year
                    ORDER BY year
                """,
                'mantain': True
            }
        ],
        'vegetation_evolution_by_categoria': lambda p: [
            {
                'source': 'lapig',
                'id': 'vegetation_evolution_by_categoria',
                'sql': f"""
                    SELECT
                        year as label,
                        '#228B22' as color,
                        CAST(COALESCE(SUM(class_1), 0) AS double precision)
                          / NULLIF(CAST(COALESCE(SUM(class_1), 0) + COALESCE(SUM(class_2), 0) AS double precision), 0)
                          * 100 as value
                    FROM natural_vegetation_regions_app_rl_1985_2024
                    WHERE categoria = ${{categoria}} AND {region_filter_coverage}
                    GROUP BY year
                    ORDER BY year
                """,
                'mantain': True
            }
        ]
    }
    return queries

default_params = {}