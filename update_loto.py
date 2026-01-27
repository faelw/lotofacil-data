import requests
import json
import os
from collections import Counter

# --- CONFIGURAÇÕES ---
API_URL = "https://loteriascaixa-api.herokuapp.com/api/lotofacil"
MISTRAL_KEY = os.environ.get("MISTRAL_API_KEY")
MISTRAL_ENDPOINT = "https://api.mistral.ai/v1/chat/completions"

# ==============================================================================
# 🧠 CÉREBRO MATEMÁTICO (Python Data Science)
# ==============================================================================

def analisar_ciclo(todos_jogos):
    """Descobre quais números faltam para sair desde que o ciclo abriu."""
    todos_numeros = set(range(1, 26))
    numeros_saidos_no_ciclo = set()
    
    # Percorre de trás para frente
    for jogo in reversed(todos_jogos):
        dezenas = {int(d) for d in jogo['dezenas']}
        numeros_saidos_no_ciclo.update(dezenas)
        
        if len(numeros_saidos_no_ciclo) == 25:
            # O ciclo fechou neste jogo aqui. O próximo começou um novo.
            # Então reiniciamos a contagem a partir do jogo seguinte a este.
            numeros_saidos_no_ciclo = set() 
            # (Na prática simplificada: pegamos o que falta sair desde o último fechamento)
            # Para simplificar a lógica deste script: vamos apenas ver o que falta sair 
            # baseados numa contagem progressiva simples dos últimos jogos até completar 25.
            break
            
    # Recalculando ciclo de forma robusta:
    # Pega os últimos jogos e vê quais numeros faltam para completar 25
    acumulado = set()
    jogos_no_ciclo = 0
    for jogo in reversed(todos_jogos):
        dezenas = {int(d) for d in jogo['dezenas']}
        acumulado.update(dezenas)
        jogos_no_ciclo += 1
        if len(acumulado) == 25:
            # Ciclo fechou aqui. 
            # O que importa são os números que AINDA NÃO SAÍRAM depois desse fechamento.
            # Como essa lógica é complexa, vamos usar a abordagem de "Números que não saem há X jogos"
            break
    
    # Abordagem de Ciclo Aberto Simplificada e Eficaz:
    # Quais números não saíram nos últimos X jogos?
    faltam_sair = list(todos_numeros - acumulado) if len(acumulado) < 25 else []
    return faltam_sair

def calcular_atrasos(todos_jogos):
    """Calcula há quantos jogos cada dezena não sai."""
    atrasos = {n: 0 for n in range(1, 26)}
    
    # Percorre do mais recente para trás
    for num in range(1, 26):
        count = 0
        for jogo in reversed(todos_jogos):
            if num not in [int(d) for d in jogo['dezenas']]:
                count += 1
            else:
                break # Encontrou o número, para de contar
        atrasos[num] = count
    return atrasos

def detectar_momentum(todos_jogos):
    """Compara curto prazo (10 jogos) vs médio prazo (30 jogos)."""
    # Frequencia últimos 10
    ultimos_10 = [int(d) for j in todos_jogos[-10:] for d in j['dezenas']]
    freq_10 = Counter(ultimos_10)
    
    # Frequencia últimos 30
    ultimos_30 = [int(d) for j in todos_jogos[-30:] for d in j['dezenas']]
    freq_30 = Counter(ultimos_30)
    
    tendencias = {}
    for n in range(1, 26):
        media_curta = freq_10.get(n, 0) / 10 # Ex: 0.6 (60%)
        media_longa = freq_30.get(n, 0) / 30 # Ex: 0.5 (50%)
        
        diff = media_curta - media_longa
        
        if diff >= 0.15:
            tendencias[n] = "🔥 Forte Alta"
        elif diff >= 0.05:
            tendencias[n] = "📈 Subindo"
        elif diff <= -0.15:
            tendencias[n] = "❄️ Queda Livre"
        elif diff <= -0.05:
            tendencias[n] = "📉 Caindo"
        else:
            tendencias[n] = "⚖️ Estável"
            
    return tendencias

def preparar_payload_ia(todos_jogos):
    ultimo_jogo = todos_jogos[-1]
    dezenas_ultimo = [int(d) for d in ultimo_jogo['dezenas']]
    
    # 1. Dados Básicos
    soma = sum(dezenas_ultimo)
    pares = len([d for d in dezenas_ultimo if d % 2 == 0])
    
    # 2. Dados Avançados
    atrasos = calcular_atrasos(todos_jogos)
    momentum = detectar_momentum(todos_jogos)
    
    # Monta tabela analítica para a IA
    tabela_analitica = []
    for n in range(1, 26):
        status_atraso = f"Atrasado há {atrasos[n]} jogos" if atrasos[n] > 0 else "Saiu no último"
        tabela_analitica.append(f"Dezena {n:02d}: {status_atraso} | Tendência: {momentum[n]}")
        
    # Filtros de Destaque para o Prompt
    top_atrasadas = [k for k, v in sorted(atrasos.items(), key=lambda item: item[1], reverse=True)[:5]]
    em_alta = [k for k, v in momentum.items() if "Alta" in v or "Subindo" in v]
    
    return {
        "concurso": ultimo_jogo['concurso'],
        "resultado": dezenas_ultimo,
        "resumo_matematico": {
            "soma": soma,
            "pares": pares,
            "top_5_atrasadas": top_atrasadas,
            "lista_em_alta": em_alta
        },
        "detalhamento_tecnico": tabela_analitica # A IA vai ler linha por linha
    }

# ==============================================================================
# 🤖 CONSULTOR IA (Mistral)
# ==============================================================================

def gerar_insights_mistral(dados_completos):
    print("\n--- Enviando Análise Robusta para a IA ---")
    
    if not MISTRAL_KEY:
        print("ERRO: Chave MISTRAL_API_KEY não encontrada.")
        return

    prompt_sistema = """
    Você é um cientista de dados especializado em loterias.
    Você recebe uma análise técnica pré-processada (Atrasos, Tendências de Alta/Baixa e Soma).
    
    SUA MISSÃO: Cruzar esses dados para encontrar "Oportunidades de Ouro".
    - Se uma dezena está em "Forte Alta", ela é um Hot Pick.
    - Se uma dezena está muito atrasada (mais de 4 jogos), ela é um alerta de retorno.
    - Use EMOJIS.
    - Seja extremamente profissional e analítico.
    """

    prompt_usuario = f"""
    Analise profundamente os dados do concurso {dados_completos['concurso']}:
    
    RESUMO MATEMÁTICO:
    {json.dumps(dados_completos['resumo_matematico'], indent=2)}
    
    TABELA TÉCNICA (Dezena por Dezena):
    {json.dumps(dados_completos['detalhamento_tecnico'], indent=2)}
    
    TAREFA:
    Gere EXATAMENTE 40 insights divididos nestas 4 categorias estratégicas:

    1. 💎 MINERAÇÃO DE DADOS (10 insights): Foque nas dezenas com 'Forte Alta' ou tendências claras.
    2. ⏳ LEI DO RETORNO (10 insights): Foque EXCLUSIVAMENTE nas dezenas atrasadas (Gaps).
    3. 📐 ESTRUTURA DO JOGO (10 insights): Analise soma, pares e equilíbrio.
    4. 🎯 PALPITES ALGORÍTMICOS (10 insights): Sugestões diretas baseadas no cruzamento de dados.

    Exemplo de estilo: 
    "💎 A dezena 05 entrou em tendência de 'Forte Alta', saindo 30% a mais que a média."
    "⏳ Alerta Vermelho: A dezena 23 está atrasada há 5 jogos, probabilidade de retorno de 85%."

    FORMATO JSON OBRIGATÓRIO:
    {{
        "analise_referencia": "{dados_completos['concurso']}",
        "insights": [
            {{ "id": 1, "texto": "..." }},
            ... até 40 ...
        ]
    }}
    """

    payload = {
        "model": "mistral-small-latest",
        "messages": [
            {"role": "system", "content": prompt_sistema},
            {"role": "user", "content": prompt_usuario}
        ],
        "temperature": 0.4, # Baixa temperatura para ser muito preciso
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
            print("SUCESSO! Insights Analíticos gerados.")
        else:
            print(f"ERRO MISTRAL: {response.status_code} - {response.text}")

    except Exception as e:
        print(f"ERRO CRÍTICO: {e}")

# ==============================================================================
# 🚀 EXECUTOR
# ==============================================================================

def atualizar_dados():
    print("Iniciando atualização Data Science...")
    os.makedirs("api", exist_ok=True)

    try:
        response = requests.get(API_URL)
        if response.status_code != 200: return
        todos_jogos = response.json()
    except Exception as e:
        print(f"Erro fatal: {e}")
        return

    todos_jogos.sort(key=lambda x: x['concurso'])

    # 1. Compacto
    compacto = [{"c": j['concurso'], "d": [int(d) for d in j['dezenas']]} for j in todos_jogos]
    with open("api/lotofacil_compacto.json", "w", encoding="utf-8") as f:
        json.dump(compacto, f, separators=(',', ':'))

    # 2. Detalhado
    ultimos_10 = todos_jogos[-10:]
    ultimos_10.reverse()
    with open("api/lotofacil_detalhada.json", "w", encoding="utf-8") as f:
        json.dump(ultimos_10, f, indent=2, ensure_ascii=False)

    # 3. Análise IA Robusta (Passa TUDO para calcular médias longas)
    dados_processados = preparar_payload_ia(todos_jogos)
    gerar_insights_mistral(dados_processados)

if __name__ == "__main__":
    atualizar_dados()
