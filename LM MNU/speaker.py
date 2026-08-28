import numpy as np
import soundfile as sf
import sounddevice as sd
from kokoro import KPipeline

def generate_audio(text, name):
    text = text.replace(';', '.').replace(',', '.')

    tts_pipeline = KPipeline(lang_code='p')
    generator = tts_pipeline(text, voice='pm_alex', speed=1.0)
    audio_chunks = []
    for _, _, audio in generator:
        chunk = audio.numpy() if hasattr(audio, 'numpy') else audio
        audio_chunks.append(chunk)

    if audio_chunks:
        full_audio = np.concatenate(audio_chunks)
        sf.write(name, full_audio, 24000)
        print("Áudio produzido")

if(__name__ == "__main__"):
    text = 'Texto da IA: Sou da comissão da Inglaterra e gostaria de fazer uma pergunta a representante da China: embora o crescimento econômico acelerado do seu país seja inegável, a sua recente defesa de que as barreiras comerciais e as subsídios estatais são instrumentos legítimos de soberania nacional ignora o fato de que tais práticas distorcem o mercado global e prejudicam a competitividade justa das pequenas e médias empresas europeias; considerando que a Organização Mundial do Comércio defende a redução de distorções, em que medida a China está disposta a revisar suas políticas de subsídio para alinhar seu modelo de desenvolvimento com as normas multilaterais de livre comércio?.'

    generate_audio(text, 'fala_ia_teste.wav')


