import requests
import json
import os
from collections import Counter

# --- CONFIGURAÇÕES ---
API_URL = "https://loteriascaixa-api.herokuapp.com/api/lotofacil"
MISTRAL_KEY = os.environ.get("MISTRAL_API_KEY")
MISTRAL_ENDPOINT = "https://api.mistral.ai/v1/chat/completions"

# --- FUNÇÕES DE ESTATÍSTICA PURA (O Python calcula, não a IA) ---
def calcular_estatisticas(jogos):
    ultimos_10 = jogos[-10:]
    ultimo_jogo = jogos[-1]
    dezenas_ultimo = [int(d) for d in ultimo_jogo['dezenas']]
    
    # 1. Frequência nos últimos 10
    todas_dezenas = []
    for jogo in ultimos_10:
        todas_dezenas.extend([int(d) for d in jogo['dezenas']])
    freq = Counter(todas_dezenas)
    
    quentes = [k for k, v in freq.items() if v >= 7] # Saíram 7+ vezes
    frias = [n for n in range(1, 26) if n not in todas_dezenas] # Não saíram
    
    # 2. Pares e Ímpares do último
    pares = len([d for d in dezenas_ultimo if d % 2 == 0])
    impares = 15 - pares
    
    # 3. Soma
    soma = sum(dezenas_ultimo)
    
    # 4. Repetidas do anterior
    penultimo = [int(d) for d in jogos[-2]['dezenas']]
    repetidas = len(set(dezenas_ultimo).intersection(penultimo))
    
    return {
        "concurso": ultimo_jogo['concurso'],
        "dezenas": dezenas_ultimo,
        "analise": {
            "quentes_top": quentes,
            "frias_zeradas": frias,
            "pares": pares,
            "impares": impares,
            "soma": soma,
            "repetidas_anterior": repetidas
        }
    }

def gerar_insights_mistral(stats):
    print("\n--- Gerando Insights com Mistral AI (Matemática Pré-calculada) ---")
    
    if not MISTRAL_KEY:
        print("ERRO: Chave MISTRAL_API_KEY não encontrada.")
        return

    # Prompt técnico que recebe os dados já mastigados
    prompt_sistema = """
    Você é um analista estatístico sênior de Lotofácil.
    Sua função NÃO é adivinhar números, mas interpretar os dados estatísticos fornecidos.
    Seja direto, técnico e use terminologia de apostador profissional (dezenas, ciclo, tendência).
    Saída OBRIGATÓRIA: JSON válido.
    """

    prompt_usuario = f"""
    Analise estes dados matemáticos REAIS do concurso {stats['concurso']}:
    
    ESTATÍSTICAS CALCULADAS:
    - Dezenas do Jogo: {stats['dezenas']}
    - Soma Total: {stats['analise']['soma']} (O ideal é entre 180 e 210)
    - Pares: {stats['analise']['pares']} / Ímpares: {stats['analise']['impares']}
    - Repetidas do anterior: {stats['analise']['repetidas_anterior']} (Média é 9)
    - Dezenas Quentes (Saíram muito nos últimos 10): {stats['analise']['quentes_top']}
    - Dezenas Frias (Não saíram nos últimos 10): {stats['analise']['frias_zeradas']}

    TAREFA:
    Gere 100 insights curtos baseados NESSES NÚMEROS.
    Misture observações sobre o jogo atual e dicas para o próximo.
    Exemplos de insight: 
    "A soma de {stats['analise']['soma']} indica um jogo baixo.", 
    "Atenção às dezenas {stats['analise']['frias_zeradas']} que estão atrasadas."

    FORMATO JSON:
    {{
        "analise_referencia": "{stats['concurso']}",
        "insights": [
            {{ "id": 1, "texto": "..." }},
            ... até 100 ...
        ]
    }}
    """

    payload = {
        "model": "mistral-small-latest", # Modelo rápido e inteligente
        "messages": [
            {"role": "system", "content": prompt_sistema},
            {"role": "user", "content": prompt_usuario}
        ],
        "temperature": 0.5,
        "response_format": {"type": "json_object"}
    }

    headers = {
        "Authorization": f"Bearer {MISTRAL_KEY}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(MISTRAL_ENDPOINT, json=payload, headers=headers)
        
        if response.status_code == 200:
            conteudo = response.json()['choices'][0]['message']['content']
            
            os.makedirs("api", exist_ok=True)
            with open("api/insights_ia.json", "w", encoding="utf-8") as f:
                f.write(conteudo)
            print("SUCESSO! Insights gerados pela Mistral.")
        else:
            print(f"ERRO API MISTRAL: {response.status_code} - {response.text}")

    except Exception as e:
        print(f"ERRO CRÍTICO: {e}")

def atualizar_dados():
    print("Iniciando atualização...")
    os.makedirs("api", exist_ok=True)

    try:
        response = requests.get(API_URL)
        if response.status_code != 200: return
        todos_jogos = response.json()
    except Exception as e:
        print(f"Erro fatal: {e}")
        return

    # Garante ordem (Antigo -> Novo)
    todos_jogos.sort(key=lambda x: x['concurso'])

    # 1. Compacto
    compacto = [{"c": j['concurso'], "d": [int(d) for d in j['dezenas']]} for j in todos_jogos]
    with open("api/lotofacil_compacto.json", "w", encoding="utf-8") as f:
        json.dump(compacto, f, separators=(',', ':'))

    # 2. Detalhado (Últimos 10 invertidos para exibição)
    ultimos_10_visual = todos_jogos[-10:]
    ultimos_10_visual.reverse()
    with open("api/lotofacil_detalhada.json", "w", encoding="utf-8") as f:
        json.dump(ultimos_10_visual, f, indent=2, ensure_ascii=False)

    # 3. IA (Passamos TODOS os jogos para cálculo estatístico correto)
    # A função calcular_estatisticas vai pegar só os últimos 10 para análise
    stats = calcular_estatisticas(todos_jogos)
    gerar_insights_mistral(stats)

if __name__ == "__main__":
    atualizar_dados()
