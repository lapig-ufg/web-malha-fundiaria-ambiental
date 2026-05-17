import urllib.request
import json
from typing import Any

def buscar_dados_api(url: str) -> list[dict]:
    """Faz a chamada na API e retorna o JSON."""
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode('utf-8'))
            # Garante que estamos trabalhando com uma lista de objetos
            return data if isinstance(data, list) else [data]
    except Exception as e:
        print(f"Erro ao buscar a URL: {e}")
        return []

def analisar_objetos(objetos: list[dict], nome_classe: str, registro_classes: dict) -> str:
    """
    Navega recursivamente pela lista de objetos, mescla as chaves,
    infere os tipos e gera a definição da classe.
    """
    estatisticas_campos = {}
    total_objetos = len(objetos)

    # Passo 1: Mapear todas as chaves, seus tipos e frequência
    for obj in objetos:
        if not isinstance(obj, dict):
            continue
            
        for chave, valor in obj.items():
            if chave not in estatisticas_campos:
                estatisticas_campos[chave] = {'tipos': set(), 'contagem': 0, 'aninhados': []}
            
            estatisticas_campos[chave]['contagem'] += 1

            if isinstance(valor, dict):
                # Guarda objetos aninhados para análise recursiva futura
                estatisticas_campos[chave]['aninhados'].append(valor)
            elif isinstance(valor, list):
                estatisticas_campos[chave]['tipos'].add('list')
            elif valor is not None:
                # Extrai o nome do tipo do Python (ex: 'str', 'int', 'bool')
                estatisticas_campos[chave]['tipos'].add(type(valor).__name__)

    # Passo 2: Construir a string da classe
    definicao_classe = f"class {nome_classe}:\n"
    tem_campos = False

    for chave, stats in estatisticas_campos.items():
        tem_campos = True
        
        # Se a chave não aparece em 100% dos objetos, ela é opcional
        eh_opcional = stats['contagem'] < total_objetos

        if stats['aninhados']:
            # Chamada RECURSIVA para sub-dicionários
            nome_classe_aninhada = chave.capitalize()
            analisar_objetos(stats['aninhados'], nome_classe_aninhada, registro_classes)
            tipo_campo = nome_classe_aninhada
        else:
            tipos = stats['tipos']
            if not tipos:
                tipo_campo = "Any"
            else:
                # Junta múltiplos tipos caso existam (ex: int | float)
                tipo_campo = " | ".join(list(tipos))

        # Adiciona o typing de Null/None se for opcional
        if eh_opcional:
            tipo_campo = f"{tipo_campo} | None"

        definicao_classe += f"    {chave}: {tipo_campo}\n"

    if not tem_campos:
        definicao_classe += "    pass\n"

    # Salva no registro (dicionário global que guarda os resultados)
    registro_classes[nome_classe] = definicao_classe
    return nome_classe

def gerar_modelos_da_url(url: str, nome_classe_raiz: str = "RootClass"):
    """Função principal que orquestra o processo e imprime o resultado."""
    dados = buscar_dados_api(url)
    if not dados:
        return

    registro_classes = {}
    analisar_objetos(dados, nome_classe_raiz, registro_classes)

    # Imprime as classes. Usamos reversed para que classes dependentes (ex: Origin)
    # sejam impressas antes da classe principal (ex: EnimagmaClass)
    print("--- MODELOS GERADOS ---\n")
    for nome, definicao in reversed(registro_classes.items()):
        print(definicao)

# =========================================================
# COMO TESTAR LOCALMENTE SEM UMA URL REAL (MOCK)
# =========================================================
if __name__ == "__main__":
    raw = buscar_dados_api("https://ows.lapig.iesa.ufg.br/api/map/limits?lang=pt")[0]
    
    data = []
    for r in raw.items():
        for n in r[1]:
            data.append(n)
            
    registro_teste = {}
    analisar_objetos(data, "Layer", registro_teste)
    for nome, def_classe in reversed(registro_teste.items()):
        print(def_classe)
        
    # Para rodar com sua URL real, basta descomentar a linha abaixo:
    # gerar_modelos_da_url("https://sua-api.com/endpoint", "EnimagmaClass")