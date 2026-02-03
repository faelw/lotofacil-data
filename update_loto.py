import requests
import json
import os
import time
import urllib3
from datetime import datetime

# Desabilita avisos de SSL para o site da Caixa (governo muitas vezes tem certs problemáticos)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- CONFIGURAÇÕES ---
FILE_DB = "api/lotofacil.json"          # Banco de dados completo
FILE_COMPACT = "api/lotofacil_compacto.json"  # Para o App (Leve)
FILE_LATEST = "api/lotofacil_detalhada.json"  # Últimos 10 (Detalhado)

# --- FONTES DE DADOS (Redundância) ---
URL_API_COMUNITARIA = "https://loteriascaixa-api.herokuapp.com/api/lotofacil"
URL_CAIXA_OFICIAL = "https://servicebus2.caixa.gov.br/portaldeloterias/api/lotofacil"

# Headers para "enganar" o servidor da Caixa e parecer um Chrome
HEADERS_CAIXA = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/plain, */*',
    'Referer': 'https://loterias.caixa.gov.br/',
    'Origin': 'https://loterias.caixa.gov.br'
}

def carregar_banco_local():
    """Lê o arquivo JSON existente para saber onde paramos."""
    if not os.path.exists(FILE_DB):
        return []
    try:
        with open(FILE_DB, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []

def salvar_arquivos(todos_jogos):
    """Gera os arquivos finais para o App consumir."""
    os.makedirs("api", exist_ok=True)
    
    # 1. Banco Completo (Backup)
    todos_jogos.sort(key=lambda x: x['concurso']) # Garante ordem
    with open(FILE_DB, "w", encoding="utf-8") as f:
        json.dump(todos_jogos, f, indent=None, separators=(',', ':'))
    
    # 2. Compacto (Para o App carregar rápido)
    # Formato minificado: [{"c": 1, "d": [1,2,3...]}]
    compacto = [
        {
            "c": j['concurso'],
            "d": [int(d) for d in j['dezenas']]
        } 
        for j in todos_jogos
    ]
    with open(FILE_COMPACT, "w", encoding="utf-8") as f:
        json.dump(compacto, f, separators=(',', ':'))

    # 3. Detalhada (Últimos 10 para visualização rápida)
    detalhada = todos_jogos[-10:][::-1] # Inverte para o mais recente primeiro
    with open(FILE_LATEST, "w", encoding="utf-8") as f:
        json.dump(detalhada, f, indent=2)

    print(f"✅ Sucesso! Total de jogos: {len(todos_jogos)}. Último: {todos_jogos[-1]['concurso']}")

# --- ESTRATÉGIA 1: DOWNLOAD EM MASSA (API COMUNITÁRIA) ---
def buscar_api_comunitaria():
    print("📡 Tentando Fonte 1 (API Comunitária)...")
    try:
        r = requests.get(URL_API_COMUNITARIA, timeout=10)
        if r.status_code == 200:
            dados = r.json()
            # Padronização simples
            limpos = []
            for j in dados:
                limpos.append({
                    "concurso": int(j['concurso']),
                    "data": j.get('data', ''),
                    "dezenas": [int(d) for d in j['dezenas']]
                })
            return limpos
    except Exception as e:
        print(f"⚠️ Falha na Fonte 1: {e}")
    return None

# --- ESTRATÉGIA 2: SCRAPING OFICIAL (INCREMENTAL) ---
def buscar_caixa_oficial(ultimo_concurso_local):
    print(f"🕵️ Tentando Fonte 2 (Caixa Oficial) a partir do {ultimo_concurso_local}...")
    
    novos_jogos = []
    
    # Primeiro, descobre qual é o último jogo REAL na Caixa
    try:
        r = requests.get(f"{URL_CAIXA_OFICIAL}", headers=HEADERS_CAIXA, verify=False, timeout=10)
        if r.status_code != 200: return None
        
        ultimo_real = r.json()
        num_ultimo = ultimo_real['numero']
        
        print(f"🎯 Último concurso na Caixa: {num_ultimo}. Local: {ultimo_concurso_local}")
        
        if num_ultimo <= ultimo_concurso_local:
            print("✅ Dados já estão atualizados.")
            return [] # Nada a fazer

        # Loop para baixar os faltantes (do local+1 até o último)
        # Baixamos um por um para garantir integridade via endpoint específico
        for i in range(ultimo_concurso_local + 1, num_ultimo + 1):
            print(f"   ⬇️ Baixando concurso {i}...")
            url_jogo = f"{URL_CAIXA_OFICIAL}/{i}"
            rj = requests.get(url_jogo, headers=HEADERS_CAIXA, verify=False)
            
            if rj.status_code == 200:
                j = rj.json()
                # Normaliza o formato da Caixa para o nosso formato
                dezenas_limpas = [int(d) for d in j['listaDezenas']]
                dezenas_limpas.sort()
                
                novos_jogos.append({
                    "concurso": j['numero'],
                    "data": j['dataApuracao'],
                    "dezenas": dezenas_limpas
                })
                time.sleep(0.5) # Respeito ao servidor para não tomar block
            else:
                print(f"❌ Erro ao baixar jogo {i}")
        
        return novos_jogos

    except Exception as e:
        print(f"⚠️ Falha na Fonte 2: {e}")
        return None

# --- ORQUESTADOR ---
def main():
    banco_atual = carregar_banco_local()
    
    # Define qual é o último concurso que temos
    ultimo_concurso = 0
    if banco_atual:
        ultimo_concurso = max(j['concurso'] for j in banco_atual)

    dados_atualizados = None

    # TENTATIVA 1: API Comunitária (Geralmente traz tudo de uma vez)
    # Se o banco local estiver vazio ou muito defasado, prioriza essa
    dados_api = buscar_api_comunitaria()
    
    if dados_api and len(dados_api) > len(banco_atual):
        print("🎉 Fonte 1 funcionou e trouxe dados novos.")
        dados_atualizados = dados_api
    else:
        # TENTATIVA 2: Fonte Oficial (Scraping Incremental)
        # Usada se a Fonte 1 falhar ou se quisermos apenas pegar o do dia (mais confiável)
        novos = buscar_caixa_oficial(ultimo_concurso)
        
        if novos is not None:
            # Junta o antigo com o novo
            if novos: # Se trouxe lista vazia, é pq já tava atualizado
                banco_atual.extend(novos)
                dados_atualizados = banco_atual
            else:
                # Já estava atualizado, apenas re-salva para garantir integridade
                dados_atualizados = banco_atual

    # SALVAMENTO FINAL
    if dados_atualizados:
        salvar_arquivos(dados_atualizados)
    else:
        print("❌ Nenhuma fonte funcionou ou não há internet.")

if __name__ == "__main__":
    main()
