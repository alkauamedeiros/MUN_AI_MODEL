from ollama_config import ollama_client

def get_response(matrix, autor, receiver, user_input):

    question_context = None
    with open("question_context.txt", 'r') as op:
        question_context = op.read()

    country_context = None
    try:
        with open(f"{autor}_CONTEXT.txt", 'r') as op:
            country_context = op.read()
            question_context+= country_context
    except:
        print("Erro de abertura do contexto do país!")

    question_context+= matrix.search_cell(autor, autor)
    question_context+= matrix.search_cell(autor, receiver)
    question_context+= '\n\nFalas do debate:\n'+matrix.search_cell(receiver, autor)
    question_context+= '\n\nLembre-se de obedecer à formatação adequada, não usando aspas ou asteriscos. Se apresente, desenvolva sua pergunta com base nos contextos fornecidos, e faça a pergunta. Sua resposta deve ser comparável a uma fala de 1 minuto ou mais.'

    #print(f"\n\nQUESTION CONTEXT: {question_context}\n\n")

    stream = ollama_client.chat(
        model = 'qwen3.5:9b',
        messages=[
            {
                'role' : 'system',
                'content' :  question_context,
            },

            {
                'role' : 'user',
                'content' : user_input,
            },
        ],
        options={'temperature' : 0.5},

        think = False,
        stream = False
    )

    return stream['message']['content']
