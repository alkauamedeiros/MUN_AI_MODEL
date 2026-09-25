import numpy as np
import queue
import threading
from faster_whisper import WhisperModel
import logging
import logger_config as log_c
import time

# Recupera o logger identificado com o nome deste módulo
logger = logging.getLogger(__name__)

class AudioTranscriber:
    def __init__(self, model_size="medium", device="cuda", compute_type="float16"):
        tempo_carregamento_inicio = time.perf_counter()

        logger.info(f"Carregando modelo Whisper '{model_size}' no dispositivo '{device}' ({compute_type}).")

        self.model = WhisperModel(model_size, device=device, compute_type=compute_type)
        tempo_carregamento_final = time.perf_counter() - tempo_carregamento_inicio

        logger.info(f"Modelo Whisper carregado com sucesso em {tempo_carregamento_final:.2f}s.")

        self.audio_queue = queue.Queue()
        
        self.listen_event = threading.Event()
        self.listen_event.set()

    def pause_listening(self):
        logger.info("Gravação em segundo plano pausada.")
        self.listen_event.clear()

    def resume_listening(self):
        logger.info("Gravação em segundo plano retomada.")
        self.listen_event.set()

    def _record_audio(self):
        import subprocess

        logger.info("Thread de gravação em segundo plano iniciada.")
        
        CHUNK = 1024
        TARGET_RATE = 16000
        SILENCE_THRESHOLD = 500
        SILENCE_CHUNKS = int(TARGET_RATE / CHUNK * 1.5)
        
        print("\n🎤 Iniciando captura nativa via PulseAudio (Bypass do Conda)...")

        #Chama o gravador nativo do Linux já formatado para o Whisper (16kHz, Mono, 16-bit)
        cmd = ["parecord", "--raw", "--format=s16le", "--channels=1", "--rate=16000"]
        
        try:
            #Inicia o processo de gravação em segundo plano
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
            logger.info("Processo de gravação em segundo plano iniciado.")
        except Exception as e:
            print("[ERRO] Comando 'parecord' não encontrado. Instale o pacote 'pulseaudio-utils'.")
            logger.error(f"Erro crítico de inicialização da gravação em segundo plano: {e}", exc_info=True)
            return

        frames, silent_chunks_count, is_speaking = [], 0, False

        try:
            while True:
                #Lê 2048 bytes (1024 amostras de 2 bytes) diretos do fluxo do sistema
                data = process.stdout.read(CHUNK * 2)
                
                if not data:
                    logger.warning("Fluxo de áudio do 'parecord' retornou vazio. Encerrando gravação")
                    break
                    
                if not self.listen_event.is_set():
                    frames, silent_chunks_count, is_speaking = [], 0, False
                    continue
                    
                #Calcula o RMS
                audio_data = np.frombuffer(data, dtype=np.int16)
                rms = np.sqrt(np.mean(audio_data.astype(np.float32)**2))

                print(f"Volume RMS Nativo: {rms:.1f}", end='\r')

                #Lógica de gravação de silêncio (inalterada)
                if rms > SILENCE_THRESHOLD:
                    is_speaking, silent_chunks_count = True, 0
                    frames.append(data)
                elif is_speaking:
                    silent_chunks_count += 1
                    frames.append(data)
                    
                    if silent_chunks_count > SILENCE_CHUNKS:
                        logger.info("Silêncio de detectado. Enviando bloco para transcrição.")
                        print("\nEnviando bloco para transcrição...")
                        self.audio_queue.put(b''.join(frames))
                        frames, is_speaking, silent_chunks_count = [], False, 0
        except Exception as e:
            logger.error(f"Erro inesperado no loop de gravação de áudio: {e}",
                         exc_info=True)
        finally:
            logger.info("Thread de gravação em segundo plano finalizada.")

    def live_stream_transcribe(self, language="pt"):

        logger.info("Iniciando transcrição ao vivo.")

        record_thread = threading.Thread(target=self._record_audio, daemon=True)
        record_thread.start()

        tempo_inicio = time.perf_counter()

        try:
            while True:
                try:
                    # Adicionado timeout para não travar o loop no silêncio
                    audio_bytes = self.audio_queue.get(timeout=0.5)
                except queue.Empty:
                    # Se der timeout, retorna um bloco vazio para o main.py girar o loop
                    yield {"text": ""}
                    continue

                audio_np = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32768.0

                tempo_transc_inicio = time.perf_counter()
                
                #O Whisper analisa o áudio inteiro e pode retornar múltiplos segmentos
                segments, _ = self.model.transcribe(audio_np, language=language, beam_size=5, vad_filter=True, condition_on_previous_text=False)
                
                full_text = " ".join([segment.text.strip() for segment in segments])
                
                tempo_transc_decorrido = time.perf_counter() - tempo_transc_inicio
                
                if full_text:
                    discurso_formatado = log_c.formatar_discurso_log(full_text)

                    logger.info(f'Transcrição de {len(full_text)} caracteres concluída em {tempo_transc_decorrido:.2f}s. | Texto: "{discurso_formatado}"')

                    logger.debug(f'Texto completo da transcrição: "{full_text}"')

                    yield {"text": full_text}
                else:
                    logger.debug(f"Processamento de áudio sem texto detectado em {tempo_transc_decorrido:.2f}")
                
                self.audio_queue.task_done()
        except Exception as e:
            tempo_decorrido = time.perf_counter() - tempo_inicio

            logger.error(f"Falha ao transcrever o áudio após {tempo_decorrido:.2f}s: {e}",
                        exc_info=True)