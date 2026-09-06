import numpy as np
import soundfile as sf
import sounddevice as sd
from kokoro import KPipeline
#from f5_tts.api import F5TTS
#from TTS.api import TTS

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


if(__name__ == "__main__"):
    print("Carregando o modelo KOKORO na GPU...")
    with open("debate_slow_down.txt", 'r') as op:
        text = op.read()

    generate_audio(text, "simualacao_final_2.wav")
