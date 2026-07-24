import sounddevice as sd
import numpy as np
import time
import queue

class AudioHandler:
    def __init__(self, samplerate=16000):
        self.samplerate = samplerate
        self.chunk_size = 512  # ~32ms chunk at 16kHz
        self.playback_chunk_size = 1024

    def calibrate_noise(self, duration=1.0):
        """
        Listens to the microphone for 'duration' seconds and calculates the noise floor.
        Returns: threshold (float) to separate speech from noise.
        """
        print("[Audio] Calibrando nivel de ruido ambiente... Por favor, mantente en silencio.")
        rms_values = []
        
        def callback(indata, frames, time, status):
            if status:
                print(status, flush=True)
            # Calculate RMS of the incoming chunk
            rms = np.sqrt(np.mean(indata**2))
            rms_values.append(rms)

        # Start input stream for calibration
        with sd.InputStream(samplerate=self.samplerate, channels=1, dtype='float32',
                            callback=callback, blocksize=self.chunk_size):
            time.sleep(duration)
            
        if not rms_values:
            # Fallback threshold if no frames captured
            return 0.02
            
        mean_rms = np.mean(rms_values)
        max_rms = np.max(rms_values)
        std_rms = np.std(rms_values)
        
        # Threshold: Mean + 4 standard deviations, or max * 1.5, whichever is higher
        threshold = max(mean_rms + 4 * std_rms, max_rms * 1.5)
        # Ensure a minimum threshold to prevent dead loops on absolute silence
        threshold = max(threshold, 0.005)
        
        print(f"[Audio] Calibración completa. Umbral de ruido: {threshold:.5f} (RMS promedio: {mean_rms:.5f})")
        return threshold

    def listen_for_speech(self, threshold, on_speech_start=None):
        """
        Listens to the microphone. When speech is detected, records until a silence is detected.
        Returns: 1D numpy array of float32 samples representing the speech.
        """
        print("[Audio] Escuchando...")
        audio_buffer = []
        speech_started = False
        silence_start_time = None
        silence_timeout = 1.5  # seconds of silence before we stop recording
        
        # Buffer to keep a small pre-roll (e.g., 0.3 seconds) so we don't lose the start of speech
        pre_roll_chunks = int(0.3 * self.samplerate / self.chunk_size)
        pre_roll_buffer = []

        q = queue.Queue()

        def callback(indata, frames, time, status):
            if status:
                print(status, flush=True)
            q.put(indata.copy())

        # Open stream
        with sd.InputStream(samplerate=self.samplerate, channels=1, dtype='float32',
                            callback=callback, blocksize=self.chunk_size):
            
            while True:
                try:
                    chunk = q.get(timeout=0.1)
                except queue.Empty:
                    continue
                
                rms = np.sqrt(np.mean(chunk**2))
                
                if not speech_started:
                    # Maintain pre-roll buffer
                    pre_roll_buffer.append(chunk)
                    if len(pre_roll_buffer) > pre_roll_chunks:
                        pre_roll_buffer.pop(0)
                        
                    if rms > threshold:
                        speech_started = True
                        print("[Audio] ¡Voz detectada! Grabando...")
                        if on_speech_start:
                            on_speech_start() # Trigger GUI change to LISTENING
                        # Start recording with pre-roll
                        for pr_chunk in pre_roll_buffer:
                            audio_buffer.extend(pr_chunk.flatten())
                else:
                    audio_buffer.extend(chunk.flatten())
                    
                    if rms < threshold:
                        if silence_start_time is None:
                            silence_start_time = time.time()
                        elif time.time() - silence_start_time > silence_timeout:
                            print("[Audio] Silencio detectado. Procesando audio...")
                            break
                    else:
                        silence_start_time = None # Reset silence timer if they speak again

        return np.array(audio_buffer, dtype=np.float32)

    def find_digital_output_device(self):
        """
        Scans available audio output devices and returns the index of the first one
        whose name contains 'digital' or 'iec958' or 'spdif'.
        Returns None if not found, which will fall back to default.
        """
        try:
            devices = sd.query_devices()
            for idx, dev in enumerate(devices):
                if dev['max_output_channels'] > 0:
                    name = dev['name']
                    # Look for digital outputs
                    if any(k in name.lower() for k in ["digital", "iec958", "spdif"]):
                        print(f"[Audio] Encontrada salida digital automática: Dispositivo {idx} ({name})")
                        return idx
        except Exception as e:
            print(f"[Audio] Error al escanear dispositivos de audio: {e}")
        return None

    def play_test_beep(self, device=None):
        """
        Generates and plays a 440 Hz test beep for 0.4 seconds at 48000 Hz.
        Useful for diagnosing output device and volume issues.
        """
        print("[Audio] Generando tono de prueba (440 Hz beep)...")
        fs = 48000
        duration = 0.4
        f = 440.0
        t = np.arange(int(fs * duration)) / fs
        samples = 0.25 * np.sin(2 * np.pi * f * t) # volume at 0.25
        self.play_audio(samples.astype(np.float32), fs, lambda r: None, device=device)


    def play_audio(self, audio_data, samplerate, gui_mouth_callback, device=None):
        """
        Plays audio samples chunk by chunk and sends the current mouth open ratio to the GUI.
        Converts mono audio to stereo and resamples to 48000 Hz for maximum compatibility with ALSA/Pipewire (specifically S/PDIF/digital outputs).
        """
        if audio_data is None or len(audio_data) == 0:
            return
            
        # Digital devices (HDMI, S/PDIF) often only support standard rates like 48000 Hz.
        # Kokoro TTS outputs at 24000 Hz. We resample to 48000 Hz to avoid PaErrorCode -9997.
        if samplerate != 48000:
            duration = len(audio_data) / samplerate
            new_num_samples = int(duration * 48000)
            x_old = np.linspace(0, duration, len(audio_data))
            x_new = np.linspace(0, duration, new_num_samples)
            audio_data = np.interp(x_new, x_old, audio_data).astype(np.float32)
            samplerate = 48000

        # Open a stereo stream (2 channels) for better Linux/ALSA/Pipewire compatibility
        try:
            stream = sd.OutputStream(samplerate=samplerate, channels=2, dtype='float32', device=device)
            with stream:
                for i in range(0, len(audio_data), self.playback_chunk_size):
                    chunk = audio_data[i : i + self.playback_chunk_size]
                    # Pad if it's the last chunk
                    if len(chunk) < self.playback_chunk_size:
                        chunk = np.pad(chunk, (0, self.playback_chunk_size - len(chunk)))
                    
                    # Compute RMS for lip sync
                    rms = np.sqrt(np.mean(chunk**2))
                    # Map RMS to a 0.0 - 1.0 ratio
                    ratio = min(rms * 6.0, 1.0)
                    gui_mouth_callback(ratio)
                    
                    # Convert mono chunk to stereo (left and right channels)
                    stereo_chunk = np.column_stack((chunk, chunk))
                    
                    # Play chunk
                    stream.write(stereo_chunk)
        except Exception as e:
            print(f"[Audio] Error en la reproducción de audio (¿dispositivo incorrecto?): {e}")
                
        # Reset mouth when finished
        gui_mouth_callback(0.0)
