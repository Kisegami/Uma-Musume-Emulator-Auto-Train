import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
import json
import os
from datetime import datetime

# Import centralized font management
try:
    from .font_manager import get_font_manager, get_font
    from .font_config_editor import open_font_editor
except ImportError:
    from font_manager import get_font_manager, get_font
    from font_config_editor import open_font_editor

try:
    from .config_panel import ConfigPanel
    from .status_panel import StatusPanel
    from .log_panel import LogPanel
    from .bot_controller import BotController
except ImportError:
    from config_panel import ConfigPanel
    from status_panel import StatusPanel
    from log_panel import LogPanel
    from bot_controller import BotController

class MainWindow:
    def __init__(self, root):
        self.root = root
        self.root.title("Uma Musume Auto-Train Bot")
        self.root.geometry("1400x900")
        self.root.minsize(1200, 800)

        # Set customtkinter appearance mode and color theme
        ctk.set_appearance_mode("dark")  # "dark" or "light"
        ctk.set_default_color_theme("dark-blue")  # "blue", "green", "dark-blue"

        # Modern color scheme
        self.colors = {
            'bg_dark': '#212121',
            'bg_medium': '#2b2b2b',
            'bg_light': '#3c3c3c',
            'text_light': '#ffffff',
            'text_gray': '#b0b0b0',
            'accent_blue': '#1f538d',
            'accent_green': '#2d5a27',
            'accent_red': '#8b2635',
            'accent_yellow': '#8b6914',
            'border': '#3c3c3c'
        }

        # Configure root window
        self.root.configure(bg=self.colors['bg_dark'])
        
        # Bot control variables
        self.bot_running = False
        self.config_file = "config.json"
        
        # Auto-save configuration
        self.auto_save_enabled = True
        self.auto_save_delay = 1000  # 1 second delay after last change
        self.auto_save_timer = None
        
        # Load configuration
        self.load_config()
        
        # Create menu bar
        self.create_menu()
        
        # Create GUI components
        self.create_widgets()
        
        # Initialize bot controller
        self.bot_controller = BotController(self)
    
    def create_menu(self):
        """Create menu bar with font configuration option"""
        try:
            # Create menu bar
            menubar = tk.Menu(self.root, bg=self.colors['bg_medium'], fg=self.colors['text_light'])
            self.root.config(menu=menubar)
            
            # Settings menu
            settings_menu = tk.Menu(menubar, tearoff=0, bg=self.colors['bg_medium'], fg=self.colors['text_light'])
            menubar.add_cascade(label="Settings", menu=settings_menu)
            settings_menu.add_command(label="Font Configuration...", command=self.open_font_config)
            settings_menu.add_separator()
            settings_menu.add_command(label="Reload Fonts", command=self.reload_fonts)
            
        except Exception as e:
            print(f"Error creating menu: {e}")
    
    def open_font_config(self):
        """Open the font configuration editor"""
        try:
            open_font_editor(self.root)
        except Exception as e:
            self.add_log(f"Error opening font editor: {e}", "error")
    
    def reload_fonts(self):
        """Reload font configuration"""
        try:
            from font_manager import reload_fonts
            reload_fonts()
            self.add_log("Font configuration reloaded", "success")
        except Exception as e:
            self.add_log(f"Error reloading fonts: {e}", "error")

    def create_widgets(self):
        """Create the main layout with three main panels using modern customtkinter"""
        # Main container with dark background
        main_frame = ctk.CTkFrame(self.root, fg_color=self.colors['bg_dark'], corner_radius=0)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Configure grid layout
        main_frame.grid_columnconfigure(0, weight=5, minsize=800)  # Left column - give much more space to config + status
        main_frame.grid_columnconfigure(1, weight=2, minsize=200, pad=0)  # Right column - significantly reduce log panel size
        main_frame.grid_rowconfigure(0, weight=1)
        
        # Left side container - Config and Status
        left_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        left_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        left_frame.grid_columnconfigure(0, weight=1, minsize=800)  # Force minimum width
        left_frame.grid_rowconfigure(0, weight=2)  # Config takes more space
        left_frame.grid_rowconfigure(1, weight=1)  # Status takes less space
        
        # Top left - Config Panel (Beautiful rounded rectangle)
        self.config_panel = ConfigPanel(left_frame, self, self.colors)
        self.config_panel.grid(row=0, column=0, sticky="nsew", pady=(0, 15))
        
        # Bottom left - Status Panel (Beautiful rounded rectangle)
        self.status_panel = StatusPanel(left_frame, self, self.colors)
        self.status_panel.grid(row=1, column=0, sticky="nsew")
        
        # Right side - Log Panel (Beautiful rounded rectangle)
        self.log_panel = LogPanel(main_frame, self, self.colors)
        self.log_panel.grid(row=0, column=1, sticky="nsew")
        
        # Add initial log message
        self.add_log("Modern GUI initialized successfully")
        self.add_log(f"Configuration loaded from: {self.config_file}")
    
    def load_config(self):
        """Load configuration from file"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    self.config = json.load(f)
            else:
                # Load example config if main config doesn't exist
                if os.path.exists('config.example.json'):
                    with open('config.example.json', 'r', encoding='utf-8') as f:
                        self.config = json.load(f)
                    # Save as main config
                    self.save_config()
                else:
                    self.config = self.get_default_config()
                    self.save_config()
        except Exception as e:
            self.add_log(f"Error loading config: {e}")
            self.config = self.get_default_config()
    
    def get_default_config(self):
        """Get default configuration"""
        return {
            "priority_stat": ["spd", "sta", "wit", "pwr", "guts"],
            "minimum_mood": "GREAT",
            "maximum_failure": 15,
            "strategy": "PACE",

            "retry_race": True,
            "skill_point_cap": 400,
            "skill_purchase": "auto",
            "skill_file": "skills_example.json",
            "enable_skill_point_check": True,
            "min_energy": 30,
            "min_score": 1.0,
            "min_wit_score": 1.0,
            "do_race_when_bad_training": True,
            "stat_caps": {
                "spd": 1100,
                "sta": 1100,
                "pwr": 600,
                "guts": 600,
                "wit": 600
            },
            "capture_method": "adb",
            "adb_config": {
                "device_address": "127.0.0.1:7555",
                "adb_path": "adb",
                "screenshot_timeout": 5,
                "input_delay": 0.5,
                "connection_timeout": 10
            },
            "nemu_ipc_config": {
                "nemu_folder": "J:\\MuMuPlayerGlobal",
                "instance_id": 2,
                "display_id": 0,
                "timeout": 1.0
            },
            "ldopengl_config": {
                "ld_folder": "J:\\LDPlayer\\LDPlayer9",
                "instance_id": 0,
                "orientation": 0
            },
            "debug_mode": False
        }
    
    def save_config(self):
        """Save configuration to file"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            self.add_log(f"Configuration saved to {self.config_file}")
        except Exception as e:
            self.add_log(f"Error saving config: {e}")
    
    def schedule_auto_save(self):
        """Schedule an auto-save after a delay"""
        if not self.auto_save_enabled:
            return
            
        # Cancel any existing timer
        if self.auto_save_timer:
            self.root.after_cancel(self.auto_save_timer)
        
        # Schedule new auto-save
        self.auto_save_timer = self.root.after(self.auto_save_delay, self.auto_save)
    
    def auto_save(self):
        """Perform automatic save without showing success message"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            self.add_log("Configuration auto-saved", "info")
        except Exception as e:
            self.add_log(f"Error auto-saving config: {e}", "error")
        finally:
            self.auto_save_timer = None
    

    

    

    
    def update_status(self, year, energy, turn, mood, goal_met, stats):
        """Update the status panel with real-time data"""
        self.status_panel.update_status(year, energy, turn, mood, goal_met, stats)
    
    def start_bot(self):
        """Start the bot automation"""
        if hasattr(self, 'bot_controller'):
            self.bot_controller.start_bot()
            self.bot_running = True
            # Update log panel button
            if hasattr(self, 'log_panel'):
                self.log_panel.update_start_stop_button(True)
    
    def stop_bot(self):
        """Stop the bot automation"""
        if hasattr(self, 'bot_controller'):
            self.bot_controller.stop_bot()
            self.bot_running = False
            # Update log panel button
            if hasattr(self, 'log_panel'):
                self.log_panel.update_start_stop_button(False)
    
    def add_log(self, message, level="info"):
        """Add a log message to the queue"""
        if hasattr(self, 'log_panel'):
            self.log_panel.add_log_entry(message, level)
    
    def get_config(self):
        """Get current configuration"""
        return self.config
    
    def set_config(self, new_config):
        """Update configuration"""
        self.config = new_config
        self.schedule_auto_save()
        self.config_panel.refresh_config()
    
    def update_config_value(self, key, value):
        """Update a single configuration value and trigger auto-save"""
        self.config[key] = value
        self.schedule_auto_save()
    
    def update_nested_config_value(self, parent_key, child_key, value):
        """Update a nested configuration value and trigger auto-save"""
        if parent_key not in self.config:
            self.config[parent_key] = {}
        self.config[parent_key][child_key] = value
        self.schedule_auto_save()

def main():
    """Main function to run the modern GUI"""
    root = ctk.CTk()
    root.title("Uma Musume Auto-Train Bot")
    app = MainWindow(root)
    
    # Handle window close
    def on_closing():
        if app.bot_running:
            if messagebox.askokcancel("Quit", "Bot is running. Do you want to stop it and quit?"):
                app.stop_bot()
                root.destroy()
            else:
                return
        else:
            root.destroy()
    
    root.protocol("WM_DELETE_WINDOW", on_closing)
    
    # Center window
    root.update_idletasks()
    x = (root.winfo_screenwidth() // 2) - (root.winfo_width() // 2)
    y = (root.winfo_screenheight() // 2) - (root.winfo_height() // 2)
    root.geometry(f"+{x}+{y}")
    
    root.mainloop()

if __name__ == "__main__":
    main()
