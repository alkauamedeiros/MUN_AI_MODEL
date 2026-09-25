import urllib.request
import os

# Dicionário mapeando os nomes para o código do país na API
paises = {
    "CHINA": "cn",
    "BRASIL": "br",
    "ALEMANHA": "de",
    "COLOMBIA": "co",
    "EGITO": "eg",
    "ESTADOS_UNIDOS": "us",
    "FRANCA": "fr",
    "INDIA": "in",
    "BAHREIN": "bh",
    "ISRAEL": "il",
    "PALESTINA": "ps",
    "PANAMA": "pa",
    "CONGO": "cd",
    "RUSSIA": "ru"
}

# Cria a pasta 'flags' se ela não existir
os.makedirs("flags", exist_ok=True)

print("Iniciando o download das bandeiras...")

for nome, codigo in paises.items():
    url = f"https://flagcdn.com/w320/{codigo}.png"
    caminho_arquivo = f"flags/{nome}.png"
    
    try:
        urllib.request.urlretrieve(url, caminho_arquivo)
        print(f"✅ {nome}.png baixada com sucesso!")
    except Exception as e:
        print(f"❌ Erro ao baixar {nome}: {e}")

print("\nDownload concluído! Agora você pode testar a interface do seu main.py.")