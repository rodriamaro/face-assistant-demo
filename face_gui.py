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
        
        # Color definitions for states (Nick Jr. style but stylized)
        self.colors = {
            "IDLE": "#1a365d",       # Dark slate blue
            "LISTENING": "#c05621",  # Dark orange
            "THINKING": "#553c9a",   # Dark purple
            "SPEAKING": "#22543d"    # Dark forest green
        }
        
        # Canvas setup (fixed at top, height 600)
        # Using standard tk.Canvas for precise pixel/vector drawing
        self.canvas = tk.Canvas(self.root, width=600, height=600, highlightthickness=0)
        self.canvas.pack(fill="x", side="top")
        
        # Bottom controls frame (Modern CTkFrame)
        self.control_frame = ctk.CTkFrame(self.root, fg_color="#1e293b", corner_radius=15)
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
            dropdown_fg_color="#1e293b",
            dropdown_hover_color="#334155",
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
            fg_color="#475569",
            progress_color="#3b82f6",
            button_color="#3b82f6",
            button_hover_color="#1d4ed8"
        )
        self.speed_slider.set(1.1)
        self.speed_slider.grid(row=0, column=3, padx=5, pady=20, sticky="we")
        self.speed_val_lbl.grid(row=0, column=4, padx=5, pady=20, sticky="w")
        
        # Positions for Face features
        self.eye_left_center = (200, 220)
        self.eye_right_center = (400, 220)
        self.nose_center = (300, 330)
        self.mouth_center = (300, 440)
        
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
        if state in self.colors:
            self.state = state
            
    def set_mouth_open_ratio(self, ratio):
        self.mouth_open_ratio = ratio

    def draw_face(self):
        # Clear canvas
        self.canvas.delete("all")
        
        # Set background color based on state
        bg_color = self.colors[self.state]
        self.canvas.configure(bg=bg_color)
        
        # 1. DRAW EYEBROWS (Cejas)
        self.draw_eyebrows()
        
        # 2. DRAW EYES (Ojos)
        self.draw_eyes()
        
        # 3. DRAW NOSE (Nariz)
        self.canvas.create_oval(
            self.nose_center[0] - 25, self.nose_center[1] - 20,
            self.nose_center[0] + 25, self.nose_center[1] + 20,
            fill="#f1c40f", outline="#e67e22", width=3
        )
        
        # 4. DRAW MOUTH (Boca)
        self.draw_mouth()

    def draw_eyes(self):
        eye_w, eye_h = 90, 110
        pupil_r = 20
        
        if self.blink_active:
            # Left Eye closed
            self.canvas.create_line(
                self.eye_left_center[0] - 45, self.eye_left_center[1],
                self.eye_left_center[0] + 45, self.eye_left_center[1],
                fill="black", width=6, capstyle="round"
            )
            # Right Eye closed
            self.canvas.create_line(
                self.eye_right_center[0] - 45, self.eye_right_center[1],
                self.eye_right_center[0] + 45, self.eye_right_center[1],
                fill="black", width=6, capstyle="round"
            )
            return

        # Left Eye White
        self.canvas.create_oval(
            self.eye_left_center[0] - eye_w/2, self.eye_left_center[1] - eye_h/2,
            self.eye_left_center[0] + eye_w/2, self.eye_left_center[1] + eye_h/2,
            fill="white", outline="black", width=4
        )
        # Right Eye White
        self.canvas.create_oval(
            self.eye_right_center[0] - eye_w/2, self.eye_right_center[1] - eye_h/2,
            self.eye_right_center[0] + eye_w/2, self.eye_right_center[1] + eye_h/2,
            fill="white", outline="black", width=4
        )
        
        max_pupil_offset = 12
        px_left = self.eye_left_center[0] + self.look_offset_x * max_pupil_offset
        py_left = self.eye_left_center[1] + self.look_offset_y * max_pupil_offset
        px_right = self.eye_right_center[0] + self.look_offset_x * max_pupil_offset
        py_right = self.eye_right_center[1] + self.look_offset_y * max_pupil_offset
        
        # Left Pupil
        self.canvas.create_oval(
            px_left - pupil_r, py_left - pupil_r,
            px_left + pupil_r, py_right + pupil_r,
            fill="black", outline=""
        )
        # Right Pupil
        self.canvas.create_oval(
            px_right - pupil_r, py_right - pupil_r,
            px_right + pupil_r, py_right + pupil_r,
            fill="black", outline=""
        )

    def draw_eyebrows(self):
        y_offset = -75
        left_eb_x1 = self.eye_left_center[0] - 50
        left_eb_y1 = self.eye_left_center[1] + y_offset
        left_eb_x2 = self.eye_left_center[0] + 50
        left_eb_y2 = self.eye_left_center[1] + y_offset
        
        right_eb_x1 = self.eye_right_center[0] - 50
        right_eb_y1 = self.eye_right_center[1] + y_offset
        right_eb_x2 = self.eye_right_center[0] + 50
        right_eb_y2 = self.eye_right_center[1] + y_offset
        
        if self.state == "LISTENING":
            left_eb_y1 -= 15
            left_eb_y2 -= 15
            right_eb_y1 -= 15
            right_eb_y2 -= 15
        elif self.state == "THINKING":
            left_eb_y1 += 5
            left_eb_y2 -= 15
            right_eb_y1 -= 15
            right_eb_y2 += 5
        elif self.state == "SPEAKING":
            bounce = math.sin(time.time() * 15) * 5
            left_eb_y1 += bounce
            left_eb_y2 += bounce
            right_eb_y1 += bounce
            right_eb_y2 += bounce

        # Draw left eyebrow
        self.canvas.create_line(
            left_eb_x1, left_eb_y1, left_eb_x2, left_eb_y2,
            fill="black", width=8, capstyle="round"
        )
        # Draw right eyebrow
        self.canvas.create_line(
            right_eb_x1, right_eb_y1, right_eb_x2, right_eb_y2,
            fill="black", width=8, capstyle="round"
        )

    def draw_mouth(self):
        cx, cy = self.mouth_center
        
        if self.state == "LISTENING":
            self.canvas.create_arc(
                cx - 60, cy - 20, cx + 60, cy + 20,
                start=180, extent=180, fill="black", outline=""
            )
        elif self.state == "THINKING":
            self.canvas.create_oval(
                cx - 20, cy - 20, cx + 20, cy + 20,
                fill="black", outline=""
            )
        elif self.state == "SPEAKING":
            m_width = 120 - (self.mouth_open_ratio * 20)
            m_height = 10 + (self.mouth_open_ratio * 100)
            self.canvas.create_oval(
                cx - m_width/2, cy - m_height/2,
                cx + m_width/2, cy + m_height/2,
                fill="black", outline=""
            )
        else:  # IDLE
            self.canvas.create_arc(
                cx - 70, cy - 30, cx + 70, cy + 20,
                start=180, extent=180, fill="black", outline=""
            )

    def update_loop(self):
        self.blink_timer += 1
        if not self.blink_active:
            if self.blink_timer > random.randint(120, 360):
                self.blink_active = True
                self.blink_timer = 0
        else:
            if self.blink_timer > 8:
                self.blink_active = False
                self.blink_timer = 0
                
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
