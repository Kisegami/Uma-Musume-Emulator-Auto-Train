"""
Main Tab for Uma Musume Auto-Train Bot GUI Configuration

Contains ADB configuration and screenshot capture settings.
"""

import customtkinter as ctk
import tkinter as tk

try:
    from .base_tab import BaseTab
except ImportError:
    from base_tab import BaseTab

class MainTab(BaseTab):
    """Main configuration tab containing ADB and capture settings"""
    
    # Mode display labels mapping
    MODE_DISPLAY_LABELS = {
        "ura": "URA Finale",
        "unity": "Unity Cup"
    }
    MODE_VALUES = {
        "URA Finale": "ura",
        "Unity Cup": "unity"
    }
    
    def __init__(self, tabview, config_panel, colors):
        """Initialize the Main tab"""
        super().__init__(tabview, config_panel, colors, "Main")
    
    def create_tab(self):
        """Create the Main tab with ADB configuration"""
        # Add tab to tabview
        main_tab = self.tabview.add("Main")
        
        # Create scrollable content
        main_scroll = self.create_scrollable_content(main_tab)
        
        config = self.main_window.get_config()

        # Mode Configuration Section
        mode_frame, _ = self.create_section_frame(main_scroll, "Mode Configuration")
        
        # Mode selector with display labels
        mode_value = config.get('mode', 'ura')
        mode_display = self.MODE_DISPLAY_LABELS.get(mode_value, "URA Finale")
        self.config_panel.mode_var = tk.StringVar(value=mode_display)
        # Store actual mode value separately for saving
        self.config_panel._mode_actual_value = mode_value
        self.add_variable_with_autosave('mode', self.config_panel.mode_var)
        _, mode_combo = self.create_setting_row(mode_frame, "Mode:", 'optionmenu', 
                                               values=['URA Finale', 'Unity Cup'], 
                                               variable=self.config_panel.mode_var,
                                               command=lambda _: self.on_mode_change())

        # ADB Configuration Section
        adb_frame, _ = self.create_section_frame(main_scroll, "ADB Configuration")
        
        # Device Address
        self.config_panel.device_address_var = tk.StringVar(value=config.get('adb_config', {}).get('device_address', '127.0.0.1:7555'))
        self.add_variable_with_autosave('device_address', self.config_panel.device_address_var)
        _, device_entry = self.create_setting_row(adb_frame, "Device Address:", 'entry', textvariable=self.config_panel.device_address_var, width=200)
        
        # ADB Path
        self.config_panel.adb_path_var = tk.StringVar(value=config.get('adb_config', {}).get('adb_path', 'adb'))
        self.add_variable_with_autosave('adb_path', self.config_panel.adb_path_var)
        _, adb_path_entry = self.create_setting_row(adb_frame, "ADB Path:", 'entry', textvariable=self.config_panel.adb_path_var, width=200)
        
        # Advanced ADB settings (hidden from GUI, kept in config with defaults)
        # Screenshot Timeout
        self.config_panel.screenshot_timeout_var = tk.IntVar(value=config.get('adb_config', {}).get('screenshot_timeout', 5))
        # Input Delay
        self.config_panel.input_delay_var = tk.DoubleVar(value=config.get('adb_config', {}).get('input_delay', 0.0))
        # Connection Timeout
        self.config_panel.connection_timeout_var = tk.IntVar(value=config.get('adb_config', {}).get('connection_timeout', 10))

        # Capture Method Section
        capture_frame, _ = self.create_section_frame(main_scroll, "Screenshot Capture")

        # Method selector
        self.config_panel.capture_method_var = tk.StringVar(value=config.get('capture_method', 'adb'))
        self.add_variable_with_autosave('capture_method', self.config_panel.capture_method_var)
        _, method_combo = self.create_setting_row(capture_frame, "Method:", 'optionmenu', 
                                                 values=['adb', 'nemu_ipc', 'ldopengl'], 
                                                 variable=self.config_panel.capture_method_var,
                                                 command=lambda _: self.config_panel.toggle_capture_settings())

        # Nemu IPC settings (hidden unless selected)
        self.config_panel.nemu_settings_frame = ctk.CTkFrame(capture_frame, fg_color=self.colors['bg_light'], corner_radius=10)
        nemu_cfg = config.get('nemu_ipc_config', {})
        # Fields
        nemu_folder_row = ctk.CTkFrame(self.config_panel.nemu_settings_frame, fg_color="transparent")
        nemu_folder_row.pack(fill=tk.X, padx=15, pady=5)
        ctk.CTkLabel(nemu_folder_row, text="MuMu/Nemu Folder:", text_color=self.colors['text_light'], font=get_font('label')).pack(side=tk.LEFT)
        self.config_panel.nemu_folder_var = tk.StringVar(value=nemu_cfg.get('nemu_folder', 'J:\\MuMuPlayerGlobal'))
        self.add_variable_with_autosave('nemu_folder', self.config_panel.nemu_folder_var)
        ctk.CTkEntry(nemu_folder_row, textvariable=self.config_panel.nemu_folder_var, width=320, corner_radius=8, font=get_font('input')).pack(side=tk.RIGHT)

        instance_row = ctk.CTkFrame(self.config_panel.nemu_settings_frame, fg_color="transparent")
        instance_row.pack(fill=tk.X, padx=15, pady=5)
        ctk.CTkLabel(instance_row, text="Instance ID:", text_color=self.colors['text_light'], font=get_font('label')).pack(side=tk.LEFT)
        self.config_panel.nemu_instance_var = tk.IntVar(value=nemu_cfg.get('instance_id', 2))
        self.add_variable_with_autosave('nemu_instance', self.config_panel.nemu_instance_var)
        ctk.CTkEntry(instance_row, textvariable=self.config_panel.nemu_instance_var, width=100, corner_radius=8, font=get_font('input')).pack(side=tk.RIGHT)

        display_row = ctk.CTkFrame(self.config_panel.nemu_settings_frame, fg_color="transparent")
        display_row.pack(fill=tk.X, padx=15, pady=5)
        ctk.CTkLabel(display_row, text="Display ID:", text_color=self.colors['text_light'], font=get_font('label')).pack(side=tk.LEFT)
        self.config_panel.nemu_display_var = tk.IntVar(value=nemu_cfg.get('display_id', 0))
        self.add_variable_with_autosave('nemu_display', self.config_panel.nemu_display_var)
        ctk.CTkEntry(display_row, textvariable=self.config_panel.nemu_display_var, width=100, corner_radius=8, font=get_font('input')).pack(side=tk.RIGHT)

        timeout_row = ctk.CTkFrame(self.config_panel.nemu_settings_frame, fg_color="transparent")
        timeout_row.pack(fill=tk.X, padx=15, pady=(5, 15))
        ctk.CTkLabel(timeout_row, text="Timeout (s):", text_color=self.colors['text_light'], font=get_font('label')).pack(side=tk.LEFT)
        self.config_panel.nemu_timeout_var = tk.DoubleVar(value=nemu_cfg.get('timeout', 1.0))
        self.add_variable_with_autosave('nemu_timeout', self.config_panel.nemu_timeout_var)
        ctk.CTkEntry(timeout_row, textvariable=self.config_panel.nemu_timeout_var, width=100, corner_radius=8, font=get_font('input')).pack(side=tk.RIGHT)

        # LDOpenGL settings (hidden unless selected)
        self.config_panel.ldopengl_settings_frame = ctk.CTkFrame(capture_frame, fg_color=self.colors['bg_light'], corner_radius=10)
        ldopengl_cfg = config.get('ldopengl_config', {})
        # Fields
        ld_folder_row = ctk.CTkFrame(self.config_panel.ldopengl_settings_frame, fg_color="transparent")
        ld_folder_row.pack(fill=tk.X, padx=15, pady=5)
        ctk.CTkLabel(ld_folder_row, text="LDPlayer Folder:", text_color=self.colors['text_light'], font=get_font('label')).pack(side=tk.LEFT)
        self.config_panel.ldopengl_folder_var = tk.StringVar(value=ldopengl_cfg.get('ld_folder', 'J:\\LDPlayer\\LDPlayer9'))
        self.add_variable_with_autosave('ldopengl_folder', self.config_panel.ldopengl_folder_var)
        ctk.CTkEntry(ld_folder_row, textvariable=self.config_panel.ldopengl_folder_var, width=320, corner_radius=8, font=get_font('input')).pack(side=tk.RIGHT)

        ld_instance_row = ctk.CTkFrame(self.config_panel.ldopengl_settings_frame, fg_color="transparent")
        ld_instance_row.pack(fill=tk.X, padx=15, pady=5)
        ctk.CTkLabel(ld_instance_row, text="Instance ID:", text_color=self.colors['text_light'], font=get_font('label')).pack(side=tk.LEFT)
        self.config_panel.ldopengl_instance_var = tk.IntVar(value=ldopengl_cfg.get('instance_id', 0))
        self.add_variable_with_autosave('ldopengl_instance', self.config_panel.ldopengl_instance_var)
        ctk.CTkEntry(ld_instance_row, textvariable=self.config_panel.ldopengl_instance_var, width=100, corner_radius=8, font=get_font('input')).pack(side=tk.RIGHT)

        ld_orientation_row = ctk.CTkFrame(self.config_panel.ldopengl_settings_frame, fg_color="transparent")
        ld_orientation_row.pack(fill=tk.X, padx=15, pady=(5, 15))
        ctk.CTkLabel(ld_orientation_row, text="Orientation (0=normal, 2=upside down):", text_color=self.colors['text_light'], font=get_font('label')).pack(side=tk.LEFT)
        self.config_panel.ldopengl_orientation_var = tk.IntVar(value=ldopengl_cfg.get('orientation', 0))
        self.add_variable_with_autosave('ldopengl_orientation', self.config_panel.ldopengl_orientation_var)
        ctk.CTkEntry(ld_orientation_row, textvariable=self.config_panel.ldopengl_orientation_var, width=100, corner_radius=8, font=get_font('input')).pack(side=tk.RIGHT)

        # Initial visibility
        self.config_panel.toggle_capture_settings()
        
        # Auto-save info label
        self.create_autosave_info_label(main_scroll)
    
    def update_config(self, config):
        """Update the config dictionary with current values"""
        # Update ADB config
        config['adb_config'] = {
            'device_address': self.config_panel.device_address_var.get(),
            'adb_path': self.config_panel.adb_path_var.get(),
            'screenshot_timeout': self.config_panel.screenshot_timeout_var.get(),
            'input_delay': self.config_panel.input_delay_var.get(),
            'connection_timeout': self.config_panel.connection_timeout_var.get()
        }
        
        # Update capture method
        config['capture_method'] = self.config_panel.capture_method_var.get()
        
        # Update Nemu IPC config
        config['nemu_ipc_config'] = {
            'nemu_folder': self.config_panel.nemu_folder_var.get(),
            'instance_id': self.config_panel.nemu_instance_var.get(),
            'display_id': self.config_panel.nemu_display_var.get(),
            'timeout': self.config_panel.nemu_timeout_var.get()
        }
        
        # Update LDOpenGL config
        config['ldopengl_config'] = {
            'ld_folder': self.config_panel.ldopengl_folder_var.get(),
            'instance_id': self.config_panel.ldopengl_instance_var.get(),
            'orientation': self.config_panel.ldopengl_orientation_var.get()
        }
        
        # Update mode (convert display label to actual value)
        mode_display = self.config_panel.mode_var.get()
        mode_value = self.MODE_VALUES.get(mode_display, 'ura')
        config['mode'] = mode_value
        # Update stored actual value
        self.config_panel._mode_actual_value = mode_value
    
    def on_mode_change(self):
        """Handle mode change - update training tab visibility"""
        # Skip during initialization
        if getattr(self, '_initializing', False):
            return
        
        # Convert display label to actual value
        mode_display = self.config_panel.mode_var.get()
        mode_value = self.MODE_VALUES.get(mode_display, 'ura')
        self.config_panel._mode_actual_value = mode_value
        
        # Update config first
        try:
            config = self.main_window.get_config()
            self.update_config(config)
            self.main_window.set_config(config)
        except Exception as e:
            print(f"Error updating mode: {e}")
        
        # Notify training tab to update visibility
        training_tab = self.config_panel.get_tab('training')
        if training_tab and hasattr(training_tab, 'update_unity_fields_visibility'):
            training_tab.update_unity_fields_visibility()
