import requests
import json
import os
import statistics
from collections import Counter

# --- CONFIGURAÇÕES ---
API_URL = "https://loteriascaixa-api.herokuapp.com/api/lotofacil"
MISTRAL_KEY = os.environ.get("MISTRAL_API_KEY")
MISTRAL_ENDPOINT = "https://api.mistral.ai/v1/chat/completions"

# ==============================================================================
# 🧠 ENGINE QUANTITATIVA (Matemática de Mercado Financeiro)
# ==============================================================================

def calcular_z_score(todos_jogos):
    """
    Calcula o Z-Score de cada dezena.
    Z-Score > 2.0: Anomalia positiva (Está saindo MUITO acima do normal).
    Z-Score < -2.0: Anomalia negativa (Está sumida estatisticamente).
    """
    ultimos_30 = todos_jogos[-30:] # Amostra estatística relevante
    todas_dezenas = [int(d) for j in ultimos_30 for d in j['dezenas']]
    freq = Counter(todas_dezenas)
    
    # Média e Desvio Padrão da amostra
    valores = list(freq.values())
    media = statistics.mean(valores)
    desvio = statistics.stdev(valores) if len(valores) > 1 else 1
    
    analise_z = {}
    for n in range(1, 26):
        qtd = freq.get(n, 0)
        z_score = (qtd - media) / desvio
        
        status = "Normal"
        if z_score > 1.5: status = "🔥 Superaquecida (Overbought)"
        elif z_score > 0.5: status = "📈 Tendência Alta"
        elif z_score < -1.5: status = "❄️ Congelada (Oversold)"
        elif z_score < -0.5: status = "📉 Tendência Baixa"
            
        analise_z[n] = {
            "score": round(z_score, 2),
            "status": status,
            "frequencia_30_jogos": qtd
        }
    return analise_z

def analise_matrix(dezenas):
    """Analisa a distribuição espacial no volante (Linhas e Colunas)."""
    matriz = [[0]*5 for _ in range(5)]
    linhas = [0]*5
    colunas = [0]*5
    
    # Mapeia números para posições da matriz 5x5
    # 01 02 03 04 05
    # 06 07 ...
    for d in dezenas:
        d_idx = d - 1
        l = d_idx // 5
        c = d_idx % 5
        linhas[l] += 1
        colunas[c] += 1
        
    # Detecta desbalanceamento
    linha_cheia = [i+1 for i, x in enumerate(linhas) if x >= 4]
    linha_vazia = [i+1 for i, x in enumerate(linhas) if x <= 1]
    
    return {
        "linhas_sobrecarregadas": linha_cheia,
        "linhas_vazias": linha_vazia,
        "distribuicao_linhas": linhas,
        "distribuicao_colunas": colunas
    }

def preparar_dados_blackbox(todos_jogos):
    ultimo_jogo = todos_jogos[-1]
    dezenas = [int(d) for d in ultimo_jogo['dezenas']]
    
    # 1. Z-Score (O coração do sistema)
    z_scores = calcular_z_score(todos_jogos)
    
    # 2. Matrix Espacial
    matrix = analise_matrix(dezenas)
    
    # 3. Padrões Mágicos
    primos = [2, 3, 5, 7, 11, 13, 17, 19, 23]
    na_primos = len([d for d in dezenas if d in primos])
    
    soma = sum(dezenas)
    
    # Filtra os destaques para economizar tokens e focar a IA
    top_quentes = [f"Dezena {k}: {v['status']}" for k, v in z_scores.items() if v['score'] > 1.0]
    top_frias = [f"Dezena {k}: {v['status']}" for k, v in z_scores.items() if v['score'] < -1.0]
    
    return {
        "concurso": ultimo_jogo['concurso'],
        "resultado_bruto": dezenas,
        "indicadores_tecnicos": {
            "soma": soma,
            "primos": na_primos,
            "analise_espacial": f"Linhas Cheias: {matrix['linhas_sobrecarregadas']} | Linhas Vazias: {matrix['linhas_vazias']}"
        },
        "radar_dezenas": {
            "alertas_alta": top_quentes,
            "alertas_baixa": top_frias
        }
    }

# ==============================================================================
# 🤖 ORÁCULO AI (Mistral Persona: Quant Analyst)
# ==============================================================================

def gerar_insights_mistral(dados):
    print("\n--- Rodando Análise Mega Blaster (Mistral) ---")
    
    if not MISTRAL_KEY:
        print("ERRO: MISTRAL_API_KEY ausente.")
        return

    prompt_sistema = """
    Você é 'O Oráculo', uma IA de Elite especializada em estatística avançada de loterias.
    Você não chuta. Você analisa o Z-SCORE (Desvio Padrão) e a GEOMETRIA do jogo.
    
    Seu tom de voz: Profissional, Misterioso e Matemático.
    Use Emojis exclusivos para categorias.
    
    MISSÃO: Gerar 40 insights cirúrgicos.
    """

    prompt_usuario = f"""
    Analise o Relatório Quantitativo do concurso {dados['concurso']}:
    
    📡 RADAR DE ANOMALIAS (Z-Score):
    {json.dumps(dados['radar_dezenas'], indent=2)}
    
    📐 GEOMETRIA DO JOGO:
    {json.dumps(dados['indicadores_tecnicos'], indent=2)}
    
    Gere 40 INSIGHTS divididos EXATAMENTE nestas 4 categorias (10 de cada):

    1. 🧬 DNA DO JOGO (Análise técnica): Fale sobre a soma, linhas cheias e padrão espacial.
    2. 🚀 FOGUETES (Tendência de Alta): Analise as dezenas superaquecidas (Overbought).
    3. ⚓ ÂNCORAS (Tendência de Baixa): Analise as dezenas congeladas (Oversold) que devem voltar (Mean Reversion).
    4. 🔮 O VEREDITO (Previsões): Cruze os dados para sugerir equilíbrio.

    ESTILO:
    - "🧬 A Linha 3 veio sobrecarregada, indicando desvio espacial."
    - "🚀 A dezena 20 rompeu o Z-Score positivo, indicando exaustão."
    - "⚓ A dezena 04 está em zona de sobrevenda, alta chance de repique."

    FORMATO JSON OBRIGATÓRIO:
    {{
        "analise_referencia": "{dados['concurso']}",
        "insights": [
            {{ "id": 1, "texto": "..." }},
            ... 40 itens ...
        ]
    }}
    """

    payload = {
        "model": "mistral-small-latest",
        "messages": [
            {"role": "system", "content": prompt_sistema},
            {"role": "user", "content": prompt_usuario}
        ],
        "temperature": 0.5,
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
            print("SUCESSO! Insights Mega Blaster gerados.")
        else:
            print(f"ERRO MISTRAL: {response.status_code}")

    except Exception as e:
        print(f"ERRO CRÍTICO: {e}")

# ==============================================================================
# 🚀 EXECUTOR PRINCIPAL
# ==============================================================================

def atualizar_dados():
    print("Iniciando Sistema Mega Blaster...")
    os.makedirs("api", exist_ok=True)

    try:
        response = requests.get(API_URL)
        if response.status_code != 200: return
        todos_jogos = response.json()
    except: return

    todos_jogos.sort(key=lambda x: x['concurso'])

    # Gera arquivos básicos para o App
    compacto = [{"c": j['concurso'], "d": [int(d) for d in j['dezenas']]} for j in todos_jogos]
    with open("api/lotofacil_compacto.json", "w", encoding="utf-8") as f:
        json.dump(compacto, f, separators=(',', ':'))

    ultimos_10 = todos_jogos[-10:]
    ultimos_10.reverse()
    with open("api/lotofacil_detalhada.json", "w", encoding="utf-8") as f:
        json.dump(ultimos_10, f, indent=2, ensure_ascii=False)

    # Executa a Análise Quantitativa
    dados_processados = preparar_dados_blackbox(todos_jogos)
    gerar_insights_mistral(dados_processados)

if __name__ == "__main__":
    atualizar_dados()
