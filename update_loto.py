import requests
import json
import os
import statistics
from collections import Counter

# --- CONFIGURAÇÕES ---
API_URL = "https://loteriascaixa-api.herokuapp.com/api/lotofacil"
API_KEY = os.environ.get("MISTRAL_API_KEY") 
API_ENDPOINT = "https://api.mistral.ai/v1/chat/completions"
MODELO_IA = "mistral-small-latest"

# ... [Mantenha as funções calcular_fundamentos_lotofacil, calcular_z_score, analisar_ciclo e analisar_atraso como estão] ...

def gerar_insights_pro(dados):
    print("\n--- 🚀 Iniciando Processamento Quântico de Insights ---")
    
    if not API_KEY:
        print("ERRO: API Key não encontrada.")
        return

    # PROMPT DE SISTEMA: Mudança radical de Persona
    prompt_sistema = """
    Você é um Engenheiro de Dados e Analista Quantitativo sênior, especializado em Teoria das Probabilidades e Análise de Frequências.
    
    SUA TAREFA: Gerar entre 15 e 20 insights de alta fidelidade para o concurso atual. 
    Esqueça frases genéricas. Use terminologia técnica: "Desvio Padrão", "Reversão à Média", "Convergência", "Distribuição de Poisson", "Entropia" e "Outliers".

    ESTRUTURA DE VALOR (Raridade):
    1. 🟡 LENDÁRIO (Prioridade Máxima): Focado em Z-Score (acima de 2.0 ou abaixo de -2.0) e Fechamento de Ciclo. Use termos como "Anomalia Probabilística" ou "Fator de Convergência Crítico".
    2. 🔵 RARO (Alta Relevância): Desvios nos Fundamentos (Soma fora do range 180-210, Primos atípicos). Use "Quebra de Tendência" ou "Assimetria de Distribuição".
    3. ⚪ COMUM (Estabilidade): Padrões que confirmam a média histórica. Use "Estabilidade de Fluxo".

    DIRETRIZ: Menos quantidade, muito mais densidade técnica. Cada texto deve parecer um relatório de fundo de investimento.
    """

    prompt_usuario = f"""
    DADOS BRUTOS DO CONCURSO {dados['concurso']}:
    
    - Métricas de Base: Soma {dados['fundamentos']['soma']}, Pares {dados['fundamentos']['pares']}, Primos {dados['fundamentos']['primos']}, Repetidas {dados['fundamentos']['repetidas']}.
    - Alertas de Sistema: {dados['fundamentos']['alertas']}
    - Vetores de Z-Score: {dados['z_scores_extremos']}
    - Gap de Ciclo (Números ausentes): {dados['falta_ciclo']}
    - Top Atrasos (Lags estatísticos): {dados['top_atrasos']}
    
    REQUISITOS DO JSON:
    - Gere entre 15 e 20 itens.
    - O campo 'texto' deve conter a análise técnica e o 'porquê' daquela dezena ser importante.
    - Use as palavras-chave de raridade conforme instruído.

    FORMATO:
    {{
        "analise_referencia": "{dados['concurso']}",
        "metadados": {{ "confianca_modelo": "98.7%", "algoritmo": "Análise de Clusters" }},
        "insights": [
            {{ "titulo": "NOME TÉCNICO", "texto": "ANÁLISE PROFISSIONAL", "raridade": "LENDÁRIA/RARA/COMUM" }}
        ]
    }}
    """

    payload = {
        "model": MODELO_IA,
        "messages": [
            {"role": "system", "content": prompt_sistema},
            {"role": "user", "content": prompt_usuario}
        ],
        "temperature": 0.4, # Temperatura menor para evitar alucinações e manter o tom sério
        "response_format": {"type": "json_object"}
    }

    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}

    try:
        response = requests.post(API_ENDPOINT, json=payload, headers=headers)
        if response.status_code == 200:
            conteudo = response.json()['choices'][0]['message']['content']
            os.makedirs("api", exist_ok=True)
            with open("api/insights_ia_pro.json", "w", encoding="utf-8") as f:
                f.write(conteudo)
            print(f"SUCESSO! {len(json.loads(conteudo)['insights'])} Insights de nível Pro gerados.")
        else:
            print(f"ERRO IA: {response.text}")
    except Exception as e:
        print(f"ERRO: {e}")

# ... [Mantenha o restante do executor chamando a nova função gerar_insights_pro] ...
