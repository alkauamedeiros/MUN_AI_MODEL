import ollama

ollama_client = ollama.Client(host='http://127.0.0.1:11435')

def chat(*args):
    return ollama.chat(args)