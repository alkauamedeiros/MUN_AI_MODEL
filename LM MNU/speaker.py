import numpy as np
import soundfile as sf
import sounddevice as sd
import subprocess
import threading
import sys
import select
from kokoro import KPipeline


def smart_split(text, max_length=250):
    """
    Divide o texto em pedaços baseados em vírgulas para manter a fluidez.
    Garante que nenhum pedaço ultrapasse o max_length para não quebrar o TTS.
    """
    # Trocamos : e ; por vírgulas para manter a entonação contínua e a pausa curta
    text = text.replace(':', ',').replace(';', ',')
    
    # Dividimos o texto inteiro onde há vírgulas
    parts = text.split(',')
    
    chunks = []
    current_chunk = ""
    
    for i, part in enumerate(parts):
        # Re-adiciona a vírgula para dar a instrução de "pausa curta" ao modelo,
        # exceto na última parte (que geralmente já tem ponto de interrogação/final)
        separator = "," if i < len(parts) - 1 else ""
        part_with_punct = part.strip() + separator
        
        # Se juntar o pedaço atual passar do limite, guardamos o que temos e começamos um novo
        if len(current_chunk) + len(part_with_punct) > max_length and current_chunk:
            chunks.append(current_chunk.strip())
            current_chunk = part_with_punct + " "
        else:
            current_chunk += part_with_punct + " "
            
    if current_chunk:
        chunks.append(current_chunk.strip())
        
    return chunks

def generate_audio(text, name):
    # Divide os discursos usando a palavra-chave que você colocou no texto
    discursos = text.split('[PAUSA]')
    
    tts_pipeline = KPipeline(lang_code='p')
    audio_chunks = []
    
    # Cria exatamente 4 segundos de silêncio (24000 amostras/segundo * 4 segundos)
    silencio = np.zeros(24000 * 4, dtype=np.float32)

    for i, discurso in enumerate(discursos):
        chunks = smart_split(discurso, max_length=300)
        
        for chunk in chunks:
            if not chunk: continue
            
            generator = tts_pipeline(chunk, voice='pm_alex', speed=1.0)
            
            for _, _, audio in generator:
                audio_array = audio.numpy() if hasattr(audio, 'numpy') else audio
                audio_chunks.append(audio_array)
        
        # Adiciona os 4 segundos de silêncio após cada orador, exceto no último
        if i < len(discursos) - 1:
            audio_chunks.append(silencio)

    if audio_chunks:
        full_audio = np.concatenate(audio_chunks)
        sf.write(name, full_audio, 24000)
        print(f"Áudio '{name}' produzido com sucesso!")

def play_audio_with_interrupt(file_path):
    """
    Reproduz o áudio e escuta o teclado no Linux.
    Pressionar ENTER cancela o áudio imediatamente e devolve o controle ao script.
    """
    process = subprocess.Popen(["aplay", file_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print("📢 Reproduzindo fala da IA... [Pressione ENTER para cortar]")

    stop_event = threading.Event()

    def listen_for_interrupt():
        while process.poll() is None and not stop_event.is_set():
            # Monitora se alguma tecla foi pressionada no terminal
            if select.select([sys.stdin], [], [], 0.1)[0]:
                sys.stdin.readline()  # Limpa o buffer do teclado
                if process.poll() is None:
                    print("\n🛑 Fala da IA interrompida manualmente!")
                    process.terminate()
                break

    interrupt_thread = threading.Thread(target=listen_for_interrupt, daemon=True)
    interrupt_thread.start()

    process.wait()
    stop_event.set()


if(__name__ == "__main__"):
    print("Carregando o modelo KOKORO na GPU...")
    with open("debate_slow_down.txt", 'r') as op:
        text = op.read()

    generate_audio(text, "simualacao_final_2.wav")
