import threading
import time
import sys
import os
import ctypes
import glob

# Preload CUDA libraries if installed via pip to avoid libcublas/libcudnn search errors
try:
    import nvidia.cublas
    import nvidia.cudnn
    
    lib_dirs = []
    # Search in all paths registered by nvidia namespace packages
    for path in list(nvidia.cublas.__path__):
        lib_dir = os.path.join(path, "lib")
        if os.path.exists(lib_dir):
            lib_dirs.append(lib_dir)
    for path in list(nvidia.cudnn.__path__):
        lib_dir = os.path.join(path, "lib")
        if os.path.exists(lib_dir):
            lib_dirs.append(lib_dir)
            
    preloaded_count = 0
    
    # Load libcublasLt first as it is a dependency of libcublas
    for d in lib_dirs:
        lt_libs = glob.glob(os.path.join(d, "libcublasLt.so*"))
        if lt_libs:
            try:
                ctypes.CDLL(lt_libs[0], mode=ctypes.RTLD_GLOBAL)
                print(f"[System] Pre-cargada: {os.path.basename(lt_libs[0])}")
                preloaded_count += 1
            except Exception as e:
                print(f"[System] Error pre-cargando Lt: {e}")
                
    # Load libcublas
    for d in lib_dirs:
        cublas_libs = glob.glob(os.path.join(d, "libcublas.so*"))
        for p in cublas_libs:
            if "libcublasLt" not in p:
                try:
                    ctypes.CDLL(p, mode=ctypes.RTLD_GLOBAL)
                    print(f"[System] Pre-cargada: {os.path.basename(p)}")
                    preloaded_count += 1
                    break
                except Exception as e:
                    print(f"[System] Error pre-cargando cublas: {e}")
                    
    # Load libcudnn
    for d in lib_dirs:
        cudnn_libs = glob.glob(os.path.join(d, "libcudnn.so*"))
        if cudnn_libs:
            try:
                ctypes.CDLL(cudnn_libs[0], mode=ctypes.RTLD_GLOBAL)
                print(f"[System] Pre-cargada: {os.path.basename(cudnn_libs[0])}")
                preloaded_count += 1
            except Exception as e:
                print(f"[System] Error pre-cargando cudnn: {e}")
                
    if preloaded_count > 0:
        print(f"[System] Éxito: Se pre-cargaron {preloaded_count} librerías CUDA desde PIP.")
except Exception as e:
    print(f"[System] Advertencia en el pre-cargador de CUDA: {e}")

from downloader import ensure_models_exist, MODEL_PATH, VOICES_PATH
from face_gui import FaceGUI
from audio_handler import AudioHandler
from tts_handler import TTSHandler
from brain import AssistantBrain
from faster_whisper import WhisperModel

class AssistantApp:
    def __init__(self):
        self.gui = FaceGUI()
        self.audio = AudioHandler()
        # By default, use None (system default device) to let Pipewire route to S/PDIF.
        # This prevents locking raw ALSA hardware devices.
        self.output_device = None
        
        # Bind window close event
        self.is_running = True
        self.gui.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Start background processing thread
        self.bg_thread = threading.Thread(target=self.background_loop, daemon=True)
        self.bg_thread.start()

    def on_closing(self):
        print("\n[System] Cerrando aplicación...")
        self.is_running = False
        self.gui.root.destroy()
        sys.exit(0)

    def background_loop(self):
        # 1. Show thinking while loading models
        self.gui.set_state("THINKING")
        print("[System] Iniciando sistema local de asistente...")
        
        # 2. Download models if missing
        try:
            ensure_models_exist()
        except Exception as e:
            print(f"[System] Error al descargar modelos: {e}")
            self.gui.set_state("IDLE")
            return
            
        # 3. Load TTS
        tts = TTSHandler(MODEL_PATH, VOICES_PATH)
        
        # 4. Load Brain (Ollama)
        brain = AssistantBrain(model_name="llama3.1")
        
        # 5. Load STT (Whisper on CUDA GPU)
        try:
            print("[STT] Cargando Whisper en la GPU (CUDA float16)...")
            # We use float16 on GPU for maximum speed, fallback to int8 if needed
            whisper_model = WhisperModel("base", device="cuda", compute_type="float16")
            print("[STT] Whisper cargado correctamente.")
        except Exception as e:
            print(f"[STT] Error cargando Whisper en GPU: {e}. Intentando en CPU...")
            try:
                whisper_model = WhisperModel("base", device="cpu", compute_type="int8")
                print("[STT] Whisper cargado en CPU.")
            except Exception as e2:
                print(f"[STT] Falló la carga de Whisper: {e2}")
                self.is_running = False
                return

        # 6. Calibrate noise floor
        # Change state to LISTENING briefly to show calibration starts
        self.gui.set_state("LISTENING")
        try:
            threshold = self.audio.calibrate_noise(duration=1.5)
        except Exception as e:
            print(f"[Audio] Error calibrando micrófono: {e}")
            threshold = 0.01
            
        # 7. Greet user on startup (Generated by LLM)
        print("[System] Generando saludo inicial con el LLM...")
        self.gui.set_state("THINKING")
        greeting_text = brain.get_response("Salúdeme con una única frase muy corta de bienvenida y reporte de sistemas, Señor.")
        print(f"[System] Saludo generado: '{greeting_text}'")
        self.gui.set_state("SPEAKING")
        # Read settings from GUI dynamically
        voice = self.gui.current_voice
        speed = self.gui.current_speed
        lang = "es" if voice.startswith("e") else "en-us"
        
        samples, sr = tts.speak(greeting_text, voice=voice, speed=speed, lang=lang)
        if samples is not None and self.is_running:
            self.audio.play_audio(samples, sr, self.gui.set_mouth_open_ratio, device=self.output_device)

        print("[System] ¡Asistente listo y escuchando!")
        self.gui.set_state("IDLE")

        # 9. Main interaction loop
        while self.is_running:
            try:
                # LISTENING
                # We pass a callback to immediately change face background color to LISTENING when speech is detected
                user_audio = self.audio.listen_for_speech(
                    threshold, 
                    on_speech_start=lambda: self.gui.set_state("LISTENING")
                )
                
                if not self.is_running:
                    break
                
                # THINKING (Transcribing)
                self.gui.set_state("THINKING")
                print("[STT] Procesando voz...")
                segments, info = whisper_model.transcribe(user_audio, beam_size=5, language="es")
                user_text = " ".join([segment.text for segment in segments]).strip()
                
                if not user_text:
                    print("[STT] No se detectó ninguna palabra. Volviendo a esperar.")
                    self.gui.set_state("IDLE")
                    time.sleep(0.5)
                    continue
                    
                print(f"[STT] Usuario dijo: '{user_text}'")
                
                # Check for exit commands
                if any(word in user_text.lower() for word in ["adiós", "salir", "chao", "apagar", "terminar"]):
                    self.gui.set_state("SPEAKING")
                    # Read settings from GUI dynamically
                    voice = self.gui.current_voice
                    speed = self.gui.current_speed
                    lang = "es" if voice.startswith("e") else "en-us"
                    
                    samples, sr = tts.speak("Desconectando sistemas. Hasta luego, Señor.", voice=voice, speed=speed, lang=lang)
                    if samples is not None:
                        self.audio.play_audio(samples, sr, self.gui.set_mouth_open_ratio, device=self.output_device)
                    self.gui.root.after(100, self.on_closing)
                    break
                
                # THINKING (LLM Response)
                print("[Brain] Consultando a Ollama...")
                reply_text = brain.get_response(user_text)
                print(f"[Brain] Réplica: '{reply_text}'")
                
                # THINKING (Generating voice)
                print("[TTS] Generando audio...")
                # Read settings from GUI dynamically
                voice = self.gui.current_voice
                speed = self.gui.current_speed
                lang = "es" if voice.startswith("e") else "en-us"
                
                samples, sr = tts.speak(reply_text, voice=voice, speed=speed, lang=lang)
                
                if not self.is_running:
                    break
                    
                # SPEAKING (Playback & Mouth-sync)
                if samples is not None:
                    self.gui.set_state("SPEAKING")
                    self.audio.play_audio(samples, sr, self.gui.set_mouth_open_ratio, device=self.output_device)
                else:
                    print("[TTS] Error generando audio, no se puede reproducir.")
                    
                # Back to IDLE
                self.gui.set_state("IDLE")
                time.sleep(0.3)
                
            except Exception as e:
                print(f"[System] Error en el bucle principal: {e}")
                self.gui.set_state("IDLE")
                time.sleep(1)

    def run(self):
        # Run GUI on main thread
        self.gui.run()

if __name__ == "__main__":
    app = AssistantApp()
    app.run()
