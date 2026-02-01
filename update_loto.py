import requests
import json
import os
import statistics
from collections import Counter
from uuid import uuid4
from datetime import datetime

# ======================================================
# 0. CONFIGURAÇÕES GERAIS
# ======================================================

LOT_API = "https://loteriascaixa-api.herokuapp.com/api/lotofacil"
MISTRAL_API_KEY = os.environ.get("MISTRAL_API_KEY")
MISTRAL_ENDPOINT = "https://api.mistral.ai/v1/chat/completions"
MISTRAL_MODEL = "mistral-small-latest"

OUTPUT_DIR = "api"
OUTPUT_FILE = "insights_ia.json"

# ======================================================
# 1. COLETA E VALIDAÇÃO DE DADOS
# ======================================================

def carregar_e_validar_dados():
    r = requests.get(LOT_API)
    r.raise_for_status()
    dados = r.json()
    
    if len(dados) < 2:
        raise ValueError("Histórico insuficiente para análise.")
        
    atual = dados[-1]
    anterior = dados[-2]
    
    # Validação de integridade: Concurso sequencial e 15 dezenas
    if int(atual["concurso"]) != int(anterior["concurso"]) + 1:
        print(f"⚠️ Aviso: Salto detectado entre concursos {anterior['concurso']} e {atual['concurso']}")
    
    if len(atual["dezenas"]) != 15:
        raise ValueError(f"Concurso {atual['concurso']} possui número inválido de dezenas.")

    return dados

# ======================================================
# 2. FUNÇÕES MATEMÁTICAS AVANÇADAS
# ======================================================

def calcular_z_scores(historico):
    ocorrencias = Counter()
    for c in historico:
        ocorrencias.update(c["dezenas"])

    valores = list(ocorrencias.values())
    media = statistics.mean(valores)
    desvio = statistics.pstdev(valores)

    z_scores = {str(dez): (freq - media) / desvio if desvio else 0 
                for dez, freq in ocorrencias.items()}

    return z_scores, media, desvio

def calcular_ciclo(historico):
    ultimo = {}
    total = len(historico)
    for i, concurso in enumerate(historico):
        for d in concurso["dezenas"]:
            ultimo[int(d)] = i
    
    return {str(d): total - ultimo.get(d, 0) for d in range(1, 26)}

def calcular_fundamentos(concurso, anterior):
    # Garantir dezenas como inteiros e ordenadas para cálculo de gaps
    dezenas = sorted([int(d) for d in concurso["dezenas"]])
    dezenas_ant = set([int(d) for d in anterior["dezenas"]])
    
    soma = sum(dezenas)
    pares = sum(1 for d in dezenas if d % 2 == 0)
    primos = sum(1 for d in dezenas if d in {2,3,5,7,11,13,17,19,23})
    repetidas = len(set(dezenas) & dezenas_ant)

    # Cálculo do Cluster Factor (Desvio Padrão dos Gaps)
    # Gap médio teórico na Lotofácil é ~1.6
    gaps = [dezenas[i+1] - dezenas[i] for i in range(len(dezenas)-1)]
    cluster_factor = statistics.pstdev(gaps)

    alertas = []
    if soma < 180 or soma > 210: alertas.append("Soma fora da faixa histórica")
    if cluster_factor > 2.0: alertas.append("Alta concentração/agrupamento (Clusters)")

    return {
        "soma": soma,
        "pares": pares,
        "primos": primos,
        "repetidas": repetidas,
        "cluster_factor": round(cluster_factor, 2),
        "alertas": alertas
    }

# ======================================================
# 3. GERADOR DE INSIGHTS (LÓGICA QUANT)
# ======================================================

def gerar_insights(dados):
    ins = []

    # Z-Scores
    for dez, z in dados["z_scores"].items():
        if abs(z) >= 1.3:
            nivel = "LENDÁRIA" if abs(z) >= 2.0 else "RARA"
            ins.append({
                "id": f"z_{dez}_{uuid4().hex[:4]}",
                "tipo": "zscore",
                "raridade": nivel,
                "titulo": f"Anomalia na dezena {dez}",
                "base": {"dezena": dez, "z_score": round(z, 2)}
            })

    # Ciclo Crítico
    for dez, gap in dados["ciclo"].items():
        if gap >= 10:
            ins.append({
                "id": f"ciclo_{dez}_{uuid4().hex[:4]}",
                "tipo": "ciclo",
                "raridade": "RARA",
                "titulo": f"Atraso crítico: Dezena {dez}",
                "base": {"dezena": dez, "concursos_ausente": gap}
            })

    # Agrupamento (Cluster Factor)
    cf = dados["fundamentos"]["cluster_factor"]
    if cf > 1.9:
        ins.append({
            "id": f"cluster_{uuid4().hex[:4]}",
            "tipo": "fundamento",
            "raridade": "RARA",
            "titulo": "Formação de Clusters Atípicos",
            "base": {"cluster_factor": cf, "contexto": "Dezenas muito próximas ou saltos irregulares."}
        })

    return ins[:15]

# ======================================================
# 4. ENRIQUECIMENTO COM IA (RESILIENTE)
# ======================================================

def enriquecer_com_ia(insights, concurso_n):
    if not MISTRAL_API_KEY or not insights:
        return insights

    prompt_sistema = (
        "Você é um analista quantitativo de loterias. "
        "Explique os insights técnicos de forma profissional e breve. "
        "MANTENHA OS IDs E NÚMEROS ORIGINAIS. "
        "O 'Cluster Factor' mede o agrupamento das dezenas (acima de 2.0 é raro). "
        "Retorne apenas JSON no formato: {\"insights\": [...]}"
    )

    payload = {
        "model": MISTRAL_MODEL,
        "messages": [
            {"role": "system", "content": prompt_sistema},
            {"role": "user", "content": json.dumps(insights)}
        ],
        "temperature": 0.2,
        "response_format": {"type": "json_object"}
    }

    try:
        r = requests.post(MISTRAL_ENDPOINT, json=payload, 
                         headers={"Authorization": f"Bearer {MISTRAL_API_KEY}", "Content-Type": "application/json"},
                         timeout=20)
        r.raise_for_status()
        dados_ia = r.json()
        return json.loads(dados_ia["choices"][0]["message"]["content"]).get("insights", insights)
    except Exception as e:
        print(f"❌ Falha na IA: {e}. Mantendo dados brutos.")
        return insights

# ======================================================
# 5. EXECUÇÃO
# ======================================================

def main():
    try:
        dados_brutos = carregar_e_validar_dados()
        atual, anterior = dados_brutos[-1], dados_brutos[-2]
        historico = dados_brutos[:-1]

        z_scores, media, desvio = calcular_z_scores(historico)
        ciclo = calcular_ciclo(historico)
        fundamentos = calcular_fundamentos(atual, anterior)

        pacote = {
            "concurso": atual["concurso"],
            "z_scores": z_scores,
            "ciclo": ciclo,
            "fundamentos": fundamentos
        }

        insights_brutos = gerar_insights(pacote)
        insights_ricos = enriquecer_com_ia(insights_brutos, atual["concurso"])

        final_output = {
            "analise_referencia": atual["concurso"],
            "data_analise": datetime.utcnow().isoformat(),
            "metricas_globais": {
                "soma": fundamentos["soma"],
                "cluster_factor": fundamentos["cluster_factor"]
            },
            "insights": insights_ricos
        }

        os.makedirs(OUTPUT_DIR, exist_ok=True)
        with open(os.path.join(OUTPUT_DIR, OUTPUT_FILE), "w", encoding="utf-8") as f:
            json.dump(final_output, f, ensure_ascii=False, indent=2)

        print(f"✅ Sucesso: Concurso {atual['concurso']} processado.")

    except Exception as e:
        print(f"🚨 Erro crítico no pipeline: {e}")

if __name__ == "__main__":
    main()
