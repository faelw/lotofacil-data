import requests
import json
import os
from collections import Counter

# --- CONFIGURAÇÕES ---
API_URL = "https://loteriascaixa-api.herokuapp.com/api/lotofacil"
MISTRAL_KEY = os.environ.get("MISTRAL_API_KEY")
MISTRAL_ENDPOINT = "https://api.mistral.ai/v1/chat/completions"

# --- MATEMÁTICA PESADA (Calculada pelo Python) ---
def calcular_estatisticas_avancadas(jogos):
    ultimos_10 = jogos[-10:]
    ultimo_jogo = jogos[-1]
    dezenas_ultimo = [int(d) for d in ultimo_jogo['dezenas']]
    
    # 1. Análise de Frequência
    todas_dezenas = []
    for jogo in ultimos_10:
        todas_dezenas.extend([int(d) for d in jogo['dezenas']])
    freq = Counter(todas_dezenas)
    
    quentes = [k for k, v in freq.items() if v >= 7]
    frias = [n for n in range(1, 26) if n not in todas_dezenas]
    
    # 2. Padrões Específicos
    primos_lista = [2, 3, 5, 7, 11, 13, 17, 19, 23]
    fibonacci_lista = [1, 2, 3, 5, 8, 13, 21]
    
    qtd_primos = len([d for d in dezenas_ultimo if d in primos_lista])
    qtd_fibonacci = len([d for d in dezenas_ultimo if d in fibonacci_lista])
    
    pares = len([d for d in dezenas_ultimo if d % 2 == 0])
    impares = 15 - pares
    soma = sum(dezenas_ultimo)
    
    # 3. Repetidas
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
            "quentes": quentes,
            "frias": frias
        }
    }

def gerar_insights_mistral(stats):
    print("\n--- Gerando 40 Insights Premium com Mistral AI ---")
    
    if not MISTRAL_KEY:
        print("ERRO: Chave MISTRAL_API_KEY não encontrada.")
        return

    # Prompt projetado para QUALIDADE e não quantidade
    prompt_sistema = """
    Você é um mentor especialista em Lotofácil.
    Sua missão é gerar insights curtos, impactantes e visualmente atraentes (use Emojis).
    NÃO repita informações. Varie o assunto.
    Saída: JSON estrito.
    """

    prompt_usuario = f"""
    Analise os dados matemáticos do concurso {stats['concurso']}:
    
    DADOS CALCULADOS:
    - Resultado: {stats['dezenas']}
    - Soma: {stats['analise']['soma']} (Ideal: 180-210)
    - Pares/Ímpares: {stats['analise']['pares']} Pares / {stats['analise']['impares']} Ímpares
    - Primos: {stats['analise']['primos']} (Média é 5 ou 6)
    - Fibonacci: {stats['analise']['fibonacci']} (Média é 4 ou 5)
    - Repetidas do anterior: {stats['analise']['repetidas']}
    - Dezenas Fervendo (Quentes): {stats['analise']['quentes']}
    - Dezenas Zeradas (Frias): {stats['analise']['frias']}

    TAREFA:
    Gere EXATAMENTE 40 insights divididos nestes 4 grupos (mas entregue tudo numa lista única misturada):

    1. 📊 ANÁLISE DO JOGO ATUAL (10 insights): Comente se a soma foi alta, se vieram muitos primos, etc.
    2. 🔥 TENDÊNCIAS QUENTES (10 insights): Fale sobre as dezenas que não param de sair.
    3. 🧊 OPORTUNIDADES FRIAS (10 insights): Alerte sobre os números atrasados que podem voltar.
    4. 🔮 PREVISÕES E PADRÕES (10 insights): Dicas de equilíbrio para o próximo jogo.

    ESTILO DO TEXTO:
    - Use emojis no início (ex: ⚠️, 🔥, 💰, 📉, 🎯).
    - Seja direto. Ex: "🔥 A dezena 01 está imparável, saindo em 80% dos jogos."
    - Use palavras como: "Alerta", "Certeza Estatística", "Ciclo", "Foco".

    FORMATO JSON OBRIGATÓRIO:
    {{
        "analise_referencia": "{stats['concurso']}",
        "insights": [
            {{ "id": 1, "texto": "🔥 Insight 1..." }},
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
        "temperature": 0.6, # Um pouco mais criativo
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
            
            # Validação básica
            try:
                json_test = json.loads(conteudo)
                if len(json_test['insights']) < 10:
                    print("Aviso: A IA gerou poucos insights.")
            except:
                pass

            os.makedirs("api", exist_ok=True)
            with open("api/insights_ia.json", "w", encoding="utf-8") as f:
                f.write(conteudo)
            print("SUCESSO! 40 Insights Premium gerados.")
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

    # 1. Compacto
    compacto = [{"c": j['concurso'], "d": [int(d) for d in j['dezenas']]} for j in todos_jogos]
    with open("api/lotofacil_compacto.json", "w", encoding="utf-8") as f:
        json.dump(compacto, f, separators=(',', ':'))

    # 2. Detalhado (Últimos 10)
    ultimos_10 = todos_jogos[-10:]
    ultimos_10.reverse()
    with open("api/lotofacil_detalhada.json", "w", encoding="utf-8") as f:
        json.dump(ultimos_10, f, indent=2, ensure_ascii=False)

    # 3. IA (Calcula estatísticas sobre todos os jogos, mas foca nos recentes)
    stats = calcular_estatisticas_avancadas(todos_jogos)
    gerar_insights_mistral(stats)

if __name__ == "__main__":
    atualizar_dados()
