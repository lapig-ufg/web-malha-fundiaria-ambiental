# Documentação do Dataset Parquet

Este documento descreve os arquivos `.parquet` localizados na pasta `/data`, contendo metadados técnicos e descrições das colunas.

## Resumo dos Arquivos

| Arquivo | Registros | Tamanho Estimado | Descrição Geral |
| :--- | :--- | :--- | :--- |
| `areas_preservacao_permanente.parquet` | 41.421.419 | ~23.3 GB | Dados geográficos de Áreas de Preservação Permanente (APP). |
| `malha_fundiaria.parquet` | 7.418.211 | ~3.4 GB | Malha fundiária consolidada. |
| `reserva_legal.parquet` | 13.289.772 | ~11.6 GB | Dados geográficos de Reserva Legal (RL). |

---

## 1. areas_preservacao_permanente.parquet
**Descrição**: Contém polígonos e atributos das Áreas de Preservação Permanente.

### Esquema de Colunas
| Coluna | Tipo | Descrição |
| :--- | :--- | :--- |
| `GEOCODIGO` | INTEGER | Código geográfico identificador (ex: IBGE). |
| `CD_UF` | INTEGER | Código da Unidade da Federação. |
| `AREA_M` | BIGINT | Área calculada em metros quadrados. |
| `fonte` | VARCHAR | Fonte original dos dados. |
| `cls_malha` | VARCHAR | Classe ou categoria da malha. |
| `geometry` | GEOMETRY | Geometria espacial (South America Albers - ESRI:102033) |

---

## 2. malha_fundiaria.parquet
**Descrição**: Base de dados da malha fundiária, integrando diferentes fontes de posse e propriedade.

### Esquema de Colunas
| Coluna | Tipo | Descrição |
| :--- | :--- | :--- |
| `fonte` | VARCHAR | Fonte original do dado (ex: INCRA, CAR, etc). |
| `cod_malha` | VARCHAR | Código interno da malha. |
| `cls_malha` | VARCHAR | Classificação fundiária (ex: Privado, Assentamento). |
| `area_total_ha` | DOUBLE | Área total em hectares. |
| `geom` | GEOMETRY | Geometria espacial (South America Albers - ESRI:102033). |
| `geo_id` | VARCHAR | Identificador único geográfico. |
| `GEOCODIGO` | VARCHAR | Código geográfico associado. |
| `CD_UF` | VARCHAR | Código da Unidade da Federação. |

---

## 3. reserva_legal.parquet
**Descrição**: Informações sobre as áreas declaradas como Reserva Legal.

### Esquema de Colunas
| Coluna | Tipo | Descrição |
| :--- | :--- | :--- |
| `fonte` | VARCHAR | Fonte original dos dados. |
| `cod_malha` | VARCHAR | Código identificador da malha. |
| `cls_malha` | VARCHAR | Classificação da malha. |
| `geo_id` | VARCHAR | Identificador único. |
| `GEOCODIGO` | VARCHAR | Código geográfico. |
| `CD_UF` | VARCHAR | Código da Unidade da Federação. |
| `geometry` | GEOMETRY | Geometria espacial (South America Albers - ESRI:102033). |

---

## Observações Técnicas
- **Formato**: Apache Parquet (colunar), otimizado para leitura analítica.
- **Sistema de Referência**: As geometrias estão em **South America Albers Equal Area Conic (ESRI:102033)**.
- **Ferramentas Recomendadas**: DuckDB para consultas rápidas e GeoPandas/PyArrow para processamento Python.
