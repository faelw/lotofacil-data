import requests
import json
import os
import time
import urllib3

# Ignora avisos de SSL da Caixa
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- ARQUIVOS ---
FILE_DB = "api/lotofacil.json"
FILE_COMPACT = "api/lotofacil_compacto.json"
FILE_LATEST = "api/lotofacil_detalhada.json"

URL_CAIXA = "https://servicebus2.caixa.gov.br/portaldeloterias/api/lotofacil"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'application/json',
    'Origin': 'https://loterias.caixa.gov.br',
    'Referer': 'https://loterias.caixa.gov.br/'
}

def carregar_banco():
    if os.path.exists(FILE_DB):
        try:
            with open(FILE_DB, "r", encoding="utf-8") as f:
                return json.load(f)
        except: return []
    return []

def salvar_arquivos(jogos):
    # Ordena por concurso
    jogos.sort(key=lambda x: x['concurso'])
    
    os.makedirs("api", exist_ok=True)
    
    # 1. Banco Completo (Backup interno)
    with open(FILE_DB, "w", encoding="utf-8") as f:
        json.dump(jogos, f, separators=(',', ':'))

    # 2. Compacto (Apenas números para matemática leve)
    compacto = [{"c": j['concurso'], "d": [int(d) for d in j['dezenas']]} for j in jogos]
    with open(FILE_COMPACT, "w", encoding="utf-8") as f:
        json.dump(compacto, f, separators=(',', ':'))

    # 3. Detalhada (NO FORMATO EXATO DOS PRINTS)
    # Invertemos para o mais recente ficar no topo
    detalhada = jogos[-15:][::-1]
    
    with open(FILE_LATEST, "w", encoding="utf-8") as f:
        # indent=4 ou 2 deixa igual ao seu print
        json.dump(detalhada, f, indent=2, ensure_ascii=False)
        
    print(f"✅ Arquivos salvos no formato Legacy! Último: {jogos[-1]['concurso']}")

def formatar_dezena(num):
    """Converte 1 -> '01' (String)"""
    return str(num).zfill(2)

def parse_jogo_legacy(dados):
    """
    Mapeia os dados da Caixa para o formato EXATO das suas imagens.
    """
    try:
        concurso = int(dados.get('numero', dados.get('concurso', 0)))
        if concurso == 0: return None

        # Data
        data_apuracao = dados.get('dataApuracao', dados.get('data', ''))
        
        # Local
        local = f"{dados.get('localSorteio', '')} em {dados.get('nomeMunicipioUFSorteio', '')}"

        # Dezenas (Tratamento especial para Strings '01')
        raw_dezenas = dados.get('listaDezenas', dados.get('dezenas', []))
        # Dezenas ORDENADAS (campo 'dezenas')
        dezenas_ints = sorted([int(d) for d in raw_dezenas])
        dezenas_fmt = [formatar_dezena(d) for d in dezenas_ints]
        
        # Dezenas ORDEM SORTEIO (campo 'dezenasOrdemSorteio')
        # A API as vezes manda 'listaDezenasOrdemSorteio', se não tiver, usa a raw
        raw_ordem = dados.get('listaDezenasOrdemSorteio', raw_dezenas)
        dezenas_ordem_fmt = [formatar_dezena(d) for d in raw_ordem]

        # Premiações (Mapear listaRateioPremio -> premiacoes)
        premiacoes_fmt = []
        lista_rateio = dados.get('listaRateioPremio', dados.get('premiacoes', [])) or []
        
        for p in lista_rateio:
            faixa = p.get('faixa', p.get('descricaoFaixa', '')) # Tenta pegar numero da faixa
            descricao = p.get('descricaoFaixa', '')
            
            # Ajuste da Faixa (Se vier texto, tentar converter ou mapear)
            # No seu print, faixa 1 = 15 acertos, faixa 2 = 14, etc.
            faixa_int = 0
            if '15' in str(descricao): faixa_int = 1
            elif '14' in str(descricao): faixa_int = 2
            elif '13' in str(descricao): faixa_int = 3
            elif '12' in str(descricao): faixa_int = 4
            elif '11' in str(descricao): faixa_int = 5
            
            # Se a API já mandar o numero da faixa, usa ele
            if isinstance(faixa, int): faixa_int = faixa

            premiacoes_fmt.append({
                "descricao": descricao,
                "faixa": faixa_int,
                "ganhadores": int(p.get('numeroDeGanhadores', 0)),
                "valorPremio": float(p.get('valorPremio', 0.0))
            })
        
        # Garante a ordem das faixas (1 a 5)
        premiacoes_fmt.sort(key=lambda x: x['faixa'])

        # MONTAGEM DO JSON FINAL (Estrutura idêntica ao Print)
        obj_final = {
            "loteria": "lotofacil",
            "concurso": concurso,
            "data": data_apuracao,
            "local": local.strip(),
            "concursoEspecial": bool(dados.get('indicadorConcursoEspecial', False) == 1),
            "dezenasOrdemSorteio": dezenas_ordem_fmt,
            "dezenas": dezenas_fmt,
            "trevos": [], # Lotofácil não tem trevos, mas o JSON pede array vazio
            "timeCoracao": None,
            "mesSorte": None,
            "premiacoes": premiacoes_fmt,
            "estadosPremiados": [], # Simplificado para vazio para não quebrar
            "observacao": dados.get('observacao', ""),
            "acumulou": bool(dados.get('acumulado', False)),
            "proximoConcurso": int(dados.get('numeroConcursoProximo', 0)),
            "dataProximoConcurso": dados.get('dataProximoConcurso', ""),
            "localGanhadores": [], # Simplificado
            "valorArrecadado": float(dados.get('valorArrecadado', 0.0)),
            "valorAcumuladoConcurso_0_5": float(dados.get('valorAcumuladoConcurso_0_5', 0.0)),
            "valorAcumuladoConcursoEspecial": float(dados.get('valorAcumuladoConcursoEspecial', 0.0)),
            "valorAcumuladoProximoConcurso": float(dados.get('valorAcumuladoProximoConcurso', 0.0)),
            "valorEstimadoProximoConcurso": float(dados.get('valorEstimadoProximoConcurso', 0.0))
        }

        return obj_final

    except Exception as e:
        print(f"Erro parse Legacy {dados.get('numero')}: {e}") 
        return None

def buscar_jogo_caixa(id_concurso):
    try:
        url = f"{URL_CAIXA}/{id_concurso}"
        r = requests.get(url, headers=HEADERS, verify=False, timeout=5)
        if r.status_code == 200:
            return parse_jogo_legacy(r.json())
    except: pass
    return None

def atualizar():
    banco = carregar_banco()
    
    ultimo_id_local = 0
    if banco:
        ultimo_id_local = max(int(j['concurso']) for j in banco)
    
    print(f"📊 Último local: {ultimo_id_local}")

    # 1. Busca último na Caixa
    try:
        r = requests.get(URL_CAIXA, headers=HEADERS, verify=False, timeout=10)
        dados_ultimo = r.json()
        ultimo_real = int(dados_ultimo['numero'])
    except:
        print("❌ Erro conexão Caixa")
        return

    alteracoes = False

    # 2. Baixa Novos
    if ultimo_real > ultimo_id_local:
        for i in range(ultimo_id_local + 1, ultimo_real + 1):
            print(f"⬇️ Baixando {i}...")
            novo = buscar_jogo_caixa(i)
            if novo:
                banco.append(novo)
                alteracoes = True
            time.sleep(0.5)

    # 3. REPARAÇÃO / ATUALIZAÇÃO FORÇADA
    # Verifica os últimos 3 jogos. Se 'premiacoes' estiver vazio, baixa de novo.
    banco.sort(key=lambda x: x['concurso'])
    
    for i in range(len(banco) - 1, max(-1, len(banco) - 4), -1):
        jogo = banco[i]
        
        # Validação baseada no novo formato 'premiacoes'
        tem_premios = len(jogo.get('premiacoes', [])) > 0
        dados_suspeitos = False
        
        if tem_premios:
             # Verifica se premio principal é 0 mas tem ganhadores
             try:
                p15 = next((p for p in jogo['premiacoes'] if p['faixa'] == 1), None)
                if p15 and p15['valorPremio'] == 0.0 and p15['ganhadores'] > 0: 
                    dados_suspeitos = True
             except: pass
        
        if not tem_premios or dados_suspeitos:
            print(f"♻️ Reparando {jogo['concurso']} (Legacy Format)...")
            versao_nova = buscar_jogo_caixa(jogo['concurso'])
            
            if versao_nova and len(versao_nova.get('premiacoes', [])) > 0:
                banco[i] = versao_nova
                alteracoes = True
                print("   ✅ Reparado!")
            time.sleep(1)

    # Salva SEMPRE para garantir que a formatação antiga seja convertida para a nova se rodar pela primeira vez
    salvar_arquivos(banco) 

if __name__ == "__main__":
    atualizar()
