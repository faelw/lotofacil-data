import requests
import json
import os
from google import genai
from google.genai import types

# --- CONFIGURAÇÕES ---
API_URL = "https://loteriascaixa-api.herokuapp.com/api/lotofacil"
GEMINI_KEY = os.environ.get("GEMINI_API_KEY") 

def gerar_insights_ia(dados_recentes):
    print("\n--- Iniciando Geração de Insights (Via Google Gemini) ---")
    
    if not GEMINI_KEY:
        print("ERRO: Chave GEMINI_API_KEY não encontrada.")
        return

    try:
        # Inicializa o cliente com a nova biblioteca
        client = genai.Client(api_key=GEMINI_KEY)
        
        ultimo_concurso = dados_recentes[0] 
        dezenas_ultimo = ultimo_concurso['dezenas']

        prompt = f"""
        Você é um matemático especialista em loterias.
        
        DADOS DE ENTRADA (Últimos 10 resultados): 
        {json.dumps(dados_recentes)}
        
        TAREFA:
        1. Analise estatisticamente o concurso {ultimo_concurso['concurso']} (Dezenas: {dezenas_ultimo}).
        2. Gere EXATAMENTE 100 insights curtos, objetivos e acionáveis sobre padrões, repetições, ciclos, primos, etc.

        FORMATO DE SAÍDA OBRIGATÓRIO (JSON PURO):
        {{
            "analise_referencia": "{ultimo_concurso['concurso']}",
            "insights": [
                {{ "id": 1, "texto": "Insight aqui..." }},
                ... ate 100 ...
            ]
        }}
        """

        print("Enviando para Gemini 1.5 Flash...")
        
        # Chamada usando a nova SDK
        response = client.models.generate_content(
            model='gemini-1.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type='application/json',
                temperature=0.7
            )
        )
        
        # Verifica se houve resposta válida
        if response.text:
            os.makedirs("api", exist_ok=True)
            with open("api/insights_ia.json", "w", encoding="utf-8") as f:
                f.write(response.text)
            print("SUCESSO! Arquivo 'api/insights_ia.json' gerado pelo Gemini.")
        else:
            print("AVISO: O Gemini retornou uma resposta vazia.")

    except Exception as e:
        print(f"ERRO CRÍTICO NA IA: {e}")

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

    # 3. IA
    gerar_insights_ia(ultimos_10)

if __name__ == "__main__":
    atualizar_dados()
