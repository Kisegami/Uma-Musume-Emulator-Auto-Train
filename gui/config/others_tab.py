"""
Others Tab for Uma Musume Auto-Train Bot GUI Configuration

Contains debug settings and other miscellaneous configuration options.
"""

import customtkinter as ctk
import tkinter as tk

try:
    from .base_tab import BaseTab
except ImportError:
    from base_tab import BaseTab

class OthersTab(BaseTab):
    """Others configuration tab containing debug and miscellaneous settings"""
    
    def __init__(self, tabview, config_panel, colors):
        """Initialize the Others tab"""
        super().__init__(tabview, config_panel, colors, "Others")
    
    def create_tab(self):
        """Create the Others tab"""
        # Add tab to tabview
        others_tab = self.tabview.add("Others")
        
        # Create scrollable content
        others_scroll = self.create_scrollable_content(others_tab)
        
        config = self.main_window.get_config()
        
        # Debug Mode Section
        self._create_debug_section(others_scroll, config)
        
        # Auto-save info label
        self.create_autosave_info_label(others_scroll)
    
    def _create_debug_section(self, parent, config):
        """Create the debug settings section"""
        debug_frame, _ = self.create_section_frame(parent, "Debug Settings")
        
        self.debug_mode_var = tk.BooleanVar(value=config.get('debug_mode', False))
        self.add_variable_with_autosave('debug_mode', self.debug_mode_var)
        
        debug_checkbox = ctk.CTkCheckBox(debug_frame, text="Debug Mode", 
                                       variable=self.debug_mode_var, 
                                       text_color=self.colors['text_light'])
        debug_checkbox.pack(pady=(0, 15))
    
    def save_other_settings(self):
        """Save other settings to config"""
        try:
            config = self.main_window.get_config()
            
            # Update debug mode
            config['debug_mode'] = self.debug_mode_var.get()
            
            # Save to file
            self.main_window.set_config(config)
            messagebox.showinfo("Success", "Other settings saved successfully!")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save other settings: {e}")
    
    def update_config(self, config):
        """Update the config dictionary with current values"""
        config['debug_mode'] = self.debug_mode_var.get()
