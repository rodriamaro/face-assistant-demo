import os
from kokoro_onnx import Kokoro

class TTSHandler:
    def __init__(self, model_path="models/kokoro-v1.0.onnx", voices_path="models/voices-v1.0.bin"):
        self.model_path = model_path
        self.voices_path = voices_path
        self.kokoro = None
        self.is_initialized = False
        
        # Check if files exist before initializing
        if os.path.exists(model_path) and os.path.exists(voices_path):
            self.init_model()
        else:
            print("[TTS] Los archivos del modelo no están disponibles. Se inicializará cuando estén listos.")

    def init_model(self):
        try:
            print("[TTS] Cargando modelo Kokoro ONNX en memoria...")
            self.kokoro = Kokoro(self.model_path, self.voices_path)
            self.is_initialized = True
            print("[TTS] Modelo Kokoro ONNX cargado exitosamente.")
        except Exception as e:
            print(f"[TTS] Error al inicializar Kokoro ONNX: {e}")
            self.is_initialized = False

    def speak(self, text, voice="ef_dora", speed=1.1, lang="es"):
        """
        Generates audio samples for the given text.
        Returns: (samples, sample_rate) or (None, None)
        """
        if not self.is_initialized:
            # Try to initialize again (in case downloader finished)
            self.init_model()
            if not self.is_initialized:
                print("[TTS] Kokoro TTS no está listo todavía.")
                return None, None
        
        try:
            # Generate audio samples
            # Kokoro supports Spanish 'es' with voices like ef_dora or em_alex
            print(f"[TTS] Generando voz para: '{text}' con voz '{voice}'...")
            samples, sample_rate = self.kokoro.create(
                text,
                voice=voice,
                speed=speed,
                lang=lang
            )
            return samples, sample_rate
        except Exception as e:
            print(f"[TTS] Error generando audio con Kokoro: {e}")
            # If the Spanish voice fails, try fallback voice (like 'af_sarah' which is standard)
            try:
                print("[TTS] Intentando fallback con voz standard en inglés...")
                samples, sample_rate = self.kokoro.create(
                    text,
                    voice="af_sarah",
                    speed=speed,
                    lang="en-us"
                )
                return samples, sample_rate
            except Exception as e2:
                print(f"[TTS] Fallback también falló: {e2}")
                return None, None
