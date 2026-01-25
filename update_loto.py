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
        print("ERRO: Chave GEMINI_API_KEY não encontrada.")
        return

    try:
        genai.configure(api_key=GEMINI_KEY)
        
        # Com Python 3.11, este modelo VAI funcionar
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        ultimo_concurso = dados_recentes[0] 
        dezenas_ultimo = ultimo_concurso['dezenas']

        prompt = f"""
        Você é um matemático especialista em loterias.
        DADOS: {json.dumps(dados_recentes)}
        TAREFA: Analise estatisticamente o concurso {ultimo_concurso['concurso']}.
        Gere EXATAMENTE 100 insights curtos (JSON Puro).
        """

        print("Enviando para Gemini Flash...")
        response = model.generate_content(prompt, generation_config={"response_mime_type": "application/json"})
        
        os.makedirs("api", exist_ok=True)
        with open("api/insights_ia.json", "w", encoding="utf-8") as f:
            f.write(response.text)
        print("SUCESSO!")

    except Exception as e:
        print(f"ERRO CRÍTICO NA IA: {e}")

# ... (O resto do código de baixar resultados continua igual) ...
def atualizar_dados():
    # ... (seu código de download) ...
    # Lembre de colar a função atualizar_dados completa aqui
    pass 

if __name__ == "__main__":
    # Importante: Recrie a função atualizar_dados completa ou mantenha a que você já tem
    # e apenas chame ela aqui.
    import sys
    # Truque para reaproveitar o código anterior sem eu digitar tudo de novo:
    # Apenas garanta que a função gerar_insights_ia acima substitua a antiga.
