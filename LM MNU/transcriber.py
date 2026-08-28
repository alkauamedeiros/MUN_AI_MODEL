import os
import site
from faster_whisper import WhisperModel

#O PIP INSTALL
#pip install nvidia-cublas-cu12 nvidia-cudnn-cu12

# Configuração de CUDA
python_libs = site.getsitepackages()[0]
os.environ["LD_LIBRARY_PATH"] = f"{os.path.join(python_libs, 'nvidia/cublas/lib')}:{os.path.join(python_libs, 'nvidia/cudnn/lib')}:" + os.environ.get("LD_LIBRARY_PATH", "")

class AudioTranscriber:
    def __init__(self, model_size="medium", device="cuda", compute_type="float16"):
        self.model = WhisperModel(model_size, device=device, compute_type=compute_type)

    def stream_transcribe(self, audio_path: str, language="pt"):
        """Yields cada segmento de áudio conforme é processado."""
        segments, _ = self.model.transcribe(audio_path, language=language, beam_size=5)
        for segment in segments:
            yield {
                #"start": segment.start,
                #"end": segment.end,
                "text": segment.text.strip()
            }