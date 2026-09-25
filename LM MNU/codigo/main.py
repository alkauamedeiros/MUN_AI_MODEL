import time
import logging
import logger_config as log_c

log_c.setup_logger()
logger = logging.getLogger(__name__)

import torch  #Força o carregamento prévio do CUDA no processo
import transcriber as tr
import language as lang
import separator as sep
import display as disp

import speaker as spk

if(__name__ == "__main__"):
    logger.info("==========================================")
    logger.info("Iniciando a pipeline do modelo.")
    logger.info("==========================================")

    tempo_inicio_app = time.perf_counter()

    data_matrix = None

    try:

        AUDIO_FILE = 'simulacao_4.mp3'
        DATA_FILE = 'data_matrix.db'

        logger.info("Criando matriz de dados.")
        data_matrix = sep.DataMatrix(overwrite=False)

        logger.info("Alocando o transcritor de áudio na GPU (Whisper)...")
        tempo_inicio_transcritor = time.perf_counter()

        tr_text = tr.AudioTranscriber("medium", "cuda")

        tempo_transcritor = time.perf_counter() - tempo_inicio_transcritor
        logger.info(f"Transcritor carregado na GPU em {tempo_transcritor:.2f}s.")


        cur_text = ''

        cur_audio = 1

        #Inicia a janela do display
        disp.start_display_thread()
        disp.set_ouvindo()

        try:
            #Variável para acumular as frases de um mesmo orador
            speech_buffer = ""
            
            #Palavras-chave que indicam o fim da fala (em letras minúsculas para facilitar a detecção)
            keywords_encerramento = []
            try:
                with open("../instrucoes/speech_endings.txt", "r", encoding="utf-8") as op:
                    keywords_encerramento = [
                        linha.strip().lower() 
                        for linha in op.read().split('\n') 
                        if linha.strip()
                    ]
            except Exception as e:
                logger.error(f"Falha ao carregar as finalizações de falas: {e}. Vamos assumir a lista default: ['Essa é a minha fala'].")
                keywords_encerramento = ["Essa é a minha fala"]

            #live_stream_transcribe() retorna textos de acordo com as pausas detectadas
            for chunk in tr_text.live_stream_transcribe():
                cur_text = chunk["text"].strip()

                #Ignora blocos vazios
                if(cur_text):
                    #Adiciona o novo trecho ao texto acumulado
                    speech_buffer += cur_text + " "
                    print(f"\n🗣️ Orador falando (parcial): {speech_buffer.strip()}\n")
                
                #Verifica se o orador disse a frase de encerramento
                buffer_minusc = speech_buffer.lower()

                #Usa as palavras-chave ou a barra de espaço para detectar o fim da fala
                apertou_espaco = disp.check_reset_espaco()
                if ((apertou_espaco) or (any(kw in buffer_minusc for kw in keywords_encerramento))):

                    if(apertou_espaco):
                        logger.info("[FIM DE FALA DETECTADO] Interrupção manual via barra de espaço. Processando discurso completo...")
                    else:
                        logger.info("[FIM DE FALA DETECTADO] Processando discurso completo...")

                    tempo_inicio_ciclo = time.perf_counter()

                    #Armazena o texto COMPLETO acumulado
                    final_text = speech_buffer.strip()

                    #Insere o discurso usando o agent_insertion
                    data_matrix.agent_insertion(final_text)

                    #Detecta a ativação da IA
                    agent_activation = data_matrix.ai_activation(final_text)
                    
                    if agent_activation is not None:
                        ai_question = lang.get_response(
                            data_matrix, 
                            agent_activation[0], 
                            agent_activation[1], 
                            f"Faça uma pergunta de {agent_activation[0]} para {agent_activation[1]}"
                        )
                    
                        #==========================================
                        #TRAVA DE ESCUTA
                        #==========================================
                        logger.info("Microfone pausado para a fala da IA.")
                        tr_text.pause_listening()

                        audio_filename = f"../audios/fala_ia{cur_audio}.wav"
                        
                        #GERA O ÁUDIO
                        spk.generate_audio(ai_question, audio_filename)
                        
                        #ATUALIZA A TELA (Falando)
                        disp.set_falando(ai_question, agent_activation[0])

                        #Reproduz e aguarda
                        spk.play_audio_with_interrupt(audio_filename)

                        #ATUALIZA A TELA (Ouvindo)
                        disp.set_ouvindo()
                        
                        tr_text.resume_listening()
                        logger.info("Microfone liberado.")
                        #==========================================
                        
                        cur_audio += 1
                    else:
                        logger.warning("A geração da resposta da IA retornou vazia. Pulando etapa de fala.")

                    #ZERA O BUFFER para o próximo orador poder falar
                    speech_buffer = ""
                    tempo_total_ciclo = time.perf_counter() - tempo_inicio_ciclo
                    logger.info(f"Ciclo de resposta completo processado em {tempo_total_ciclo:.2f}s.")

        except KeyboardInterrupt:
            logger.info("A gravação foi interrompida pelo usuário.")
        #Fecha a matriz e termina a execução do código

        pass
    except Exception as e:
        logger.critical(f"A aplicação encerrou devido a um erro não tratado {e}",
                        exc_info=True)
    finally:
        if data_matrix is not None:
            try:
                data_matrix.close_matrix()
                logger.info("Matriz de dados fechada com sucesso.")
            except Exception as e:
                logger.error(f"Erro ao tentar fechar a matriz de dados: {e}")

        tempo_total = time.perf_counter() - tempo_inicio_app
        logger.info(f"Sistema finalizado. Tempo total: {tempo_total:.2f}s.")
        
        logger.info("Aplicação finalizada.")