import os
import warnings
import numpy as np
import soundfile as sf
import subprocess
import threading
import sys
import select
from kokoro import KPipeline
import logging
import time

logger = logging.getLogger(__name__)

#Silencia alguns avisos no terminal
warnings.filterwarnings("ignore")
os.environ["PYTHONWARNINGS"] = "ignore"
os.environ["HF_HUB_ENABLE_HF_TRANSFER"] = "0"
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["HF_TOKEN"] = ""
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"


tempo_inicio = time.perf_counter()
logger.debug("Carregando o modelo Kokoro com as configurações (lang_code='p', repo_id='hexgrad/Kokoro-82M').")
tts_pipeline = KPipeline(lang_code='p', repo_id='hexgrad/Kokoro-82M')

tempo_kokoro = time.perf_counter() - tempo_inicio
logger.debug(f"O modelo Kokoro foi carregado em {tempo_kokoro:.2f}s.")

def generate_audio(text, name):
    tempo_inicio = time.perf_counter()
    try:
        audio_chunks = []

        logger.info("Iniciando a criação do áudio.")

        generator = tts_pipeline(text, voice='pm_alex', speed=1.0)

        for _, _, audio in generator:
            audio_array = audio.numpy() if hasattr(audio, 'numpy') else audio
            audio_chunks.append(audio_array)

        if audio_chunks:
            full_audio = np.concatenate(audio_chunks)
            sf.write(name, full_audio, 24000)
            
            tempo_decorrido = time.perf_counter() - tempo_inicio
            logger.info(f"Áudio produzido com sucesso em {tempo_decorrido:.2f}s | Salvo em: '{name}'")
        else:
            logger.warning("O modelo TTS não gerou nenhum segmento de áudio.")

    except Exception as e:
        tempo_decorrido = time.perf_counter() - tempo_inicio
        logger.error(f"A geração do áudio falhou após {tempo_decorrido:.2f}s: {e}",
                     exc_info=True)

def play_audio_with_interrupt(file_path):
    """
    Reproduz o áudio e escuta o teclado no Linux.
    Pressionar ENTER cancela o áudio imediatamente e devolve o controle ao script.
    """

    tempo_inicio = time.perf_counter()

    if not os.path.exists(file_path):
        logger.error(f"Arquivo de áudio não encontrado para reprodução: '{file_path}'")
        return

    try:
        process = subprocess.Popen(["aplay", file_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print("📢 Reproduzindo fala da IA... [Pressione ENTER para cortar]")

        stop_event = threading.Event()

        def listen_for_interrupt():
            while process.poll() is None and not stop_event.is_set():
                #Monitora se alguma tecla foi pressionada no terminal
                if select.select([sys.stdin], [], [], 0.1)[0]:
                    sys.stdin.readline()  #Limpa o buffer do teclado
                    if process.poll() is None:
                        logger.info("Reprodução do áudio interrompida pelo usuário.")
                        process.terminate()
                    break

        interrupt_thread = threading.Thread(target=listen_for_interrupt, daemon=True)
        interrupt_thread.start()

        process.wait()
        stop_event.set()

        tempo_decorrido = time.perf_counter() - tempo_inicio
        logger.info(f"Reprodução do áudio finalizada após {tempo_decorrido:.2f}s.")
    except Exception as e:
        tempo_decorrido = time.perf_counter() - tempo_inicio
        logger.error(f"Erro durante a execução após {tempo_decorrido:.2f}s: {e}")


if(__name__ == "__main__"):
    print("Carregando o modelo KOKORO na GPU...")
    with open("debate_slow_down.txt", 'r') as op:
        text = op.read()

    generate_audio(text, "simualacao_final_2.wav")
