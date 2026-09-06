import torch  # Força o carregamento prévio do CUDA no processo
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

    try:
        # O gerador entrega o texto imediatamente após a pausa ser detectada e transcrita
        for chunk in tr_text.live_stream_transcribe():
            cur_text = chunk["text"].strip()

            # Ignora blocos vazios (ruídos de fundo que a IA não transcreveu como palavras)
            if not cur_text:
                continue
                
            print(f"Transcrição do áudio: {cur_text}")
            
            # Envia o texto para o agente imediatamente após a fala
            agent_decision = data_matrix.agent_insertion(cur_text)
            
            if agent_decision is not None:
                ai_question = lang.get_response(
                    data_matrix, 
                    agent_decision[0], 
                    agent_decision[1], 
                    f"Faça uma pergunta de {agent_decision[0]} para {agent_decision[1]}"
                )
                print(f"\n\nPergunta da IA: {ai_question}")
                
                # ==========================================
                # TRAVA DE ESCUTA
                # ==========================================
                print("🔒 Microfone pausado para a fala da IA...")
                tr_text.pause_listening()
                
                # spk.generate_audio(ai_question, f"fala_ia{cur_audio}.wav")
                
                tr_text.resume_listening()
                print("🔓 Microfone liberado.\n")
                # ==========================================
                
                cur_audio += 1

    except KeyboardInterrupt:
        print("\n[AVISO] Gravação interrompida pelo usuário (Ctrl+C).")

    # Finalização do script que já existia no seu main.py original
    print("Gerando pergunta final...")
    ai_text = lang.get_response(
        data_matrix, 
        "INGLATERRA", 
        "ESTADOS_UNIDOS_DA_AMERICA", 
        "Faça uma pergunta da Inglaterra para Estados Unidos."
    )
    print(f"Texto da IA: {ai_text}.")
    
    # spk.generate_audio(ai_text, "fala_ia_final.wav")
    
    data_matrix.close_matrix()
    print("Pipeline encerrada com sucesso.")
    pass





    # for chunk in tr_text.stream_transcribe(AUDIO_FILE):
    #     text = chunk["text"]

    #     #Agregadores de texto
    #     cur_lump+=1
    #     cur_text+=f" {text}"

    #     #Verifica se o texto foi suficientemente agrupado
    #     if(cur_lump == TEXT_LUMP):
    #         #Envia o texto para o agente que armazena o texto na matriz
    #         agent_decision = data_matrix.agent_insertion(cur_text)
    #         print(f"Transcrição do áudio: {cur_text}")
    #         if(agent_decision != None):
    #             ai_question = lang.get_response(data_matrix, agent_decision[0], agent_decision[1], f"Faça uma pergunta de {agent_decision[0]} para {agent_decision[1]}")
    #             print('\n\n')
    #             print(f"Pergunta da IA: {ai_question}")
    #             #spk.generate_audio(ai_question, f"fala_ia{cur_audio}.wav")
    #             cur_audio += 1
    #             pass

    #         print("\n")

    #         cur_text = ''
    #         cur_lump = 1


