"""
Restart Tab for Uma Musume Auto-Train Bot GUI Configuration

Contains restart conditions and career management settings.
"""

import customtkinter as ctk
import tkinter as tk

try:
    from .base_tab import BaseTab
except ImportError:
    from base_tab import BaseTab

class RestartTab(BaseTab):
    """Restart configuration tab containing restart career settings"""
    
    def __init__(self, tabview, config_panel, colors):
        """Initialize the Restart tab"""
        super().__init__(tabview, config_panel, colors, "Restart")
    
    def create_tab(self):
        """Create the Restart tab with restart career settings"""
        # Add tab to tabview
        restart_tab = self.tabview.add("Restart")
        
        # Create scrollable content
        restart_scroll = self.create_scrollable_content(restart_tab)
        
        config = self.main_window.get_config()
        
        # Restart Career Settings Section
        self._create_restart_settings_section(restart_scroll, config)
        
        # Legacy Settings Section
        self._create_legacy_settings_section(restart_scroll, config)
        
        # Support Settings Section
        self._create_support_settings_section(restart_scroll, config)
        
        # Auto-save info label
        self.create_autosave_info_label(restart_tab, {'side': tk.BOTTOM, 'pady': 20})
    
    def _create_restart_settings_section(self, parent, config):
        """Create the restart career settings section"""
        restart_frame = ctk.CTkFrame(parent, fg_color=self.colors['bg_light'], corner_radius=10)
        restart_frame.pack(fill=tk.X, pady=10, padx=10)
        
        restart_title = ctk.CTkLabel(restart_frame, text="Restart Career Settings", font=get_font('section_title'), text_color=self.colors['text_light'])
        restart_title.pack(pady=(15, 10))
        
        # Restart Career Run checkbox
        self.restart_enabled_var = tk.BooleanVar(value=config.get('restart_career', {}).get('restart_enabled', False))
        self.restart_enabled_var.trace('w', self.on_restart_setting_change)
        restart_checkbox = ctk.CTkCheckBox(restart_frame, text="Restart Career run", variable=self.restart_enabled_var, 
                                         text_color=self.colors['text_light'], font=get_font('checkbox'),
                                         command=self.toggle_restart_settings)
        restart_checkbox.pack(anchor=tk.W, pady=(0, 15))
        
        # Restart criteria frame (initially hidden if restart is disabled)
        self.restart_criteria_frame = ctk.CTkFrame(restart_frame, fg_color="transparent")
        if self.restart_enabled_var.get():
            self.restart_criteria_frame.pack(fill=tk.X, pady=5)
        
        # Restart criteria radio buttons
        self.restart_criteria_var = tk.StringVar(value="times")
        self.restart_criteria_var.trace('w', self.on_restart_setting_change)
        if config.get('restart_career', {}).get('total_fans_requirement', 0) > 0:
            self.restart_criteria_var.set("fans")
        else:
            self.restart_criteria_var.set("times")
        
        criteria_label = ctk.CTkLabel(self.restart_criteria_frame, text="Restart Criteria (choose one):", text_color=self.colors['text_light'])
        criteria_label.pack(anchor=tk.W, pady=(0, 10))
        
        # Times radio button and input
        times_frame = ctk.CTkFrame(self.restart_criteria_frame, fg_color="transparent")
        times_frame.pack(fill=tk.X, pady=5)
        times_radio = ctk.CTkRadioButton(times_frame, text="Restart career", variable=self.restart_criteria_var, value="times",
                                       text_color=self.colors['text_light'], font=get_font('radiobutton'),
                                       command=self.on_criteria_change)
        times_radio.pack(side=tk.LEFT)
        self.restart_times_var = tk.IntVar(value=config.get('restart_career', {}).get('restart_times', 5))
        self.restart_times_var.trace('w', self.on_restart_setting_change)
        times_entry = ctk.CTkEntry(times_frame, textvariable=self.restart_times_var, width=80, corner_radius=8)
        times_entry.pack(side=tk.LEFT, padx=(10, 0))
        times_label = ctk.CTkLabel(times_frame, text="times", text_color=self.colors['text_light'])
        times_label.pack(side=tk.LEFT, padx=(5, 0))
        
        # Fans radio button and input
        fans_frame = ctk.CTkFrame(self.restart_criteria_frame, fg_color="transparent")
        fans_frame.pack(fill=tk.X, pady=5)
        fans_radio = ctk.CTkRadioButton(fans_frame, text="Run until achieve", variable=self.restart_criteria_var, value="fans",
                                      text_color=self.colors['text_light'], font=get_font('radiobutton'),
                                      command=self.on_criteria_change)
        fans_radio.pack(side=tk.LEFT)
        self.total_fans_requirement_var = tk.IntVar(value=config.get('restart_career', {}).get('total_fans_requirement', 0))
        self.total_fans_requirement_var.trace('w', self.on_restart_setting_change)
        fans_entry = ctk.CTkEntry(fans_frame, textvariable=self.total_fans_requirement_var, width=80, corner_radius=8)
        fans_entry.pack(side=tk.LEFT, padx=(10, 0))
        fans_label = ctk.CTkLabel(fans_frame, text="fans", text_color=self.colors['text_light'])
        fans_label.pack(side=tk.LEFT, padx=(5, 0))
    
    def _create_legacy_settings_section(self, parent, config):
        """Create the legacy settings section"""
        self.legacy_frame = ctk.CTkFrame(parent, fg_color=self.colors['bg_light'], corner_radius=10)
        if self.restart_enabled_var.get():
            self.legacy_frame.pack(fill=tk.X, pady=10, padx=10)
        
        legacy_title = ctk.CTkLabel(self.legacy_frame, text="Legacy Settings", font=get_font('section_title'), text_color=self.colors['text_light'])
        legacy_title.pack(pady=(15, 10))
        
        # Include Legacy from Guests checkbox
        self.include_guests_legacy_var = tk.BooleanVar(value=config.get('auto_start_career', {}).get('include_guests_legacy', False))
        self.include_guests_legacy_var.trace('w', self.on_restart_setting_change)
        legacy_checkbox = ctk.CTkCheckBox(self.legacy_frame, text="Include Legacy from Guests", variable=self.include_guests_legacy_var, 
                                        text_color=self.colors['text_light'], font=get_font('checkbox'))
        legacy_checkbox.pack(anchor=tk.W, pady=(0, 15))
    
    def _create_support_settings_section(self, parent, config):
        """Create the support settings section"""
        self.support_frame = ctk.CTkFrame(parent, fg_color=self.colors['bg_light'], corner_radius=10)
        if self.restart_enabled_var.get():
            self.support_frame.pack(fill=tk.X, pady=10, padx=10)
        
        support_title = ctk.CTkLabel(self.support_frame, text="Support Settings (Note: Only choose followed player support)", 
                                   font=get_font('section_title'), text_color=self.colors['text_light'])
        support_title.pack(pady=(15, 10))
        
        # Support Speciality
        speciality_frame = ctk.CTkFrame(self.support_frame, fg_color="transparent")
        speciality_frame.pack(fill=tk.X, padx=15, pady=5)
        ctk.CTkLabel(speciality_frame, text="Support Speciality:", text_color=self.colors['text_light'], font=get_font('label')).pack(side=tk.LEFT)
        self.support_speciality_var = tk.StringVar(value=config.get('auto_start_career', {}).get('support_speciality', 'STA'))
        self.support_speciality_var.trace('w', self.on_restart_setting_change)
        speciality_combo = ctk.CTkOptionMenu(speciality_frame, values=['SPD', 'STA', 'PWR', 'GUTS', 'WIT', 'PAL'], 
                                           variable=self.support_speciality_var, fg_color=self.colors['accent_blue'], 
                                           corner_radius=8, button_color=self.colors['accent_blue'],
                                           button_hover_color=self.colors['accent_green'])
        speciality_combo.pack(side=tk.RIGHT)
        
        # Support Rarity
        rarity_frame = ctk.CTkFrame(self.support_frame, fg_color="transparent")
        rarity_frame.pack(fill=tk.X, padx=15, pady=5)
        ctk.CTkLabel(rarity_frame, text="Support Rarity:", text_color=self.colors['text_light'], font=get_font('label')).pack(side=tk.LEFT)
        self.support_rarity_var = tk.StringVar(value=config.get('auto_start_career', {}).get('support_rarity', 'SSR'))
        self.support_rarity_var.trace('w', self.on_restart_setting_change)
        rarity_combo = ctk.CTkOptionMenu(rarity_frame, values=['R', 'SR', 'SSR'], 
                                       variable=self.support_rarity_var, fg_color=self.colors['accent_blue'], 
                                       corner_radius=8, button_color=self.colors['accent_blue'],
                                       button_hover_color=self.colors['accent_green'])
        rarity_combo.pack(side=tk.RIGHT)
    
    def toggle_restart_settings(self):
        """Toggle visibility of restart settings based on restart enabled checkbox"""
        if self.restart_enabled_var.get():
            self.restart_criteria_frame.pack(fill=tk.X, pady=5)
            self.legacy_frame.pack(fill=tk.X, pady=10, padx=10)
            self.support_frame.pack(fill=tk.X, pady=10, padx=10)
        else:
            self.restart_criteria_frame.pack_forget()
            self.legacy_frame.pack_forget()
            self.support_frame.pack_forget()
        # Auto-save is already triggered by the variable trace
    
    def on_criteria_change(self):
        """Handle changes in restart criteria selection"""
        # When criteria changes, update the other field to 0
        if self.restart_criteria_var.get() == "times":
            self.total_fans_requirement_var.set(0)
        else:  # fans
            self.restart_times_var.set(0)
    
    def save_restart_settings(self):
        """Save restart career settings"""
        try:
            # Get current config
            config = self.main_window.get_config()
            
            # Update restart career config
            if 'restart_career' not in config:
                config['restart_career'] = {}
            
            config['restart_career']['restart_enabled'] = self.restart_enabled_var.get()
            
            # Update restart criteria based on radio button selection
            if self.restart_criteria_var.get() == "times":
                config['restart_career']['restart_times'] = self.restart_times_var.get()
                config['restart_career']['total_fans_requirement'] = 0
            else:  # fans
                config['restart_career']['restart_times'] = 0
                config['restart_career']['total_fans_requirement'] = self.total_fans_requirement_var.get()
            
            # Update auto start career config
            if 'auto_start_career' not in config:
                config['auto_start_career'] = {}
            
            config['auto_start_career']['include_guests_legacy'] = self.include_guests_legacy_var.get()
            config['auto_start_career']['support_speciality'] = self.support_speciality_var.get()
            config['auto_start_career']['support_rarity'] = self.support_rarity_var.get()
            
            # Save to file
            self.main_window.set_config(config)
            
            messagebox.showinfo("Success", "Restart settings saved successfully!")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save restart settings: {e}")
    
    def update_config(self, config):
        """Update the config dictionary with current values"""
        # Ensure restart_career section exists
        if 'restart_career' not in config:
            config['restart_career'] = {}
        
        # Update restart career settings
        config['restart_career']['restart_enabled'] = self.restart_enabled_var.get()
        # Update restart criteria based on radio button selection
        if self.restart_criteria_var.get() == "times":
            config['restart_career']['restart_times'] = self.restart_times_var.get()
            config['restart_career']['total_fans_requirement'] = 0
        else:  # fans
            config['restart_career']['restart_times'] = 0
            config['restart_career']['total_fans_requirement'] = self.total_fans_requirement_var.get()
        
        # Ensure auto_start_career section exists
        if 'auto_start_career' not in config:
            config['auto_start_career'] = {}
        
        # Update auto start career settings
        config['auto_start_career']['include_guests_legacy'] = self.include_guests_legacy_var.get()
        config['auto_start_career']['support_speciality'] = self.support_speciality_var.get()
        config['auto_start_career']['support_rarity'] = self.support_rarity_var.get()
        # Note: auto_charge_tp is not currently in the GUI, but preserve it if it exists in the original config
        original_config = self.main_window.get_config()
        if 'auto_start_career' in original_config and 'auto_charge_tp' in original_config['auto_start_career']:
            config['auto_start_career']['auto_charge_tp'] = original_config['auto_start_career']['auto_charge_tp']
    
    def on_restart_setting_change(self, *args):
        """Called when any restart setting variable changes - auto-save"""
        self.on_setting_change(*args)