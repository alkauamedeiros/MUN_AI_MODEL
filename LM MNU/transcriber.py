import os
import site
import scipy.signal
import pyaudio
import numpy as np
import queue
import threading
from faster_whisper import WhisperModel

# (Mantenha sua configuração de CUDA existente aqui)

class AudioTranscriber:
    def __init__(self, model_size="medium", device="cuda", compute_type="float16"):
        self.model = WhisperModel(model_size, device=device, compute_type=compute_type)
        self.audio_queue = queue.Queue()
        
        self.listen_event = threading.Event()
        self.listen_event.set() 

    def pause_listening(self):
        self.listen_event.clear()

    def resume_listening(self):
        self.listen_event.set()

    def _record_audio(self):
        import subprocess
        
        CHUNK = 1024
        TARGET_RATE = 16000
        SILENCE_THRESHOLD = 500
        SILENCE_CHUNKS = int(TARGET_RATE / CHUNK * 1.5)
        
        print("\n🎤 Iniciando captura nativa via PulseAudio (Bypass do Conda)...")

        # Chama o gravador nativo do Linux já formatado para o Whisper (16kHz, Mono, 16-bit)
        cmd = ["parecord", "--raw", "--format=s16le", "--channels=1", "--rate=16000"]
        
        try:
            # Inicia o processo de gravação em segundo plano
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        except FileNotFoundError:
            print("[ERRO] Comando 'parecord' não encontrado. Instale o pacote 'pulseaudio-utils'.")
            return

        frames, silent_chunks_count, is_speaking = [], 0, False
        
        while True:
            # Lê 2048 bytes (1024 amostras de 2 bytes) diretos do fluxo do sistema
            data = process.stdout.read(CHUNK * 2)
            
            if not data:
                break
                
            if not self.listen_event.is_set():
                frames, silent_chunks_count, is_speaking = [], 0, False
                continue
                
            # Calcula o RMS
            audio_data = np.frombuffer(data, dtype=np.int16)
            rms = np.sqrt(np.mean(audio_data.astype(np.float32)**2))

            print(f"Volume RMS Nativo: {rms:.1f}", end='\r')

            # Lógica de gravação de silêncio (inalterada)
            if rms > SILENCE_THRESHOLD:
                is_speaking, silent_chunks_count = True, 0
                frames.append(data)
            elif is_speaking:
                silent_chunks_count += 1
                frames.append(data)
                
                if silent_chunks_count > SILENCE_CHUNKS:
                    print("\nEnviando bloco para transcrição...")
                    self.audio_queue.put(b''.join(frames))
                    frames, is_speaking, silent_chunks_count = [], False, 0

    def live_stream_transcribe(self, language="pt"):
        record_thread = threading.Thread(target=self._record_audio, daemon=True)
        record_thread.start()

        while True:
            audio_bytes = self.audio_queue.get()
            audio_np = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32768.0
            
            # O Whisper analisa o áudio inteiro e pode retornar múltiplos segmentos
            segments, _ = self.model.transcribe(audio_np, language=language, beam_size=5, vad_filter=True, condition_on_previous_text=False)
            
            # Em vez de mandar um por um, juntamos todos os segmentos em uma única string
            full_text = " ".join([segment.text.strip() for segment in segments])
            
            # Só envia para o main.py se a string não estiver vazia
            if full_text:
                yield {"text": full_text}
            
            self.audio_queue.task_done()

    # def live_stream_transcribe(self, language="pt"):
    #     record_thread = threading.Thread(target=self._record_audio, daemon=True)
    #     record_thread.start()

    #     while True:
    #         audio_bytes = self.audio_queue.get()
    #         audio_np = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32768.0
            
    #         segments, _ = self.model.transcribe(audio_np, language=language, beam_size=5)
    #         for segment in segments:
    #             yield {"text": segment.text.strip()}
            
    #         self.audio_queue.task_done()