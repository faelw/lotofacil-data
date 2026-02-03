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

# Caminhos dos arquivos no seu repositório Git
PATH_IA = "api/insights_ia.json"
PATH_DETALHADA = "api/lotofacil_detalhada.json"
PATH_COMPACTO = "api/lotofacil_compacto.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# ======================================================
# COLETA ROBUSTA
# ======================================================
def capturar_dados_completos():
    url_oficial = "https://servicebus2.caixa.gov.br/portaldeloterias/api/lotofacil"
    try:
        r = requests.get(url_oficial, headers=HEADERS, timeout=15, verify=False)
        if r.status_code == 200:
            return r.json()
    except Exception as e:
        print(f"⚠️ Erro na coleta: {e}")
        return None

# ======================================================
# PROCESSAMENTO DE ARQUIVOS
# ======================================================
def salvar_arquivos_json(dados_brutos, insights_ia):
    os.makedirs("api", exist_ok=True)
    
    # 1. ARQUIVO DETALHADO (Dados da Caixa + IA)
    detalhada = {
        "concurso": dados_brutos['numero'],
        "data": dados_brutos['dataApuracao'],
        "dezenas": sorted(dados_brutos['listaDezenas']),
        "premiacao": dados_brutos['listaRateioPremio'],
        "acumulado": dados_brutos['acumulado'],
        "proximo_estimado": dados_brutos['valorEstimadoProximoConcurso'],
        "ia_insights": insights_ia
    }
    
    # 2. ARQUIVO COMPACTO (Para carregamento ultra-rápido)
    compacto = {
        "n": dados_brutos['numero'],
        "d": sorted(dados_brutos['listaDezenas']),
        "s": 1 if dados_brutos['acumulado'] else 0 # s de status acumulado
    }

    # Escrita física dos arquivos
    with open(PATH_DETALHADA, "w", encoding="utf-8") as f:
        json.dump(detalhada, f, ensure_ascii=False, indent=4)
        
    with open(PATH_COMPACTO, "w", encoding="utf-8") as f:
        json.dump(compacto, f, ensure_ascii=False, indent=2)

    with open(PATH_IA, "w", encoding="utf-8") as f:
        json.dump(insights_ia, f, ensure_ascii=False, indent=4)

# ======================================================
# INTEGRAÇÃO GEMINI
# ======================================================
def gerar_insights_vendedores(dados):
    prompt = f"""
    Analise o concurso {dados['numero']} da Lotofácil com dezenas {dados['listaDezenas']}.
    Crie uma análise 'vendedora' para meu app. 
    Destaque uma curiosidade estatística e sugira uma estratégia baseada em dezenas fixas.
    Retorne apenas o JSON com campos: 'titulo', 'analise', 'estrategia'.
    """
    try:
        response = model.generate_content(prompt)
        limpo = response.text.replace('```json', '').replace('```', '').strip()
        return json.loads(limpo)
    except:
        return {"analise": "Padrão de dezenas equilibrado para o próximo concurso."}

# ======================================================
# FLUXO PRINCIPAL
# ======================================================
def main():
    print(f"🚀 Iniciando atualização tripla - {datetime.now()}")
    
    dados_caixa = capturar_dados_completos()
    
    if dados_caixa:
        print(f"✅ Concurso {dados_caixa['numero']} capturado.")
        
        print("🤖 Gerando inteligência...")
        insights = gerar_insights_vendedores(dados_caixa)
        
        print("💾 Gravando Detalhado, Compacto e IA...")
        salvar_arquivos_json(dados_caixa, insights)
        
        print("🎉 Tudo pronto! Arquivos prontos para o commit no Git.")
    else:
        print("❌ Falha crítica: Os arquivos não foram atualizados.")

if __name__ == "__main__":
    main()
