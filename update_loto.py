import requests
import json
import os
import statistics
from collections import Counter

# --- CONFIGURAÇÕES ---
API_URL = "https://loteriascaixa-api.herokuapp.com/api/lotofacil"
# Você pode usar MISTRAL ou GROQ. Aqui configurei para MISTRAL por ser mais analítica.
API_KEY = os.environ.get("MISTRAL_API_KEY") 
API_ENDPOINT = "https://api.mistral.ai/v1/chat/completions"
MODELO_IA = "mistral-small-latest"

# ==============================================================================
# 🧠 CÁLCULOS MATEMÁTICOS DE ELITE
# ==============================================================================

def calcular_z_score(todos_jogos):
    """Detecta anomalias estatísticas graves."""
    ultimos_30 = todos_jogos[-30:]
    todas_dezenas = [int(d) for j in ultimos_30 for d in j['dezenas']]
    freq = Counter(todas_dezenas)
    
    valores = list(freq.values())
    media = statistics.mean(valores)
    desvio = statistics.stdev(valores) if len(valores) > 1 else 1
    
    analise = {}
    for n in range(1, 26):
        qtd = freq.get(n, 0)
        z_score = (qtd - media) / desvio
        analise[n] = round(z_score, 2)
    return analise

def analisar_ciclo(todos_jogos):
    """Descobre números que faltam para fechar o ciclo (Gatilho para Rara/Lendária)."""
    acumulado = set()
    for jogo in reversed(todos_jogos):
        dezenas = {int(d) for d in jogo['dezenas']}
        acumulado.update(dezenas)
        if len(acumulado) == 25: break
    
    faltam = list(set(range(1, 26)) - acumulado)
    return faltam

def analisar_atraso(todos_jogos):
    atrasos = {}
    for n in range(1, 26):
        count = 0
        for jogo in reversed(todos_jogos):
            if n not in [int(d) for d in jogo['dezenas']]: count += 1
            else: break
        atrasos[n] = count
    return atrasos

def preparar_dados_ia(todos_jogos):
    ultimo = todos_jogos[-1]
    
    z_scores = calcular_z_score(todos_jogos)
    ciclo = analisar_ciclo(todos_jogos)
    atrasos = analisar_atraso(todos_jogos)
    
    # Filtra Oportunidades de Ouro (Para forçar cartas Lendárias)
    ouro = []
    for n, z in z_scores.items():
        if z > 1.8: ouro.append(f"Dezena {n} (Z-Score Explosivo {z})")
        if z < -1.8: ouro.append(f"Dezena {n} (Hiper Atrasada Z-Score {z})")
    
    return {
        "concurso": ultimo['concurso'],
        "z_scores_anormais": ouro,
        "falta_ciclo": ciclo,
        "top_atrasos": [k for k,v in sorted(atrasos.items(), key=lambda x: x[1], reverse=True)[:5]]
    }

# ==============================================================================
# 🔮 O ORÁCULO (Prompt Engenheirado para seu App)
# ==============================================================================

def gerar_insights(dados):
    print("\n--- Gerando Insights Gamificados ---")
    
    if not API_KEY:
        print("ERRO: API Key não encontrada.")
        return

    prompt_sistema = """
    Você é o 'Oráculo da Loto', um sistema de IA integrado a um App Gamificado.
    
    SUA MISSÃO: Criar "Cartas de Insight" com raridades baseadas na matemática.
    
    REGRAS DE RARIDADE (Você DEVE usar as palavras-chave para ativar o App):
    
    1. 🟡 LENDÁRIA (Use palavras: "Certeza", "Padrão Ouro", "Foco Total"):
       - Use APENAS quando o Z-Score for extremo ou para fechar Ciclo.
       - Título deve ser impactante (Ex: "Oportunidade Única").
    
    2. 🔵 RARA (Use palavras: "Atenção", "Ciclo", "Importante"):
       - Use para dezenas atrasadas ou tendências fortes.
       - Título deve ser técnico (Ex: "Análise de Ciclo").
    
    3. ⚪ COMUM (Texto normal):
       - Use para observações gerais de soma, pares, etc.
       - Título simples (Ex: "Curiosidade").

    Gere 30 insights variados (aprox: 3 Lendários, 7 Raros, 20 Comuns).
    O JSON deve ter 'titulo' e 'texto'.
    """

    prompt_usuario = f"""
    DADOS MATEMÁTICOS REAIS (Concurso {dados['concurso']}):
    
    🏆 CANDIDATAS A LENDÁRIAS (Z-Score Extremo): 
    {dados['z_scores_anormais']}
    
    💎 CANDIDATAS A RARAS (Faltam no Ciclo): 
    {dados['falta_ciclo']}
    
    📉 CANDIDATAS A RARAS (Mais Atrasadas): 
    {dados['top_atrasos']}
    
    Gere o JSON. Seja criativo nos Títulos.
    FORMATO:
    {{
        "analise_referencia": "{dados['concurso']}",
        "insights": [
            {{ "titulo": "...", "texto": "..." }},
            ...
        ]
    }}
    """

    payload = {
        "model": MODELO_IA,
        "messages": [
            {"role": "system", "content": prompt_sistema},
            {"role": "user", "content": prompt_usuario}
        ],
        "temperature": 0.7,
        "response_format": {"type": "json_object"}
    }

    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}

    try:
        response = requests.post(API_ENDPOINT, json=payload, headers=headers)
        if response.status_code == 200:
            conteudo = response.json()['choices'][0]['message']['content']
            
            # Salva
            os.makedirs("api", exist_ok=True)
            with open("api/insights_ia.json", "w", encoding="utf-8") as f:
                f.write(conteudo)
            print("SUCESSO! Insights gerados.")
        else:
            print(f"ERRO IA: {response.text}")
    except Exception as e:
        print(f"ERRO: {e}")

# ==============================================================================
# 🚀 EXECUTOR
# ==============================================================================

def atualizar_dados():
    print("Iniciando...")
    os.makedirs("api", exist_ok=True)
    try:
        r = requests.get(API_URL)
        if r.status_code != 200: return
        jogos = r.json()
        jogos.sort(key=lambda x: x['concurso'])
        
        # Gera arquivos básicos
        compacto = [{"c": j['concurso'], "d": [int(d) for d in j['dezenas']]} for j in jogos]
        with open("api/lotofacil_compacto.json", "w", encoding="utf-8") as f:
            json.dump(compacto, f, separators=(',', ':'))
            
        with open("api/lotofacil_detalhada.json", "w", encoding="utf-8") as f:
            json.dump(jogos[-10:][::-1], f, indent=2, ensure_ascii=False) # Últimos 10 invertidos

        # Gera IA
        dados = preparar_dados_ia(jogos)
        gerar_insights(dados)
        
    except Exception as e:
        print(f"Erro fatal: {e}")

if __name__ == "__main__":
    atualizar_dados()
