import requests
import json
import os

# Configuração
API_URL = "https://loteriascaixa-api.herokuapp.com/api/lotofacil"

def atualizar_dados():
    print("Iniciando atualização...")
    
    os.makedirs("api", exist_ok=True)

    try:
        response = requests.get(API_URL)
        if response.status_code != 200:
            print("Erro ao acessar API")
            return
        
        todos_jogos = response.json()
        print(f"Total de jogos baixados: {len(todos_jogos)}")

    except Exception as e:
        print(f"Erro fatal: {e}")
        return

    # --- CORREÇÃO IMPORTANTE ---
    # Forçamos a ordenação pelo número do concurso (Crescente: 1, 2, 3... Atual)
    # Isso garante que a lógica funcione não importa como a API mande os dados.
    todos_jogos.sort(key=lambda x: x['concurso'])

    # 1. CRIA O ARQUIVO COMPACTO (Leve)
    compacto = []
    for jogo in todos_jogos:
        compacto.append({
            "c": jogo['concurso'],
            "d": [int(d) for d in jogo['dezenas']]
        })
    
    with open("api/lotofacil_compacto.json", "w", encoding="utf-8") as f:
        json.dump(compacto, f, separators=(',', ':'))
    print("Arquivo compacto gerado.")

    # 2. CRIA O ARQUIVO DETALHADO (Apenas os 10 mais recentes)
    # Como ordenamos lá em cima, o final da lista ([-10:]) agora são os RECENTES.
    ultimos_10 = todos_jogos[-10:] 
    
    # Invertemos para que no App o Jogo Atual apareça em primeiro na lista
    ultimos_10.reverse() 

    with open("api/lotofacil_detalhada.json", "w", encoding="utf-8") as f:
        json.dump(ultimos_10, f, indent=2, ensure_ascii=False)
    print("Arquivo detalhado gerado.")

if __name__ == "__main__":
    atualizar_dados()
