import requests
import json
import os
import google.generativeai as genai

# --- CONFIGURAÇÕES ---
API_URL = "https://loteriascaixa-api.herokuapp.com/api/lotofacil"
GEMINI_KEY = os.environ.get("GEMINI_API_KEY") # Pega a chave dos Secrets do GitHub

def gerar_insights_ia(dados_recentes):
    print("\n--- Iniciando Geração de Insights com IA ---")
    
    if not GEMINI_KEY:
        print("ERRO: Chave GEMINI_API_KEY não encontrada. Pulando etapa de IA.")
        return

    try:
        genai.configure(api_key=GEMINI_KEY)
        model = genai.GenerativeModel('gemini-1.5-flash') # Modelo rápido e econômico
        
        # O último sorteio é o primeiro da lista 'dados_recentes' (pois você inverteu a ordem)
        ultimo_concurso = dados_recentes[0] 
        dezenas_ultimo = ultimo_concurso['dezenas']

        prompt = f"""
        Você é um matemático especialista em padrões estocásticos de loteria.
        
        DADOS DE ENTRADA (Últimos 10 resultados, do mais recente para o antigo):
        {json.dumps(dados_recentes)}

        TAREFA:
        Analise estatisticamente esses dados, DANDO PESO TRIPLO ao concurso {ultimo_concurso['concurso']} (Dezenas: {dezenas_ultimo}).
        Gere uma lista com EXATAMENTE 100 insights curtos, objetivos e acionáveis.

        TÓPICOS OBRIGATÓRIOS NA MISTURA:
        - Padrões de repetição (comparado ao anterior).
        - Dezenas pares/ímpares.
        - Primos e Fibonacci.
        - Soma das dezenas.
        - Dezenas "quentes" (saem muito) e "frias" (atrasadas).
        - Ciclos.

        FORMATO DE SAÍDA (JSON Puro, sem Markdown):
        {{
            "analise_referencia": "{ultimo_concurso['concurso']}",
            "data_geracao": "Automática",
            "insights": [
                {{ "id": 1, "texto": "A soma das dezenas foi 210, acima da média..." }},
                {{ "id": 2, "texto": "A dezena 01 repetiu pela 3ª vez consecutiva..." }},
                ...
                {{ "id": 100, "texto": "..." }}
            ]
        }}
        """

        print("Enviando prompt para o Gemini...")
        response = model.generate_content(prompt, generation_config={"response_mime_type": "application/json"})
        
        # Salva o arquivo de insights na mesma pasta 'api'
        with open("api/insights_ia.json", "w", encoding="utf-8") as f:
            f.write(response.text)
            
        print("SUCESSO: Arquivo 'api/insights_ia.json' gerado com 100 insights.")

    except Exception as e:
        print(f"ERRO na IA: {e}")

def atualizar_dados():
    print("Iniciando atualização...")
    
    os.makedirs("api", exist_ok=True)

    try:
        response = requests.get(API_URL)
        if response.status_code != 200:
            print("Erro ao acessar API da Caixa")
            return
        
        todos_jogos = response.json()
        print(f"Total de jogos baixados: {len(todos_jogos)}")

    except Exception as e:
        print(f"Erro fatal ao baixar: {e}")
        return

    # Garante a ordenação cronológica (1, 2, 3...)
    todos_jogos.sort(key=lambda x: x['concurso'])

    # 1. CRIA O ARQUIVO COMPACTO (Histórico Total)
    compacto = []
    for jogo in todos_jogos:
        compacto.append({
            "c": jogo['concurso'],
            "d": [int(d) for d in jogo['dezenas']]
        })
    
    with open("api/lotofacil_compacto.json", "w", encoding="utf-8") as f:
        json.dump(compacto, f, separators=(',', ':'))
    print("Arquivo compacto gerado.")

    # 2. CRIA O ARQUIVO DETALHADO (Últimos 10)
    ultimos_10 = todos_jogos[-10:] 
    
    # Inverte para o mais recente ficar no topo (Índice 0)
    ultimos_10.reverse() 

    with open("api/lotofacil_detalhada.json", "w", encoding="utf-8") as f:
        json.dump(ultimos_10, f, indent=2, ensure_ascii=False)
    print("Arquivo detalhado gerado.")

    # 3. CHAMA A IA (Passo novo)
    # Passamos a lista 'ultimos_10' que já está limpa e invertida (recente primeiro)
    gerar_insights_ia(ultimos_10)

if __name__ == "__main__":
    atualizar_dados()
