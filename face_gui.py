import tkinter as tk
import customtkinter as ctk
import math
import random
import time

# Configure customtkinter appearance
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class FaceGUI:
    def __init__(self):
        self.root = ctk.CTk()
        self.root.title("J.A.R.V.I.S. - Asistente")
        self.root.geometry("600x700")
        self.root.resizable(False, False)
        
        # State variables
        self.state = "IDLE"  # IDLE, LISTENING, THINKING, SPEAKING
        self.mouth_open_ratio = 0.0  # 0.0 to 1.0 (controlled by audio playback)
        
        # Dynamic voice settings
        self.current_voice = "em_alex"
        self.current_speed = 1.1
        
        # Stylized Cyberpunk colors for each state
        # Contains: (Background Color, Primary Glow Color, Faint Grid Color)
        self.state_themes = {
            "IDLE": ("#060b13", "#3b82f6", "#111a2e"),       # Neon Blue / Deep Slate
            "LISTENING": ("#150c05", "#f97316", "#2c170a"),  # Neon Orange / Dark Copper
            "THINKING": ("#0f071b", "#a855f7", "#22113a"),   # Neon Purple / Dark Indigo
            "SPEAKING": ("#021315", "#06b6d4", "#0b2a2e")    # Neon Cyan / Dark Teal
        }
        
        # Canvas setup (fixed at top, height 600)
        self.canvas = tk.Canvas(self.root, width=600, height=600, highlightthickness=0)
        self.canvas.pack(fill="x", side="top")
        
        # Bottom controls frame (Modern CTkFrame)
        self.control_frame = ctk.CTkFrame(self.root, fg_color="#0f172a", corner_radius=15)
        self.control_frame.pack(fill="both", side="bottom", expand=True, padx=15, pady=15)
        
        # Configure layout grids
        self.control_frame.columnconfigure(0, weight=1)
        self.control_frame.columnconfigure(1, weight=2)
        self.control_frame.columnconfigure(2, weight=1)
        self.control_frame.columnconfigure(3, weight=2)
        self.control_frame.columnconfigure(4, weight=1)
        
        # 1. Voice Dropdown (CTkOptionMenu)
        lbl_voice = ctk.CTkLabel(self.control_frame, text="Voz:", font=("Arial", 12, "bold"), text_color="white")
        lbl_voice.grid(row=0, column=0, padx=10, pady=20, sticky="e")
        
        self.voice_map = {
            "Jarvis (Español M)": "em_alex",
            "Dora (Español F)": "ef_dora",
            "Santa (Español M)": "em_santa",
            "Sarah (Inglés F)": "af_sarah",
            "Lewis (Inglés M)": "bm_lewis"
        }
        
        voice_options = list(self.voice_map.keys())
        self.voice_menu = ctk.CTkOptionMenu(
            self.control_frame, 
            values=voice_options, 
            command=self.on_voice_changed,
            fg_color="#3b82f6",
            button_color="#2563eb",
            button_hover_color="#1d4ed8",
            dropdown_fg_color="#0f172a",
            dropdown_hover_color="#1e293b",
            width=160
        )
        self.voice_menu.set("Jarvis (Español M)")
        self.voice_menu.grid(row=0, column=1, padx=5, pady=20, sticky="w")
        
        # 2. Speed Slider (CTkSlider)
        lbl_speed = ctk.CTkLabel(self.control_frame, text="Velocidad:", font=("Arial", 12, "bold"), text_color="white")
        lbl_speed.grid(row=0, column=2, padx=10, pady=20, sticky="e")
        
        self.speed_val_lbl = ctk.CTkLabel(self.control_frame, text="1.1x", font=("Arial", 12, "bold"), text_color="#60a5fa", width=40)
        
        self.speed_slider = ctk.CTkSlider(
            self.control_frame, 
            from_=0.8, 
            to=2.0, 
            number_of_steps=12,
            command=self.on_speed_changed,
            fg_color="#334155",
            progress_color="#3b82f6",
            button_color="#3b82f6",
            button_hover_color="#1d4ed8"
        )
        self.speed_slider.set(1.1)
        self.speed_slider.grid(row=0, column=3, padx=5, pady=20, sticky="we")
        self.speed_val_lbl.grid(row=0, column=4, padx=5, pady=20, sticky="w")
        
        # Centers for Hologram Face drawing
        self.face_center = (300, 300)
        self.eye_left_center = (235, 260)
        self.eye_right_center = (365, 260)
        self.mouth_center = (300, 385)
        
        # Animation variables
        self.blink_active = False
        self.blink_timer = 0
        self.look_offset_x = 0
        self.look_offset_y = 0
        self.look_timer = 0
        
        # Create initial drawings
        self.draw_face()
        
        # Start update loop (60 FPS / ~16ms)
        self.update_loop()
        
    def set_state(self, state):
        if state in self.state_themes:
            self.state = state
            
    def set_mouth_open_ratio(self, ratio):
        self.mouth_open_ratio = ratio

    def draw_face(self):
        # Clear canvas
        self.canvas.delete("all")
        
        # Extract theme colors for the current state
        bg_color, glow_color, grid_color = self.state_themes[self.state]
        self.canvas.configure(bg=bg_color)
        
        # 1. DRAW TECH BACKGROUND GRID
        # Vertical lines
        for x in range(0, 600, 40):
            self.canvas.create_line(x, 0, x, 600, fill=grid_color, width=1)
        # Horizontal lines
        for y in range(0, 600, 40):
            self.canvas.create_line(0, y, 600, y, fill=grid_color, width=1)
            
        # 2. DRAW CENTRAL HOLOGRAM RINGS (Double Ring)
        cx, cy = self.face_center
        # Outer ring
        self.canvas.create_oval(
            cx - 165, cy - 165, cx + 165, cy + 165,
            outline=glow_color, width=3
        )
        # Inner dashed/thin ring
        self.canvas.create_oval(
            cx - 150, cy - 150, cx + 150, cy + 150,
            outline=glow_color, width=1, dash=(8, 6)
        )
        
        # 3. DRAW GLOWING EYES
        self.draw_eyes(glow_color)
        
        # 4. DRAW CIRCULAR WAVEFORM MOUTH
        self.draw_mouth(glow_color)

    def draw_eyes(self, glow_color):
        eye_r = 18
        
        # Calculate pupil/eye shift
        px_left = self.eye_left_center[0] + self.look_offset_x * 8
        py_left = self.eye_left_center[1] + self.look_offset_y * 8
        px_right = self.eye_right_center[0] + self.look_offset_x * 8
        py_right = self.eye_right_center[1] + self.look_offset_y * 8
        
        if self.blink_active:
            # Draw horizontal glowing lines when blinking
            self.canvas.create_line(
                px_left - 20, py_left, px_left + 20, py_left,
                fill=glow_color, width=4, capstyle="round"
            )
            self.canvas.create_line(
                px_right - 20, py_right, px_right + 20, py_right,
                fill=glow_color, width=4, capstyle="round"
            )
            return

        # Left Eye (White filled with neon glow outline)
        self.canvas.create_oval(
            px_left - eye_r, py_left - eye_r,
            px_left + eye_r, py_left + eye_r,
            fill="#ffffff", outline=glow_color, width=3
        )
        # Right Eye
        self.canvas.create_oval(
            px_right - eye_r, py_right - eye_r,
            px_right + eye_r, py_right + eye_r,
            fill="#ffffff", outline=glow_color, width=3
        )

    def draw_mouth(self, glow_color):
        cx, cy = self.mouth_center
        
        if self.state == "SPEAKING":
            # Circular Audio Waveform: Draw radiating spokes around a circle
            base_radius = 35
            num_spokes = 24
            max_spoke_len = 45
            
            # Draw the base circle
            self.canvas.create_oval(
                cx - base_radius, cy - base_radius,
                cx + base_radius, cy + base_radius,
                outline=glow_color, width=2
            )
            
            # Draw the glowing frequency spokes
            for i in range(num_spokes):
                angle = i * (2 * math.pi / num_spokes)
                # Randomize spoke height based on volume ratio to simulate sound waves
                spoke_len = self.mouth_open_ratio * max_spoke_len * random.uniform(0.3, 1.1)
                
                # Math coordinates for inner and outer points of the spoke
                x_inner = cx + base_radius * math.cos(angle)
                y_inner = cy + base_radius * math.sin(angle)
                x_outer = cx + (base_radius + spoke_len) * math.cos(angle)
                y_outer = cy + (base_radius + spoke_len) * math.sin(angle)
                
                self.canvas.create_line(
                    x_inner, y_inner, x_outer, y_outer,
                    fill=glow_color, width=3, capstyle="round"
                )
        elif self.state == "THINKING":
            # Pulsating circle indicating computation
            pulse = math.sin(time.time() * 8) * 5
            radius = 30 + pulse
            self.canvas.create_oval(
                cx - radius, cy - radius,
                cx + radius, cy + radius,
                outline=glow_color, width=2, dash=(6, 4)
            )
        elif self.state == "LISTENING":
            # Small, solid alert dot waiting for audio input
            radius = 12
            self.canvas.create_oval(
                cx - radius, cy - radius,
                cx + radius, cy + radius,
                fill=glow_color, outline=""
            )
        else:  # IDLE
            # Normal resting circle
            radius = 30
            self.canvas.create_oval(
                cx - radius, cy - radius,
                cx + radius, cy + radius,
                outline=glow_color, width=2
            )

    def update_loop(self):
        # Blinking logic
        self.blink_timer += 1
        if not self.blink_active:
            if self.blink_timer > random.randint(120, 360):
                self.blink_active = True
                self.blink_timer = 0
        else:
            if self.blink_timer > 8:
                self.blink_active = False
                self.blink_timer = 0
                
        # Look around logic (IDLE and THINKING only)
        self.look_timer += 1
        if self.state == "THINKING":
            self.look_offset_x = math.sin(time.time() * 3) * 0.8
            self.look_offset_y = -0.7
        elif self.state == "IDLE":
            if self.look_timer > random.randint(150, 400):
                self.look_offset_x = random.uniform(-0.6, 0.6)
                self.look_offset_y = random.uniform(-0.3, 0.3)
                self.look_timer = 0
        else:
            self.look_offset_x = 0
            self.look_offset_y = 0

        self.draw_face()
        self.root.after(16, self.update_loop)

    def on_voice_changed(self, choice):
        self.current_voice = self.voice_map.get(choice, "em_alex")
        print(f"[GUI] Voz cambiada a: {self.current_voice} ({choice})")
        
    def on_speed_changed(self, val):
        speed = float(val)
        self.current_speed = round(speed, 1)
        self.speed_val_lbl.configure(text=f"{self.current_speed:.1f}x")

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = FaceGUI()
    app.run()
