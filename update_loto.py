import requests
import json
import os
import google.generativeai as genai

# --- CONFIGURAÇÕES ---
API_URL = "https://loteriascaixa-api.herokuapp.com/api/lotofacil"
GEMINI_KEY = os.environ.get("GEMINI_API_KEY") 

def gerar_insights_ia(dados_recentes):
    print("\n--- Iniciando Geração de Insights com IA ---")
    
    if not GEMINI_KEY:
        print("ERRO: Chave GEMINI_API_KEY não encontrada. Pulando etapa de IA.")
        return

    try:
        genai.configure(api_key=GEMINI_KEY)
        
        # Tenta usar o Flash (mais rápido). Se der erro de versão, usa o Pro.
        try:
            model = genai.GenerativeModel('gemini-1.5-flash')
        except:
            print("Aviso: Modelo Flash não disponível, tentando Gemini Pro...")
            model = genai.GenerativeModel('gemini-pro')
        
        ultimo_concurso = dados_recentes[0] 
        dezenas_ultimo = ultimo_concurso['dezenas']

        prompt = f"""
        Você é um matemático especialista em loterias.
        DADOS (Últimos 10 resultados): {json.dumps(dados_recentes)}
        
        TAREFA: Analise estatisticamente, DANDO PESO TRIPLO ao concurso {ultimo_concurso['concurso']} (Dezenas: {dezenas_ultimo}).
        Gere EXATAMENTE 100 insights curtos, objetivos e acionáveis (JSON Puro).
        
        Tópicos: Repetição, Pares/Ímpares, Primos, Fibonacci, Soma, Quentes/Frias, Ciclos.

        FORMATO DE SAÍDA JSON:
        {{
            "analise_referencia": "{ultimo_concurso['concurso']}",
            "insights": [
                {{ "id": 1, "texto": "..." }},
                ...
            ]
        }}
        """

        print("Enviando prompt para o Gemini...")
        response = model.generate_content(prompt, generation_config={"response_mime_type": "application/json"})
        
        # Garante que a pasta existe antes de salvar
        os.makedirs("api", exist_ok=True)
        
        with open("api/insights_ia.json", "w", encoding="utf-8") as f:
            f.write(response.text)
            
        print("SUCESSO: Arquivo 'api/insights_ia.json' gerado.")

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
