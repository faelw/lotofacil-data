import requests
import json
import os
from collections import Counter

# --- CONFIGURAÇÕES ---
API_URL = "https://loteriascaixa-api.herokuapp.com/api/lotofacil"
MISTRAL_KEY = os.environ.get("MISTRAL_API_KEY")
MISTRAL_ENDPOINT = "https://api.mistral.ai/v1/chat/completions"

# --- MATEMÁTICA ESTATÍSTICA CORRIGIDA (REGRA DOS 60%) ---
def calcular_estatisticas_avancadas(jogos):
    # Analisa os últimos 10 jogos
    ultimos_10 = jogos[-10:]
    ultimo_jogo = jogos[-1]
    dezenas_ultimo = [int(d) for d in ultimo_jogo['dezenas']]
    
    # 1. Análise de Frequência (%)
    todas_dezenas = []
    for jogo in ultimos_10:
        todas_dezenas.extend([int(d) for d in jogo['dezenas']])
    freq = Counter(todas_dezenas)
    
    # Classificação baseada na média de 60% (6 saídas em 10 jogos)
    quentes = [] # Acima de 60% (7, 8, 9, 10 vezes)
    mornas = []  # Na média (5 ou 6 vezes)
    frias = []   # Abaixo da média (0 a 4 vezes)

    for num in range(1, 26):
        qtd = freq.get(num, 0)
        porcentagem = (qtd / 10) * 100
        
        info = f"{num} ({int(porcentagem)}%)"
        
        if qtd >= 7:
            quentes.append(info)
        elif qtd <= 4:
            frias.append(info)
        else:
            mornas.append(info)
    
    # 2. Padrões
    primos_lista = [2, 3, 5, 7, 11, 13, 17, 19, 23]
    fibonacci_lista = [1, 2, 3, 5, 8, 13, 21]
    
    qtd_primos = len([d for d in dezenas_ultimo if d in primos_lista])
    qtd_fibonacci = len([d for d in dezenas_ultimo if d in fibonacci_lista])
    
    pares = len([d for d in dezenas_ultimo if d % 2 == 0])
    impares = 15 - pares
    soma = sum(dezenas_ultimo)
    
    penultimo = [int(d) for d in jogos[-2]['dezenas']]
    repetidas = len(set(dezenas_ultimo).intersection(penultimo))
    
    return {
        "concurso": ultimo_jogo['concurso'],
        "dezenas": dezenas_ultimo,
        "analise": {
            "soma": soma,
            "pares": pares,
            "impares": impares,
            "primos": qtd_primos,
            "fibonacci": qtd_fibonacci,
            "repetidas": repetidas,
            # Listas já formatadas com a %
            "lista_quentes": quentes,
            "lista_frias": frias,
            "lista_mornas": mornas
        }
    }

def gerar_insights_mistral(stats):
    print("\n--- Gerando Insights Estatísticos Reais (Mistral AI) ---")
    
    if not MISTRAL_KEY:
        print("ERRO: Chave MISTRAL_API_KEY não encontrada.")
        return

    prompt_sistema = """
    Você é um matemático rigoroso especialista em Lotofácil.
    REGRA DE OURO: A probabilidade padrão da Lotofácil é 60%.
    - Se uma dezena saiu menos de 50% das vezes, ela é FRIA (está devendo).
    - Se saiu 60%, está NORMAL.
    - Se saiu acima de 70%, está QUENTE (pode estar saturada).
    
    Gere insights curtos e técnicos. Use Emojis.
    Saída: JSON estrito.
    """

    prompt_usuario = f"""
    Analise os dados matemáticos do concurso {stats['concurso']}:
    
    DADOS DO ÚLTIMO JOGO:
    - Resultado: {stats['dezenas']}
    - Soma: {stats['analise']['soma']}
    - Padrão: {stats['analise']['pares']} Pares / {stats['analise']['impares']} Ímpares
    
    ESTATÍSTICA DOS ÚLTIMOS 10 JOGOS:
    🔥 DEZENAS QUENTES (Estão saindo muito acima da média de 60%): 
    {stats['analise']['lista_quentes']}
    
    🧊 DEZENAS FRIAS (Estão saindo pouco, abaixo de 50%): 
    {stats['analise']['lista_frias']}
    
    ⚖️ DEZENAS MORNAS (Dentro do esperado):
    {stats['analise']['lista_mornas']}

    TAREFA:
    Gere EXATAMENTE 40 insights divididos nestes 4 grupos:

    1. 📊 ANÁLISE TÉCNICA (10 insights): Comente a soma, primos e repetidas.
    2. 🔥 ALERTAS DE QUENTES (10 insights): Avise que essas dezenas estão com frequência alta (70%+).
    3. 🧊 OPORTUNIDADES FRIAS (10 insights): Sugira atenção às frias (elas tendem a voltar para equilibrar a média de 60%).
    4. 🔮 SUGESTÕES DE EQUILÍBRIO (10 insights): Dicas gerais.

    ESTILO:
    - Ex: "🧊 A dezena 03 está fria (30%), muito abaixo da média de 60%."
    - Ex: "🔥 A dezena 20 está fervendo (80%), saindo muito acima do esperado."
    - Use termos como "Desvio Padrão", "Tendência de Retorno", "Saturação".

    FORMATO JSON OBRIGATÓRIO:
    {{
        "analise_referencia": "{stats['concurso']}",
        "insights": [
            {{ "id": 1, "texto": "..." }},
            ... até 40 ...
        ]
    }}
    """

    payload = {
        "model": "mistral-small-latest",
        "messages": [
            {"role": "system", "content": prompt_sistema},
            {"role": "user", "content": prompt_usuario}
        ],
        "temperature": 0.5, # Temperatura mais baixa para ser mais exato na matemática
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
            print("SUCESSO! Insights gerados com lógica de 60%.")
        else:
            print(f"ERRO MISTRAL: {response.status_code} - {response.text}")

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

    todos_jogos.sort(key=lambda x: x['concurso'])

    compacto = [{"c": j['concurso'], "d": [int(d) for d in j['dezenas']]} for j in todos_jogos]
    with open("api/lotofacil_compacto.json", "w", encoding="utf-8") as f:
        json.dump(compacto, f, separators=(',', ':'))

    ultimos_10 = todos_jogos[-10:]
    ultimos_10.reverse()
    with open("api/lotofacil_detalhada.json", "w", encoding="utf-8") as f:
        json.dump(ultimos_10, f, indent=2, ensure_ascii=False)

    stats = calcular_estatisticas_avancadas(todos_jogos)
    gerar_insights_mistral(stats)

if __name__ == "__main__":
    atualizar_dados()
