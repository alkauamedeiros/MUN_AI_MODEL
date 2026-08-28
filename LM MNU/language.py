import ollama

def get_response(matrix, autor, receiver, user_input):

    question_context = None
    with open("question_context.txt", 'r') as op:
        question_context = op.read()

    question_context+= matrix.search_cell(autor, receiver)
    question_context+= '\n'+matrix.search_cell(receiver, autor)

    stream = ollama.chat(
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
        options={'temperature' : 0.2},

        think = False,
        stream = False
    )

    return stream['message']['content']
