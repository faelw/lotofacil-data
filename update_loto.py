import requests
import json
import os
import google.generativeai as genai
from bs4 import BeautifulSoup
from datetime import datetime

# ======================================================
# CONFIGURAÇÕES
# ======================================================
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

# Arquivo de saída para o Git
OUTPUT_PATH = "api/insights_ia.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# ======================================================
# COLETA MULTI-FONTE
# ======================================================
def capturar_resultado():
    # FONTE 1: API Oficial (ServiceBus)
    url_oficial = "https://servicebus2.caixa.gov.br/portaldeloterias/api/lotofacil"
    try:
        print("📡 Acessando API Oficial da Caixa...")
        r = requests.get(url_oficial, headers=HEADERS, timeout=10, verify=False)
        if r.status_code == 200:
            d = r.json()
            return {
                "concurso": d['numero'],
                "dezenas": sorted([n.zfill(2) for n in d['listaDezenas']]),
                "data": d['dataApuracao']
            }
    except Exception as e:
        print(f"⚠️ Erro na API: {e}")

    # FONTE 2: Scraping (Plano B)
    try:
        print("🔍 Iniciando Scraping de emergência...")
        url_web = "https://loterias.caixa.gov.br/wps/portal/loterias/landing/lotofacil"
        r = requests.get(url_web, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(r.content, 'html.parser')
        dezenas = sorted([n.text.zfill(2) for n in soup.select('.resultado-loto li')])
        if dezenas:
            return {"concurso": "Último", "dezenas": dezenas, "data": datetime.now().strftime("%d/%m/%Y")}
    except Exception as e:
        print(f"🚨 Falha total na coleta: {e}")
        return None

# ======================================================
# MOTOR DE IA (GEMINI)
# ======================================================
def processar_ia(dados_loteria):
    prompt = f"""
    Você é o analista sênior do app LotoLab.
    DADOS DO CONCURSO {dados_loteria['concurso']}: {dados_loteria['dezenas']}
    
    TAREFA:
    1. Analise a distribuição (ímpares/pares, primos e soma).
    2. Crie 3 insights curtos e impactantes para o apostador.
    3. Use um tom profissional mas que gere curiosidade (instigue o usuário a usar o fechamento matemático do app).

    RETORNE APENAS JSON:
    {{
        "analise_tecnica": {{ "soma": 0, "pares": 0, "impares": 0 }},
        "insights": [
            {{ "titulo": "Título Curto", "texto": "Explicação técnica rápida", "tipo": "alerta/oportunidade" }}
        ]
    }}
    """
    try:
        response = model.generate_content(prompt)
        # Limpa blocos de código markdown se o Gemini os incluir
        limpo = response.text.replace('```json', '').replace('```', '').strip()
        return json.loads(limpo)
    except:
        return {"error": "IA temporariamente offline"}

# ======================================================
# MAIN
# ======================================================
def main():
    print(f"--- Iniciando Atualização LotoLab {datetime.now()} ---")
    
    dados = capturar_resultado()
    if not dados:
        print("❌ Não foi possível obter novos dados.")
        return

    print(f"✅ Dados obtidos: Concurso {dados['concurso']}")
    
    print("🤖 Consultando IA para gerar insights...")
    insights_ia = processar_ia(dados)

    # Monta o pacote final que o App vai ler
    pacote_final = {
        "status": "success",
        "ultimo_concurso": dados,
        "inteligencia": insights_ia,
        "atualizado_em": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    # Garante que a pasta api exista (importante para o Git)
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(pacote_final, f, ensure_ascii=False, indent=4)
    
    print(f"🎉 Arquivo {OUTPUT_PATH} atualizado com sucesso!")

if __name__ == "__main__":
    main()
