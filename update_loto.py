import requests
import json
import os
import time
import urllib3

# Ignora erros de SSL da Caixa
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- CONFIGURAÇÕES ---
FILE_DB = "api/lotofacil.json"
FILE_COMPACT = "api/lotofacil_compacto.json"
FILE_LATEST = "api/lotofacil_detalhada.json"

URL_API_COMUNITARIA = "https://loteriascaixa-api.herokuapp.com/api/lotofacil"
URL_CAIXA_OFICIAL = "https://servicebus2.caixa.gov.br/portaldeloterias/api/lotofacil"

HEADERS_CAIXA = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/plain, */*',
    'Referer': 'https://loterias.caixa.gov.br/',
    'Origin': 'https://loterias.caixa.gov.br'
}

# --- PROCESSADOR DE DADOS ---
def padronizar_jogo(dados_brutos):
    """Extrai dados com segurança, focando no RATEIO."""
    try:
        # Identificação
        concurso = int(dados_brutos.get('concurso', dados_brutos.get('numero')))
        data = dados_brutos.get('data', dados_brutos.get('dataApuracao'))
        
        # Dezenas
        raw_dezenas = dados_brutos.get('dezenas', dados_brutos.get('listaDezenas', []))
        if not raw_dezenas: return None
        dezenas = sorted([int(d) for d in raw_dezenas])

        # --- RATEIO E PREMIAÇÃO (A MÁGICA ACONTECE AQUI) ---
        rateio_final = []
        lista_rateio = dados_brutos.get('listaRateioPremio', dados_brutos.get('premiacoes', []))
        
        if lista_rateio:
            for item in lista_rateio:
                # Tenta pegar a faixa de acertos (ex: "15 acertos")
                descricao = item.get('descricaoFaixa', str(item.get('faixa', '')))
                acertos = 0
                
                if '15' in descricao: acertos = 15
                elif '14' in descricao: acertos = 14
                elif '13' in descricao: acertos = 13
                elif '12' in descricao: acertos = 12
                elif '11' in descricao: acertos = 11
                
                if acertos > 0:
                    rateio_final.append({
                        "acertos": acertos,
                        "ganhadores": item.get('numeroDeGanhadores', 0),
                        "premio": item.get('valorPremio', 0.0)
                    })
        
        # Garante ordem decrescente de prêmio (15 -> 11)
        rateio_final.sort(key=lambda x: x['acertos'], reverse=True)

        return {
            "concurso": concurso,
            "data": data,
            "dezenas": dezenas,
            "acumulou": dados_brutos.get('acumulado', False),
            "valor_acumulado": dados_brutos.get('valorAcumuladoProximoConcurso', 0.0),
            "rateio": rateio_final
        }
    except Exception as e:
        # print(f"Erro parse concurso {dados_brutos.get('numero')}: {e}")
        return None

# --- GERENCIAMENTO ---
def carregar_banco():
    if os.path.exists(FILE_DB):
        with open(FILE_DB, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def salvar(todos):
    todos.sort(key=lambda x: x['concurso'])
    
    os.makedirs("api", exist_ok=True)
    
    # 1. Banco Completo
    with open(FILE_DB, "w", encoding="utf-8") as f:
        json.dump(todos, f, separators=(',', ':'))
        
    # 2. Compacto
    compacto = [{"c": j['concurso'], "d": j['dezenas']} for j in todos]
    with open(FILE_COMPACT, "w", encoding="utf-8") as f:
        json.dump(compacto, f, separators=(',', ':'))
        
    # 3. Detalhada (Invertida para App)
    detalhada = todos[-15:][::-1] # Pega os 15 últimos
    with open(FILE_LATEST, "w", encoding="utf-8") as f:
        json.dump(detalhada, f, indent=2, ensure_ascii=False)
        
    print(f"💾 Arquivos salvos! Último: {todos[-1]['concurso']}")

# --- EXTRACTORS ---
def buscar_historico_basico():
    """Baixa histórico rápido (pode vir sem rateio)."""
    print("🌍 Buscando histórico básico...")
    try:
        r = requests.get(URL_API_COMUNITARIA, timeout=10)
        if r.status_code == 200:
            return [padronizar_jogo(j) for j in r.json() if padronizar_jogo(j)]
    except: pass
    return []

def enriquecer_ultimos_jogos(lista_jogos, qtd=10):
    """
    CRÍTICO: Vai na Caixa OFICIAL e baixa os detalhes dos últimos X jogos
    para garantir que o RATEIO esteja atualizado.
    """
    if not lista_jogos: return []
    
    # Pega os IDs dos últimos 'qtd' jogos
    ultimos_ids = [j['concurso'] for j in lista_jogos[-qtd:]]
    print(f"💎 Enriquecendo detalhes (Rateio) dos últimos {qtd} jogos...")
    
    mapa_jogos = {j['concurso']: j for j in lista_jogos}
    
    for concurso_id in ultimos_ids:
        try:
            url = f"{URL_CAIXA_OFICIAL}/{concurso_id}"
            r = requests.get(url, headers=HEADERS_CAIXA, verify=False, timeout=5)
            
            if r.status_code == 200:
                dados_ricos = r.json()
                jogo_processado = padronizar_jogo(dados_ricos)
                
                # Se achou rateio, substitui o jogo antigo pelo novo rico
                if jogo_processado and jogo_processado['rateio']:
                    mapa_jogos[concurso_id] = jogo_processado
                    print(f"   ✅ Concurso {concurso_id}: Rateio Atualizado!")
                else:
                    print(f"   ⚠️ Concurso {concurso_id}: Caixa sem rateio ainda.")
            time.sleep(0.5) # Respeito à API
        except Exception as e:
            print(f"   ❌ Falha ao enriquecer {concurso_id}: {e}")
            
    return list(mapa_jogos.values())

def buscar_novos_caixa(ultimo_id_local):
    """Busca jogos que ainda não existem no banco."""
    print("🕵️ Verificando novos jogos na Caixa...")
    novos = []
    try:
        # Pega ultimo oficial
        r = requests.get(URL_CAIXA_OFICIAL, headers=HEADERS_CAIXA, verify=False, timeout=10)
        if r.status_code != 200: return []
        
        ultimo_real_id = r.json()['numero']
        if ultimo_real_id <= ultimo_id_local: return []
        
        # Baixa os faltantes
        for i in range(ultimo_id_local + 1, ultimo_real_id + 1):
            print(f"   ⬇️ Baixando novo: {i}")
            rj = requests.get(f"{URL_CAIXA_OFICIAL}/{i}", headers=HEADERS_CAIXA, verify=False)
            if rj.status_code == 200:
                obj = padronizar_jogo(rj.json())
                if obj: novos.append(obj)
            time.sleep(1)
            
    except Exception as e:
        print(f"Erro busca novos: {e}")
        
    return novos

# --- MAIN ---
def main():
    banco = carregar_banco()
    
    # 1. Se banco vazio, popula com API rapida
    if not banco:
        banco = buscar_historico_basico()
    
    # 2. Descobre qual o ultimo que temos
    ultimo_id = max([j['concurso'] for j in banco]) if banco else 0
    
    # 3. Busca novos incrementalmente
    novos = buscar_novos_caixa(ultimo_id)
    if novos:
        banco.extend(novos)
        # Reordena
        banco.sort(key=lambda x: x['concurso'])
    
    # 4. PASSO DE OURO: Força atualização dos últimos 10 para pegar o rateio
    # Isso corrige jogos que foram salvos antes do rateio sair
    banco_final = enriquecer_ultimos_jogos(banco, qtd=10)
    
    salvar(banco_final)

if __name__ == "__main__":
    main()
