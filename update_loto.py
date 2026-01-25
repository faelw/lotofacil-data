import requests
import json
import os
from groq import Groq # <--- Biblioteca Nova

# --- CONFIGURAÇÕES ---
API_URL = "https://loteriascaixa-api.herokuapp.com/api/lotofacil"
GROQ_KEY = os.environ.get("GROQ_API_KEY") 

def gerar_insights_ia(dados_recentes):
    print("\n--- Iniciando Geração de Insights (Via Groq/Llama 3) ---")
    
    if not GROQ_KEY:
        print("ERRO: Chave GROQ_API_KEY não encontrada.")
        return

    try:
        client = Groq(api_key=GROQ_KEY)
        
        ultimo_concurso = dados_recentes[0] 
        dezenas_ultimo = ultimo_concurso['dezenas']

        # O Llama 3 precisa de instruções muito claras sobre JSON
        prompt_sistema = """
        Você é um matemático especialista em loterias.
        Sua saída deve ser EXCLUSIVAMENTE um objeto JSON válido.
        Não escreva nada antes ou depois do JSON.
        """

        prompt_usuario = f"""
        DADOS (Últimos 10 resultados): {json.dumps(dados_recentes)}
        
        TAREFA: 
        1. Analise o concurso {ultimo_concurso['concurso']} (Dezenas: {dezenas_ultimo}).
        2. Gere 100 insights curtos sobre padrões, repetidas, pares/ímpares, primos, soma, quentes/frias.
        
        FORMATO JSON OBRIGATÓRIO:
        {{
            "analise_referencia": "{ultimo_concurso['concurso']}",
            "insights": [
                {{ "id": 1, "texto": "..." }},
                ... ate 100 ...
            ]
        }}
        """

        print("Enviando para Llama 3 (70b Versatile)...")
        
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": prompt_sistema},
                {"role": "user", "content": prompt_usuario}
            ],
            model="llama-3.3-70b-versatile", # Modelo muito inteligente e rápido
            temperature=0.5, # Equilíbrio entre criatividade e precisão
            response_format={"type": "json_object"} # Força sair JSON perfeito
        )

        conteudo_json = chat_completion.choices[0].message.content
        
        os.makedirs("api", exist_ok=True)
        with open("api/insights_ia.json", "w", encoding="utf-8") as f:
            f.write(conteudo_json)
            
        print("SUCESSO! Arquivo 'api/insights_ia.json' gerado pela Groq.")

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
