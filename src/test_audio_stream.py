import numpy as np
import sounddevice as sd
from tts_handler import TTSHandler
from audio_handler import AudioHandler

print("Inicializando...")
tts = TTSHandler("models/kokoro-v1.0.onnx", "models/voices-v1.0.bin")
audio = AudioHandler()

text = "Hola probando el sonido de la boca con stream de audio"
samples, sr = tts.speak(text, voice="ef_dora")

if samples is not None:
    print(f"Reproduciendo con AudioHandler.play_audio...")
    # Mock GUI callback
    audio.play_audio(samples, sr, lambda r: None)
    print("Reproducción terminada.")
else:
    print("Error: samples es None")
