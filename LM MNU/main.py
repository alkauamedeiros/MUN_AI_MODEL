import ollama
import transcriber as tr
import language as lang
import speaker as spk
import separator as sep

TEXT_LUMP = 20

def get_context():
    with open("context.txt", "r", encoding="utf-8") as op:
        return op.read()


if(__name__ == "__main__"):
    AUDIO_FILE = 'simulacao_4.mp3'
    DATA_FILE = 'data_matrix.db'

    print("Criando matriz de dados")    
    data_matrix = sep.DataMatrix(overwrite=True)

    print("Alocando o transcritor de áudio na GPU")
    tr_text = tr.AudioTranscriber("medium", "cuda")

    #Agregadores de texto
    cur_lump = 1
    cur_text = ''

    print("Começando a transcrever o diálogo e guardar na matrix de dados.\n")

    cur_audio = 1

    #Para cada pedaço de áudio transcrito em stream_transcribe
    for chunk in tr_text.stream_transcribe(AUDIO_FILE):
        text = chunk["text"]

        #Agregadores de texto
        cur_lump+=1
        cur_text+=f" {text}"

        #Verifica se o texto foi suficientemente agrupado
        if(cur_lump == TEXT_LUMP):
            #Envia o texto para o agente que armazena o texto na matriz
            agent_decision = data_matrix.agent_insertion(cur_text)
            print(f"Transcrição do áudio: {cur_text}")
            if(agent_decision != None):
                ai_question = lang.get_response(data_matrix, agent_decision[0], agent_decision[1], f"Faça uma pergunta de {agent_decision[0]} para {agent_decision[1]}")
                print('\n\n')
                print(f"Pergunta da IA: {ai_question}")
                spk.generate_audio(ai_question, f"fala_ia{cur_audio}.wav")
                cur_audio += 1
                pass


            cur_text = ''
            cur_lump = 1

    ai_text = lang.get_response(data_matrix, "Inglaterra", "China", f"Faça uma pergunta de Inglaterra para China.")
    print(f"Texto da IA: {ai_text}.")
    spk.generate_audio(ai_text, "fala_ia.wav")
    
    data_matrix.close_matrix()
    pass
