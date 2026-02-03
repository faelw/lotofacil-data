import requests
import json
import os
import time
import urllib3

# Desabilita avisos de SSL (comuns em sites do governo)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- CONFIGURAÇÕES ---
FILE_DB = "api/lotofacil.json"          # Histórico Completo
FILE_COMPACT = "api/lotofacil_compacto.json"  # Apenas números (para estatística rápida)
FILE_LATEST = "api/lotofacil_detalhada.json"  # Últimos jogos com RATEIO completo

# --- FONTES ---
URL_API_COMUNITARIA = "https://loteriascaixa-api.herokuapp.com/api/lotofacil"
URL_CAIXA_OFICIAL = "https://servicebus2.caixa.gov.br/portaldeloterias/api/lotofacil"

HEADERS_CAIXA = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/plain, */*',
    'Referer': 'https://loterias.caixa.gov.br/',
    'Origin': 'https://loterias.caixa.gov.br'
}

# --- FUNÇÃO AUXILIAR: PADRONIZAÇÃO DE DADOS ---
def padronizar_jogo(dados_brutos, fonte="oficial"):
    """
    Converte o JSON bagunçado das APIs em um formato limpo e único com RATEIO.
    """
    try:
        # Extração básica
        concurso = int(dados_brutos.get('concurso', dados_brutos.get('numero')))
        data = dados_brutos.get('data', dados_brutos.get('dataApuracao'))
        
        # Dezenas (Trata lista de string ou inteiros)
        raw_dezenas = dados_brutos.get('dezenas', dados_brutos.get('listaDezenas', []))
        dezenas = sorted([int(d) for d in raw_dezenas])

        # --- EXTRAÇÃO DO RATEIO (NOVIDADE) ---
        rateio_processado = []
        lista_rateio = dados_brutos.get('listaRateioPremio', dados_brutos.get('premiacoes', []))
        
        # O padrão da Caixa geralmente traz 5 faixas para Lotofácil (15, 14, 13, 12, 11 acertos)
        if lista_rateio:
            for item in lista_rateio:
                faixa = item.get('faixa') or item.get('descricaoFaixa') # As vezes muda o nome
                # Tenta converter para inteiro (15 acertos)
                if isinstance(faixa, str):
                    if "15" in faixa: faixa = 15
                    elif "14" in faixa: faixa = 14
                    elif "13" in faixa: faixa = 13
                    elif "12" in faixa: faixa = 12
                    elif "11" in faixa: faixa = 11
                
                rateio_processado.append({
                    "acertos": faixa,
                    "ganhadores": item.get('numeroDeGanhadores', 0),
                    "premio": item.get('valorPremio', 0.0)
                })
        
        # Dados de Acumulação
        acumulou = dados_brutos.get('acumulado', False)
        valor_acumulado = dados_brutos.get('valorAcumuladoProximoConcurso', 0.0)
        
        return {
            "concurso": concurso,
            "data": data,
            "dezenas": dezenas,
            "acumulou": acumulou,
            "valor_acumulado": valor_acumulado,
            "rateio": rateio_processado
        }
    except Exception as e:
        print(f"⚠️ Erro ao padronizar concurso {dados_brutos.get('numero')}: {e}")
        return None

# --- GERENCIAMENTO DE ARQUIVOS ---
def carregar_banco_local():
    if not os.path.exists(FILE_DB): return []
    try:
        with open(FILE_DB, "r", encoding="utf-8") as f:
            return json.load(f)
    except: return []

def salvar_arquivos(todos_jogos):
    os.makedirs("api", exist_ok=True)
    
    # Ordena por concurso
    todos_jogos.sort(key=lambda x: x['concurso'])

    # 1. Banco Completo (Backup)
    with open(FILE_DB, "w", encoding="utf-8") as f:
        json.dump(todos_jogos, f, separators=(',', ':')) # Minificado

    # 2. Compacto (Para análise estatística rápida no App)
    compacto = [{"c": j['concurso'], "d": j['dezenas']} for j in todos_jogos]
    with open(FILE_COMPACT, "w", encoding="utf-8") as f:
        json.dump(compacto, f, separators=(',', ':'))

    # 3. Detalhada (Últimos 10 com RATEIO para a Home do App)
    # Invertemos para o mais recente ficar no topo
    detalhada = todos_jogos[-10:][::-1] 
    with open(FILE_LATEST, "w", encoding="utf-8") as f:
        json.dump(detalhada, f, indent=2, ensure_ascii=False)

    print(f"✅ Arquivos gerados! Último concurso: {todos_jogos[-1]['concurso']}")

# --- FONTES DE DADOS ---

def buscar_api_comunitaria():
    print("📡 Tentando API Comunitária...")
    try:
        r = requests.get(URL_API_COMUNITARIA, timeout=10)
        if r.status_code == 200:
            dados = r.json()
            limpos = []
            for j in dados:
                obj = padronizar_jogo(j, "comunitaria")
                if obj: limpos.append(obj)
            return limpos
    except Exception as e:
        print(f"⚠️ API Comunitária falhou: {e}")
    return None

def buscar_caixa_oficial(ultimo_concurso_local):
    print(f"🕵️ Verificando Caixa Oficial (Local: {ultimo_concurso_local})...")
    novos_jogos = []
    
    try:
        # 1. Pega o último jogo oficial
        r = requests.get(URL_CAIXA_OFICIAL, headers=HEADERS_CAIXA, verify=False, timeout=15)
        if r.status_code != 200: return None
        
        ultimo_real = r.json()
        num_ultimo = ultimo_real['numero']
        
        print(f"🎯 Caixa: {num_ultimo} | Local: {ultimo_concurso_local}")
        
        if num_ultimo <= ultimo_concurso_local:
            print("✅ Tudo atualizado.")
            return []

        # 2. Baixa os faltantes
        for i in range(ultimo_concurso_local + 1, num_ultimo + 1):
            print(f"   ⬇️ Baixando {i}...")
            # Tenta pegar específico
            rj = requests.get(f"{URL_CAIXA_OFICIAL}/{i}", headers=HEADERS_CAIXA, verify=False)
            if rj.status_code == 200:
                obj = padronizar_jogo(rj.json(), "oficial")
                if obj: novos_jogos.append(obj)
                time.sleep(0.5)
            else:
                print(f"❌ Falha ao baixar {i}")
        
        return novos_jogos

    except Exception as e:
        print(f"⚠️ Erro no scraping da Caixa: {e}")
        return None

# --- MAIN ---
def main():
    banco_atual = carregar_banco_local()
    ultimo_concurso = max([j['concurso'] for j in banco_atual]) if banco_atual else 0
    
    dados_novos = None
    
    # Estratégia: Tenta API rápida primeiro se banco estiver vazio
    if ultimo_concurso == 0:
        dados_novos = buscar_api_comunitaria()
    
    # Se falhou ou já temos dados (queremos apenas o incremental), vai na oficial
    if not dados_novos:
        incremental = buscar_caixa_oficial(ultimo_concurso)
        if incremental:
            banco_atual.extend(incremental)
            dados_novos = banco_atual
        else:
            # Se não baixou nada novo, mas já tinha dados, mantemos o que tem
            dados_novos = banco_atual

    if dados_novos:
        # Remove duplicatas por segurança (baseado no numero do concurso)
        # Cria um dict para garantir unicidade
        dados_unicos = {j['concurso']: j for j in dados_novos}
        lista_final = list(dados_unicos.values())
        
        salvar_arquivos(lista_final)
    else:
        print("❌ Não foi possível atualizar os dados.")

if __name__ == "__main__":
    main()
