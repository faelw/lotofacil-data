import requests
import json
import os
from google import genai
from google.genai import types

# --- CONFIGURAÇÕES ---
API_URL = "https://loteriascaixa-api.herokuapp.com/api/lotofacil"
GEMINI_KEY = os.environ.get("GEMINI_API_KEY") 

def gerar_insights_ia(dados_recentes):
    print("\n--- Iniciando Geração de Insights (Estratégia Multi-Modelo) ---")
    
    if not GEMINI_KEY:
        print("ERRO: Chave GEMINI_API_KEY não encontrada.")
        return

    # Lista de tentativas. Se um falhar, tenta o próximo.
    modelos_para_tentar = [
        'gemini-1.5-flash',       # Tentativa 1: O padrão atual
        'gemini-1.5-flash-001',   # Tentativa 2: Versão específica
        'gemini-1.5-pro',         # Tentativa 3: Versão mais potente
        'gemini-2.0-flash-exp',   # Tentativa 4: Experimental novo
        'gemini-pro'              # Tentativa 5: O clássico (quase impossível falhar)
    ]

    client = genai.Client(api_key=GEMINI_KEY)
    
    ultimo_concurso = dados_recentes[0] 
    dezenas_ultimo = ultimo_concurso['dezenas']

    prompt = f"""
    Você é um matemático especialista em loterias.
    DADOS: {json.dumps(dados_recentes)}
    TAREFA: Analise estatisticamente o concurso {ultimo_concurso['concurso']}.
    Gere EXATAMENTE 100 insights curtos (JSON Puro).
    """

    for modelo_atual in modelos_para_tentar:
        try:
            print(f"Tentando conectar com o modelo: {modelo_atual}...")
            
            response = client.models.generate_content(
                model=modelo_atual,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type='application/json',
                    temperature=0.7
                )
            )
            
            # Se chegou aqui, funcionou!
            if response.text:
                os.makedirs("api", exist_ok=True)
                with open("api/insights_ia.json", "w", encoding="utf-8") as f:
                    f.write(response.text)
                print(f"SUCESSO! Insights gerados usando o modelo: {modelo_atual}")
                return # Sai da função, pois já conseguiu

        except Exception as e:
            # Se der erro 404 ou qualquer outro, apenas avisa e deixa o loop continuar
            print(f"Falha no modelo {modelo_atual}. Tentando o próximo... (Erro: {e})")

    print("ERRO FINAL: Nenhum dos modelos funcionou. Verifique sua API Key.")

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
