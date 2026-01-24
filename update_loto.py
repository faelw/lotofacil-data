import requests
import json
import os

# Configuração
API_URL = "https://loteriascaixa-api.herokuapp.com/api/lotofacil"

def atualizar_dados():
    print("Iniciando atualização...")
    
    # 1. Cria as pastas se não existirem
    os.makedirs("api", exist_ok=True)

    # 2. Baixa TUDO da API (Todos os concursos)
    # Nota: Essa API retorna uma lista com todos os jogos de uma vez.
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

    # 3. CRIA O ARQUIVO COMPACTO (Leve para o App conferir jogos)
    # Pega apenas concurso e dezenas de TODOS os jogos
    compacto = []
    for jogo in todos_jogos:
        compacto.append({
            "c": jogo['concurso'],
            "d": [int(d) for d in jogo['dezenas']] # Converte para número para economizar espaço
        })
    
    with open("api/lotofacil_compacto.json", "w", encoding="utf-8") as f:
        json.dump(compacto, f, separators=(',', ':')) # Remove espaços para ficar bem leve
    print("Arquivo compacto gerado.")

    # 4. CRIA O ARQUIVO DETALHADO (Apenas os 10 últimos)
    # Pega tudo: ganhadores, valores, locais, etc.
    ultimos_10 = todos_jogos[-10:] # Pega os últimos 10 da lista
    
    # Inverte para o mais recente ficar em primeiro (opcional, ajuda no App)
    ultimos_10.reverse() 

    with open("api/lotofacil_detalhada.json", "w", encoding="utf-8") as f:
        json.dump(ultimos_10, f, indent=2, ensure_ascii=False)
    print("Arquivo detalhado gerado.")

if __name__ == "__main__":
    atualizar_dados()
