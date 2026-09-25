import ollama

#DEPENDE DA SALA!!
#205: http://127.0.0.1:11435
#204: http://127.0.0.1:11436
#203: http://127.0.0.1:11437
ollama_client = ollama.Client(host='http://127.0.0.1:11435')

def chat(*args):
    return ollama.chat(args)