import numpy as np
import sounddevice as sd
import time
from tts_handler import TTSHandler

print("Inicializando TTS...")
tts = TTSHandler("models/kokoro-v1.0.onnx", "models/voices-v1.0.bin")

text = "Hola probando el sonido uno dos tres"
print(f"Generando voz para: '{text}'")
samples, sr = tts.speak(text, voice="ef_dora")

if samples is not None:
    print(f"Voz generada. Muestras: {len(samples)}, Frecuencia: {sr}")
    print("Reproduciendo con sounddevice.play...")
    sd.play(samples, sr)
    sd.wait()
    print("Reproducción terminada.")
else:
    print("Error: samples es None")
