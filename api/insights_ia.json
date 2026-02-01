import requests
import json
import os
import statistics
from collections import Counter
from uuid import uuid4
from datetime import datetime

# ======================================================
# 0. CONFIGURAÇÕES GERAIS (AGORA COM GOOGLE)
# ======================================================

LOT_API = "https://loteriascaixa-api.herokuapp.com/api/lotofacil"
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY") # Certifique-se de configurar esta chave
GEMINI_ENDPOINT = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GOOGLE_API_KEY}"

OUTPUT_DIR = "api"
OUTPUT_FILE = "insights_ia.json"

# ======================================================
# 1. COLETA E VALIDAÇÃO (MANTIDA)
# ======================================================

def carregar_e_validar_dados():
    r = requests.get(LOT_API)
    r.raise_for_status()
    dados = r.json()
    if len(dados) < 2: raise ValueError("Histórico insuficiente.")
    return dados

# ======================================================
# 2. FUNÇÕES MATEMÁTICAS (MANTIDAS COM CLUSTER FACTOR)
# ======================================================

def calcular_z_scores(historico):
    ocorrencias = Counter()
    for c in historico: ocorrencias.update(c["dezenas"])
    valores = list(ocorrencias.values())
    media, desvio = statistics.mean(valores), statistics.pstdev(valores)
    return {str(dez): (freq - media) / desvio if desvio else 0 for dez, freq in ocorrencias.items()}, media, desvio

def calcular_ciclo(historico):
    ultimo = {}
    total = len(historico)
    for i, concurso in enumerate(historico):
        for d in concurso["dezenas"]: ultimo[int(d)] = i
    return {str(d): total - ultimo.get(d, 0) for d in range(1, 26)}

def calcular_fundamentos(concurso, anterior):
    dezenas = sorted([int(d) for d in concurso["dezenas"]])
    gaps = [dezenas[i+1] - dezenas[i] for i in range(len(dezenas)-1)]
    cluster_factor = statistics.pstdev(gaps)
    
    return {
        "soma": sum(dezenas),
        "pares": sum(1 for d in dezenas if d % 2 == 0),
        "repetidas": len(set(dezenas) & set([int(d) for d in anterior["dezenas"]])),
        "cluster_factor": round(cluster_factor, 2)
    }

# ======================================================
# 3. GERADOR DE INSIGHTS (ESTRUTURA BASE)
# ======================================================

def gerar_insights_base(dados):
    ins = []
    # Z-Score
    for dez, z in dados["z_scores"].items():
        if abs(z) >= 1.5:
            ins.append({
                "id": f"z_{dez}",
                "tipo": "estatistica_z",
                "titulo": f"Volatilidade na Dezena {dez}",
                "base": {"dezena": dez, "z_score": round(z, 2)}
            })
    # Agrupamento
    cf = dados["fundamentos"]["cluster_factor"]
    if cf > 1.9:
        ins.append({
            "id": "cluster_anomalia",
            "tipo": "comportamento_grupo",
            "titulo": "Formação de Clusters Atípicos",
            "base": {"cluster_factor": cf, "mensagem": "As dezenas apresentaram um padrão de agrupamento raro."}
        })
    return ins[:12]

# ======================================================
# 4. ENRIQUECIMENTO COM GOOGLE GEMINI
# ======================================================

def enriquecer_com_google(insights):
    if not GOOGLE_API_KEY or not insights:
        return insights

    prompt_texto = (
        "Você é um Analista Quantitativo Sênior. Sua tarefa é interpretar dados estatísticos de loteria. "
        "Para cada item no JSON abaixo, escreva um campo 'texto' explicando a relevância técnica daquela métrica. "
        "Seja direto, profissional e use termos como 'desvio padrão', 'frequência esperada' e 'distribuição'. "
        "MANTENHA TODOS OS IDs E NÚMEROS ORIGINAIS. "
        "RETORNE APENAS O JSON PURO, SEM MARKDOWN, NO FORMATO: {\"insights\": [...]}\n\n"
        f"DADOS: {json.dumps(insights)}"
    )

    payload = {
        "contents": [{
            "parts": [{"text": prompt_texto}]
        }],
        "generationConfig": {
            "temperature": 0.2,
            "responseMimeType": "application/json",
        }
    }

    try:
        r = requests.post(GEMINI_ENDPOINT, json=payload, timeout=30)
        r.raise_for_status()
        
        # O Gemini retorna uma estrutura aninhada: candidates -> content -> parts
        raw_response = r.json()["candidates"][0]["content"]["parts"][0]["text"]
        dados_ia = json.loads(raw_response)
        
        return dados_ia.get("insights", insights)
    except Exception as e:
        print(f"❌ Erro na API do Google: {e}")
        return insights

# ======================================================
# 5. MAIN
# ======================================================

def main():
    try:
        dados_brutos = carregar_e_validar_dados()
        atual, anterior = dados_brutos[-1], dados_brutos[-2]
        
        z_scores, _, _ = calcular_z_scores(dados_brutos[:-1])
        ciclo = calcular_ciclo(dados_brutos[:-1])
        fundamentos = calcular_fundamentos(atual, anterior)

        pacote_base = {
            "z_scores": z_scores,
            "ciclo": ciclo,
            "fundamentos": fundamentos
        }

        insights_brutos = gerar_insights_base(pacote_base)
        
        # Chamada ao Google Gemini
        print("🤖 Consultando Oracle Google Gemini...")
        insights_ricos = enriquecer_com_google(insights_brutos)

        output = {
            "concurso": atual["concurso"],
            "gerado_em": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "insights": insights_ricos
        }

        os.makedirs(OUTPUT_DIR, exist_ok=True)
        with open(os.path.join(OUTPUT_DIR, OUTPUT_FILE), "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)

        print(f"✅ Processado com sucesso via Google Gemini.")

    except Exception as e:
        print(f"🚨 Erro: {e}")

if __name__ == "__main__":
    main()
