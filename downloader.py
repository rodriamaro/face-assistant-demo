import os
import urllib.request
import sys

MODELS_DIR = "models"
MODEL_URL = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx"
VOICES_URL = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin"

MODEL_PATH = os.path.join(MODELS_DIR, "kokoro-v1.0.onnx")
VOICES_PATH = os.path.join(MODELS_DIR, "voices-v1.0.bin")

def report_progress(block_num, block_size, total_size):
    read_so_far = block_num * block_size
    if total_size > 0:
        percent = min(100, read_so_far * 100 / total_size)
        sys.stdout.write(f"\rDescargando: {percent:.1f}% ({read_so_far / (1024*1024):.1f} MB de {total_size / (1024*1024):.1f} MB)")
        sys.stdout.flush()
    else:
        sys.stdout.write(f"\rDescargando: {read_so_far / (1024*1024):.1f} MB")
        sys.stdout.flush()

def download_file(url, destination):
    print(f"\nIniciando descarga de {url}...")
    urllib.request.urlretrieve(url, destination, report_progress)
    print(f"\nDescargado con éxito en {destination}")

def ensure_models_exist():
    if not os.path.exists(MODELS_DIR):
        os.makedirs(MODELS_DIR)
        print(f"Creado directorio: {MODELS_DIR}")
        
    if not os.path.exists(MODEL_PATH):
        print("Falta el modelo Kokoro ONNX.")
        download_file(MODEL_URL, MODEL_PATH)
    else:
        print("Modelo Kokoro ONNX ya existe.")
        
    if not os.path.exists(VOICES_PATH):
        print("Falta el archivo de voces Kokoro.")
        download_file(VOICES_URL, VOICES_PATH)
    else:
        print("Archivo de voces Kokoro ya existe.")

if __name__ == "__main__":
    ensure_models_exist()
