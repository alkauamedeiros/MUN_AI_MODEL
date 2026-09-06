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
        CHUNK, FORMAT = 1024, pyaudio.paInt16
        TARGET_RATE = 16000
        
        p = pyaudio.PyAudio()
        
        # 1. BUSCA O SERVIDOR DE SOM CORRETO (PULSE/PIPEWIRE)
        device_index = None
        native_rate = 44100
        channels = 1
        
        for i in range(p.get_device_count()):
            dev_info = p.get_device_info_by_index(i)
            name = dev_info.get("name", "").lower()
            
            # Localiza a ponte 'pulse' que se comunica com apps modernos
            if dev_info.get("maxInputChannels") > 0 and "pulse" in name:
                device_index = i
                native_rate = int(dev_info.get("defaultSampleRate", 44100))
                # Aceita estéreo se o servidor exigir, para evitar buffer de zeros
                channels = min(2, int(dev_info.get("maxInputChannels", 1)))
                break
                
        # Fallback caso não encontre o pulse
        if device_index is None:
            default_info = p.get_default_input_device_info()
            device_index = default_info.get("index")
            native_rate = int(default_info.get("defaultSampleRate", 44100))
            channels = min(2, int(default_info.get("maxInputChannels", 1)))

        print(f"\n🎤 Conectando ao áudio via índice {device_index} ({channels} canais, {native_rate}Hz)...\n")

        try:
            stream = p.open(format=FORMAT, channels=channels, rate=native_rate, 
                            input=True, input_device_index=device_index, frames_per_buffer=CHUNK)
            actual_rate = native_rate
        except Exception as e:
            print(f"⚠️ Aviso: {e}. Tentando fallback de segurança...")
            actual_rate = 44100
            channels = 1
            stream = p.open(format=FORMAT, channels=channels, rate=actual_rate, 
                            input=True, input_device_index=device_index, frames_per_buffer=CHUNK)
            
        SILENCE_THRESHOLD = 300
        SILENCE_CHUNKS = int(actual_rate / CHUNK * 3)
        
        frames, silent_chunks_count, is_speaking = [], 0, False
        
        while True:
            data = stream.read(CHUNK, exception_on_overflow=False)
            
            if not self.listen_event.is_set():
                frames, silent_chunks_count, is_speaking = [], 0, False
                continue
                
            # 2. PROCESSAMENTO DE CANAIS E CÁLCULO RMS
            audio_data = np.frombuffer(data, dtype=np.int16)
            
            # Se a placa forçadamente capturou estéreo, fazemos a conversão matemática para mono
            if channels == 2:
                audio_data = audio_data.reshape(-1, 2).mean(axis=1).astype(np.int16)
                
            rms = np.sqrt(np.mean(audio_data.astype(np.float32)**2))

            print(f"Volume RMS: {rms:.1f}", end='\r') # Exibe na mesma linha para não poluir

            if rms > SILENCE_THRESHOLD:
                is_speaking, silent_chunks_count = True, 0
                frames.append(audio_data.tobytes()) # Salva os bytes já em mono
            elif is_speaking:
                silent_chunks_count += 1
                frames.append(audio_data.tobytes())
                
                if silent_chunks_count > SILENCE_CHUNKS:
                    print("\nEnviando bloco para transcrição...")
                    raw_bytes = b''.join(frames)
                    
                    if actual_rate != TARGET_RATE:
                        audio_16bit = np.frombuffer(raw_bytes, dtype=np.int16)
                        num_target_samples = int(len(audio_16bit) * TARGET_RATE / actual_rate)
                        resampled_audio = scipy.signal.resample(audio_16bit, num_target_samples)
                        raw_bytes = resampled_audio.astype(np.int16).tobytes()

                    self.audio_queue.put(raw_bytes)
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