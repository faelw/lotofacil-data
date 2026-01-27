import requests
import json
import os
import statistics
from collections import Counter

# --- CONFIGURAÇÕES ---
API_URL = "https://loteriascaixa-api.herokuapp.com/api/lotofacil"
API_KEY = os.environ.get("MISTRAL_API_KEY") 
API_ENDPOINT = "https://api.mistral.ai/v1/chat/completions"
MODELO_IA = "mistral-small-latest"

# ==============================================================================
# 🧠 CÁLCULOS MATEMÁTICOS DE ELITE (ESTATÍSTICA PURA)
# ==============================================================================

def calcular_fundamentos_lotofacil(ultimo_jogo, penultimo_jogo):
    """
    Analisa os 4 pilares fundamentais da Lotofácil.
    Retorna um dicionário com os dados e alertas de desvio.
    """
    dezenas = [int(d) for d in ultimo_jogo['dezenas']]
    dezenas_ant = [int(d) for d in penultimo_jogo['dezenas']]
    
    # 1. PAR/ÍMPAR (Padrão: 8/7, 7/8, 9/6, 6/9)
    pares = len([d for d in dezenas if d % 2 == 0])
    impares = 15 - pares
    status_pi = "Normal"
    if pares > 10 or impares > 10: status_pi = "🚨 Desequilíbrio Crítico"
    
    # 2. SOMA (Padrão: 180 a 210)
    soma = sum(dezenas)
    status_soma = "Normal"
    if soma < 165: status_soma = "❄️ Soma Muito Baixa (Atípico)"
    if soma > 225: status_soma = "🔥 Soma Muito Alta (Atípico)"
    
    # 3. PRIMOS (Padrão: 4 a 6 primos)
    primos_lista = [2, 3, 5, 7, 11, 13, 17, 19, 23]
    qtd_primos = len([d for d in dezenas if d in primos_lista])
    status_primos = "Normal"
    if qtd_primos <= 2 or qtd_primos >= 8: status_primos = "⚠️ Anomalia de Primos"
    
    # 4. REPETIDAS (Padrão: 8 a 10)
    repetidas = len(set(dezenas).intersection(set(dezenas_ant)))
    status_rep = "Normal"
    if repetidas <= 6: status_rep = "📉 Poucas Repetidas (Renovação)"
    if repetidas >= 12: status_rep = "📈 Muitas Repetidas (Estagnação)"

    return {
        "pares": pares,
        "impares": impares,
        "soma": soma,
        "primos": qtd_primos,
        "repetidas": repetidas,
        "alertas": [s for s in [status_pi, status_soma, status_primos, status_rep] if "Normal" not in s]
    }

def calcular_z_score(todos_jogos):
    """Detecta anomalias estatísticas com base nos últimos 30 concursos."""
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
    """Descobre números que faltam para fechar o ciclo completo."""
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
            if n not in [int(d) for d in jogo['dezenas']]:
                count += 1
            else:
                break
        atrasos[n] = count
    return atrasos

def preparar_dados_ia(todos_jogos):
    ultimo = todos_jogos[-1]
    penultimo = todos_jogos[-2]
    
    fundamentos = calcular_fundamentos_lotofacil(ultimo, penultimo)
    z_scores = calcular_z_score(todos_jogos)
    ciclo = analisar_ciclo(todos_jogos)
    atrasos = analisar_atraso(todos_jogos)
    
    # Filtra oportunidades de ouro para a IA focar
    z_score_anormal = []
    for n, z in z_scores.items():
        if z > 1.9: z_score_anormal.append(f"Dezena {n} (Saturada: Z-Score {z})")
        if z < -1.9: z_score_anormal.append(f"Dezena {n} (Atraso Crítico: Z-Score {z})")
    
    return {
        "concurso": ultimo['concurso'],
        "fundamentos": fundamentos,
        "z_scores_extremos": z_score_anormal,
        "falta_ciclo": ciclo,
        "top_atrasos": [k for k,v in sorted(atrasos.items(), key=lambda x: x[1], reverse=True)[:5]]
    }

# ==============================================================================
# 🔮 O ORÁCULO (Prompt Engenheirado com Validação Estatística)
# ==============================================================================

def gerar_insights(dados):
    print("\n--- Gerando Insights Validadores ---")
    
    if not API_KEY:
        print("ERRO: API Key não encontrada.")
        return

    prompt_sistema = """
    Você é o 'Oráculo da Loto', um cientista de dados especializado na Lotofácil.
    
    SUA MISSÃO: Analisar a saúde estatística do jogo e gerar cards para um App Gamificado.
    
    REGRAS DE OURO DA LOTOFÁCIL (Use para validar seus insights):
    1. Soma ideal: 180 a 210. Fora disso é atípico.
    2. Primos ideal: 4 a 6.
    3. Par/Ímpar ideal: Equilíbrio (8/7 ou 7/8).
    
    REGRAS DE RARIDADE DO APP (Obrigatório usar as palavras-chave):
    
    🟡 LENDÁRIA (Use: "Certeza", "Padrão Ouro", "Foco Total"):
       - Use APENAS para Z-Scores extremos (>1.9 ou <-1.9) ou Fechamento de Ciclo.
       - Ex: "Padrão Ouro detectado: A dezena X atingiu o limite estatístico."
    
    🔵 RARA (Use: "Atenção", "Ciclo", "Importante"):
       - Use para alertas de fundamentos (Soma alta, muitos pares) ou Atrasos Top 5.
       - Ex: "Atenção: A soma das dezenas fugiu da curva de Gauss."
    
    ⚪ COMUM:
       - Observações gerais sobre o equilíbrio do jogo.

    Gere 30 insights. O texto deve ser curto, técnico e persuasivo.
    """

    prompt_usuario = f"""
    RELATÓRIO DE SAÚDE DO CONCURSO {dados['concurso']}:
    
    📊 FUNDAMENTOS (Onde houver alerta, crie um card RARO):
    - Soma: {dados['fundamentos']['soma']}
    - Pares/Ímpares: {dados['fundamentos']['pares']}/{dados['fundamentos']['impares']}
    - Primos: {dados['fundamentos']['primos']}
    - Repetidas do anterior: {dados['fundamentos']['repetidas']}
    - ALERTAS ATIVOS: {dados['fundamentos']['alertas']}
    
    🏆 ANOMALIAS ESTATÍSTICAS (Crie cards LENDÁRIOS aqui):
    {dados['z_scores_extremos']}
    
    💎 CICLO (Se houver números, é prioridade):
    Faltam sair: {dados['falta_ciclo']}
    
    📉 ATRASOS (Top 5):
    {dados['top_atrasos']}
    
    FORMATO JSON OBRIGATÓRIO:
    {{
        "analise_referencia": "{dados['concurso']}",
        "insights": [
            {{ "titulo": "TÍTULO CRIATIVO", "texto": "TEXTO COM PALAVRA CHAVE" }},
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
        "temperature": 0.6,
        "response_format": {"type": "json_object"}
    }

    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}

    try:
        response = requests.post(API_ENDPOINT, json=payload, headers=headers)
        if response.status_code == 200:
            conteudo = response.json()['choices'][0]['message']['content']
            
            # Validação extra de JSON antes de salvar
            try:
                json.loads(conteudo)
                os.makedirs("api", exist_ok=True)
                with open("api/insights_ia.json", "w", encoding="utf-8") as f:
                    f.write(conteudo)
                print("SUCESSO! Insights estatísticos gerados.")
            except json.JSONDecodeError:
                print("ERRO: IA gerou JSON inválido.")
        else:
            print(f"ERRO IA: {response.text}")
    except Exception as e:
        print(f"ERRO: {e}")

# ==============================================================================
# 🚀 EXECUTOR
# ==============================================================================

def atualizar_dados():
    print("Iniciando Análise Complexa...")
    os.makedirs("api", exist_ok=True)
    try:
        r = requests.get(API_URL)
        if r.status_code != 200: return
        jogos = r.json()
        jogos.sort(key=lambda x: x['concurso'])
        
        # Arquivos básicos
        compacto = [{"c": j['concurso'], "d": [int(d) for d in j['dezenas']]} for j in jogos]
        with open("api/lotofacil_compacto.json", "w", encoding="utf-8") as f:
            json.dump(compacto, f, separators=(',', ':'))
            
        with open("api/lotofacil_detalhada.json", "w", encoding="utf-8") as f:
            json.dump(jogos[-10:][::-1], f, indent=2, ensure_ascii=False)

        # Gera IA com dados robustos
        dados = preparar_dados_ia(jogos)
        gerar_insights(dados)
        
    except Exception as e:
        print(f"Erro fatal: {e}")

if __name__ == "__main__":
    atualizar_dados()
