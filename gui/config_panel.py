"""
Optimized Configuration Panel for Uma Musume Auto-Train Bot GUI

This module provides a modular configuration interface using separate tab modules.
Each configuration tab is implemented as a separate module for better maintainability.
"""

import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox

# Import centralized font management
try:
    from .font_manager import get_font_manager, get_font, get_font_tuple
except ImportError:
    from font_manager import get_font_manager, get_font, get_font_tuple

class ConfigPanel(ctk.CTkFrame):
    """Main configuration panel using modular tab architecture"""
    
    def __init__(self, parent, main_window, colors):
        """Initialize the configuration panel
        
        Args:
            parent: Parent widget
            main_window: Reference to the main window
            colors: Color scheme dictionary
        """
        super().__init__(parent, fg_color=colors['bg_medium'], corner_radius=15)
        self.main_window = main_window
        self.colors = colors

        # Title label
        title_label = ctk.CTkLabel(self, text="CONFIG", font=get_font('tab_title'), text_color=colors['text_light'])
        title_label.pack(pady=(15, 10))

        # Create tabview for different config sections (modern rounded tabs)
        self.tabview = ctk.CTkTabview(self, fg_color=colors['bg_light'], corner_radius=10)
        self.tabview.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 15))
        
        # Load modular tabs
        self._load_modular_tabs()
    
    def _load_modular_tabs(self):
        """Load all configuration tabs from modules"""
        try:
            from .config import MainTab, TrainingTab, RacingTab, EventTab, SkillTab, RestartTab, OthersTab
            
            # Initialize all tabs
            self._tabs = {
                'main': MainTab(self.tabview, self, self.colors),
                'training': TrainingTab(self.tabview, self, self.colors),
                'racing': RacingTab(self.tabview, self, self.colors),
                'event': EventTab(self.tabview, self, self.colors),
                'skill': SkillTab(self.tabview, self, self.colors),
                'restart': RestartTab(self.tabview, self, self.colors),
                'others': OthersTab(self.tabview, self, self.colors),
            }
            
            print("Successfully loaded all modular configuration tabs")
            
        except ImportError as e:
            print(f"Error importing modular tabs: {e}")
            raise RuntimeError("Failed to load modular configuration tabs. Please check that all tab modules are properly implemented.")
        except Exception as e:
            print(f"Error initializing modular tabs: {e}")
            raise RuntimeError(f"Failed to initialize modular configuration tabs: {e}")
    
    def get_tab(self, tab_name):
        """Get a reference to a specific tab
        
        Args:
            tab_name: Name of the tab ('main', 'training', 'racing', etc.)
            
        Returns:
            Tab instance or None if not found
        """
        return self._tabs.get(tab_name)
    
    def refresh_config(self):
        """Refresh the configuration display"""
        # This would update all displayed values when config changes
        # Individual tabs handle their own refresh logic
        print("Configuration refresh requested")
        
        # Refresh training score values if training tab exists
        if hasattr(self, '_tabs') and 'training' in self._tabs:
            training_tab = self._tabs['training']
            if hasattr(training_tab, 'refresh_training_score_values'):
                training_tab.refresh_training_score_values()
    
    def save_config(self):
        """Save the current configuration"""
        try:
            # Get current config
            config = self.main_window.get_config()
            
            # Main tab variables (these need to be accessible from main tab)
            if hasattr(self, 'device_address_var'):
                config['adb_config'] = {
                    'device_address': self.device_address_var.get(),
                    'adb_path': self.adb_path_var.get(),
                    'screenshot_timeout': self.screenshot_timeout_var.get(),
                    'input_delay': self.input_delay_var.get(),
                    'connection_timeout': self.connection_timeout_var.get()
                }

                # Capture method & settings
                config['capture_method'] = self.capture_method_var.get()
                config['nemu_ipc_config'] = {
                    'nemu_folder': self.nemu_folder_var.get(),
                    'instance_id': self.nemu_instance_var.get(),
                    'display_id': self.nemu_display_var.get(),
                    'timeout': self.nemu_timeout_var.get()
                }
                if hasattr(self, 'ldopengl_folder_var'):
                    config['ldopengl_config'] = {
                        'ld_folder': self.ldopengl_folder_var.get(),
                        'instance_id': self.ldopengl_instance_var.get(),
                        'orientation': self.ldopengl_orientation_var.get()
                    }
            
            # Debug mode (from others tab)
            if hasattr(self, 'debug_mode_var'):
                config['debug_mode'] = self.debug_mode_var.get()
            
            # Save to file
            self.main_window.set_config(config)
            messagebox.showinfo("Success", "Configuration saved successfully!")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save configuration: {e}")

    def toggle_capture_settings(self):
        """Show/hide capture method settings based on selected method"""
        if not hasattr(self, 'capture_method_var'):
            return
        
        method = self.capture_method_var.get()
        
        # Hide all settings frames first
        if hasattr(self, 'nemu_settings_frame'):
            self.nemu_settings_frame.pack_forget()
        if hasattr(self, 'ldopengl_settings_frame'):
            self.ldopengl_settings_frame.pack_forget()
        
        # Show appropriate settings frame
        if method == 'nemu_ipc' and hasattr(self, 'nemu_settings_frame'):
            self.nemu_settings_frame.pack(fill=tk.X, pady=(0, 10), padx=10)
        elif method == 'ldopengl' and hasattr(self, 'ldopengl_settings_frame'):
            self.ldopengl_settings_frame.pack(fill=tk.X, pady=(0, 10), padx=10)
    
    def toggle_nemu_settings(self):
        """Legacy method name - redirects to toggle_capture_settings"""
        self.toggle_capture_settings()
