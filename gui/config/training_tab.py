"""
Training Tab for Uma Musume Auto-Train Bot GUI Configuration

Contains all training-related settings including stats priority, training settings,
stat caps, and training score configuration.
"""

import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
import json
import os

try:
    from .base_tab import BaseTab
except ImportError:
    from base_tab import BaseTab

class TrainingTab(BaseTab):
    """Training configuration tab containing all training-related settings"""
    
    def __init__(self, tabview, config_panel, colors):
        """Initialize the Training tab"""
        # Initialize variables
        self.priority_vars = []
        self.stat_boxes = []
        self.stat_cap_vars = {}
        
        # Training score variables
        self.rainbow_support_var = tk.DoubleVar(value=1.0)
        self.low_bond_support_var = tk.DoubleVar(value=0.7)
        self.high_bond_support_var = tk.DoubleVar(value=0.0)
        self.hint_var = tk.DoubleVar(value=0.3)
        
        # Load training score configuration
        self.load_training_score_config()
        
        super().__init__(tabview, config_panel, colors, "Training")
        
        # Set up auto-save callbacks for training score variables after base init
        self.add_variable_with_autosave('rainbow_support', self.rainbow_support_var, 'on_training_score_change')
        self.add_variable_with_autosave('low_bond_support', self.low_bond_support_var, 'on_training_score_change')
        self.add_variable_with_autosave('high_bond_support', self.high_bond_support_var, 'on_training_score_change')
        self.add_variable_with_autosave('hint', self.hint_var, 'on_training_score_change')
    
    def create_tab(self):
        """Create the Training tab with all training-related settings"""
        # Add tab to tabview
        training_tab = self.tabview.add("Training")
        
        # Create scrollable content
        training_scroll = self.create_scrollable_content(training_tab)
        
        config = self.main_window.get_config()
        
        # Stats Priority Section
        self._create_priority_section(training_scroll, config)
        
        # Training Settings Section
        self._create_training_settings_section(training_scroll, config)
        
        # Stat Caps Section
        self._create_stat_caps_section(training_scroll, config)
        
        # Training Score Section (collapsible)
        self._create_training_score_section(training_scroll)
        
        # Auto-save info label
        self.create_autosave_info_label(training_scroll)
    
    def _create_priority_section(self, parent, config):
        """Create the stats priority section"""
        priority_frame = ctk.CTkFrame(parent, fg_color=self.colors['bg_light'], corner_radius=10)
        priority_frame.pack(fill=tk.X, pady=10, padx=10)
        
        priority_title = ctk.CTkLabel(priority_frame, text="Stats Priority", font=get_font('section_title'), text_color=self.colors['text_light'])
        priority_title.pack(pady=(15, 10))
        
        # Click to swap instruction
        instruction_label = ctk.CTkLabel(priority_frame, text="Click on two boxes to swap their positions (left to right = highest to lowest priority):", 
                                       text_color=self.colors['text_gray'], font=get_font('body_medium'))
        instruction_label.pack(pady=(0, 15))
        
        # Priority stats container with drag and drop
        self.priority_container = ctk.CTkFrame(priority_frame, fg_color="transparent")
        self.priority_container.pack(fill=tk.X, padx=15, pady=(0, 15))
        
        # Create draggable stat boxes for the 5 fixed stats
        training_config = config.get('training', {})
        priority_stats = training_config.get('priority_stat', ['spd', 'sta', 'wit', 'pwr', 'guts'])
        
        # Ensure we have exactly 5 stats
        while len(priority_stats) < 5:
            priority_stats.append('spd')  # Default fallback
        priority_stats = priority_stats[:5]  # Limit to 5
        
        for i, stat in enumerate(priority_stats):
            self._create_draggable_stat_box(stat, i)
    
    def _create_training_settings_section(self, parent, config):
        """Create the training settings section"""
        settings_frame = ctk.CTkFrame(parent, fg_color=self.colors['bg_light'], corner_radius=10)
        settings_frame.pack(fill=tk.X, pady=10, padx=10)
        
        settings_title = ctk.CTkLabel(settings_frame, text="Training Settings", font=get_font('section_title'), text_color=self.colors['text_light'])
        settings_title.pack(pady=(15, 10))
        
        # Minimum Mood
        mood_frame = ctk.CTkFrame(settings_frame, fg_color="transparent")
        mood_frame.pack(fill=tk.X, padx=15, pady=5)
        ctk.CTkLabel(mood_frame, text="Minimum Mood:", text_color=self.colors['text_light'], font=get_font('label')).pack(side=tk.LEFT)
        training_config = config.get('training', {})
        self.minimum_mood_var = tk.StringVar(value=training_config.get('minimum_mood', 'GREAT'))
        self.minimum_mood_var.trace('w', self.on_training_setting_change)
        mood_combo = ctk.CTkOptionMenu(mood_frame, values=['GREAT', 'GOOD', 'NORMAL', 'BAD', 'AWFUL'], 
                                       variable=self.minimum_mood_var, fg_color=self.colors['accent_blue'], 
                                       corner_radius=8, button_color=self.colors['accent_blue'],
                                       button_hover_color=self.colors['accent_green'],
                                       font=get_font('dropdown'))
        mood_combo.pack(side=tk.RIGHT)
        
        # Maximum Failure Rate
        fail_frame = ctk.CTkFrame(settings_frame, fg_color="transparent")
        fail_frame.pack(fill=tk.X, padx=15, pady=5)
        ctk.CTkLabel(fail_frame, text="Maximum Failure Rate:", text_color=self.colors['text_light'], font=get_font('label')).pack(side=tk.LEFT)
        self.maximum_failure_var = tk.IntVar(value=training_config.get('maximum_failure', 15))
        self.maximum_failure_var.trace('w', self.on_training_setting_change)
        ctk.CTkEntry(fail_frame, textvariable=self.maximum_failure_var, width=100, corner_radius=8).pack(side=tk.RIGHT)
        
        # Minimum Energy for Training
        energy_frame = ctk.CTkFrame(settings_frame, fg_color="transparent")
        energy_frame.pack(fill=tk.X, padx=15, pady=5)
        ctk.CTkLabel(energy_frame, text="Minimum Energy for Training:", text_color=self.colors['text_light'], font=get_font('label')).pack(side=tk.LEFT)
        self.min_energy_var = tk.IntVar(value=training_config.get('min_energy', 30))
        self.min_energy_var.trace('w', self.on_training_setting_change)
        ctk.CTkEntry(energy_frame, textvariable=self.min_energy_var, width=100, corner_radius=8).pack(side=tk.RIGHT)
        
        # Do Race if no good training found
        race_frame = ctk.CTkFrame(settings_frame, fg_color="transparent")
        race_frame.pack(fill=tk.X, padx=15, pady=5)
        self.do_race_var = tk.BooleanVar(value=training_config.get('do_race_when_bad_training', False))
        self.do_race_var.trace('w', self.on_training_setting_change)
        race_checkbox = ctk.CTkCheckBox(race_frame, text="Do Race if no good training found", 
                                      variable=self.do_race_var, text_color=self.colors['text_light'],
                                      font=get_font('checkbox'), command=self.toggle_race_settings)
        race_checkbox.pack(anchor=tk.W)
        
        # Race-related settings (initially visible if do_race is True)
        self.race_settings_frame = ctk.CTkFrame(settings_frame, fg_color="transparent")
        if self.do_race_var.get():
            self.race_settings_frame.pack(fill=tk.X, pady=5)
        
        # Minimum Training Score
        score_frame = ctk.CTkFrame(self.race_settings_frame, fg_color="transparent")
        score_frame.pack(fill=tk.X, pady=5)
        ctk.CTkLabel(score_frame, text="Minimum Training Score:", text_color=self.colors['text_light'], font=get_font('label')).pack(side=tk.LEFT)
        self.min_score_var = tk.DoubleVar(value=training_config.get('min_score', 1.0))
        self.min_score_var.trace('w', self.on_training_setting_change)
        ctk.CTkEntry(score_frame, textvariable=self.min_score_var, width=100, corner_radius=8).pack(side=tk.RIGHT)
        
        # Minimum WIT Training Score
        wit_score_frame = ctk.CTkFrame(self.race_settings_frame, fg_color="transparent")
        wit_score_frame.pack(fill=tk.X, pady=5)
        ctk.CTkLabel(wit_score_frame, text="Minimum WIT Training Score:", text_color=self.colors['text_light'], font=get_font('label')).pack(side=tk.LEFT)
        self.min_wit_score_var = tk.DoubleVar(value=training_config.get('min_wit_score', 1.0))
        self.min_wit_score_var.trace('w', self.on_training_setting_change)
        ctk.CTkEntry(wit_score_frame, textvariable=self.min_wit_score_var, width=100, corner_radius=8).pack(side=tk.RIGHT)
    
    def _create_stat_caps_section(self, parent, config):
        """Create the stat caps section"""
        caps_frame = ctk.CTkFrame(parent, fg_color=self.colors['bg_light'], corner_radius=10)
        caps_frame.pack(fill=tk.X, pady=10, padx=10)
        
        caps_title = ctk.CTkLabel(caps_frame, text="Stat Caps", font=get_font('section_title'), text_color=self.colors['text_light'])
        caps_title.pack(pady=(15, 10))
        
        caps_container = ctk.CTkFrame(caps_frame, fg_color="transparent")
        caps_container.pack(fill=tk.X, padx=15, pady=(0, 15))
        
        training_config = config.get('training', {})
        stat_caps = training_config.get('stat_caps', {})
        stats = ['spd', 'sta', 'pwr', 'guts', 'wit']
        
        # Create horizontal stat cap inputs
        for i, stat in enumerate(stats):
            stat_frame = ctk.CTkFrame(caps_container, fg_color="transparent")
            stat_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 3) if i < len(stats) - 1 else (0, 0))
            
            # Stat name label
            ctk.CTkLabel(stat_frame, text=stat.upper(), font=get_font('label'), 
                        text_color=self.colors['text_gray']).pack(pady=(0, 5))
            
            # Stat cap input
            var = tk.IntVar(value=stat_caps.get(stat, 600))
            var.trace('w', self.on_training_setting_change)
            self.stat_cap_vars[stat] = var
            ctk.CTkEntry(stat_frame, textvariable=var, width=80, corner_radius=8).pack()
    
    def _create_training_score_section(self, parent):
        """Create the collapsible training score section"""
        # Training Score Frame
        score_frame = ctk.CTkFrame(parent, fg_color=self.colors['bg_light'], corner_radius=10)
        score_frame.pack(fill=tk.X, pady=10, padx=10)
        
        # Collapsible header
        self.score_header = ctk.CTkFrame(score_frame, fg_color="transparent")
        self.score_header.pack(fill=tk.X, padx=15, pady=10)
        
        # Header label with click binding
        header_label = ctk.CTkLabel(self.score_header, text="Training Score (Click to expand)", 
                                  font=get_font('section_title'), text_color=self.colors['text_light'])
        header_label.pack()
        
        # Bind click event to expand/collapse
        header_label.bind('<Button-1>', self.toggle_training_score)
        self.score_header.bind('<Button-1>', self.toggle_training_score)
        
        # Initially hidden content
        self.score_content_frame = ctk.CTkFrame(score_frame, fg_color="transparent")
        self.score_content_frame.pack_forget()
    
    def _create_draggable_stat_box(self, stat, index):
        """Create a draggable stat box for priority ordering"""
        # Create a container frame for better control - make it responsive
        container_frame = ctk.CTkFrame(self.priority_container, fg_color="transparent", width=70, height=45)
        container_frame.pack(side=tk.LEFT, padx=(0, 8))
        container_frame.pack_propagate(False)  # Prevent size changes
        
        # Create the stat box with much more rounded corners and better styling
        stat_box = ctk.CTkFrame(container_frame, fg_color=self.colors['accent_blue'], 
                               corner_radius=20, width=65, height=40,
                               border_width=1, border_color=self.colors['accent_blue'])  # Add subtle border for better definition
        stat_box.place(relx=0.5, rely=0.5, anchor="center")
        
        # Create the stat label with better font and styling
        stat_label = ctk.CTkLabel(stat_box, text=stat.upper(), 
                                font=get_font('body_large'), 
                                text_color=self.colors['text_light'])
        stat_label.place(relx=0.5, rely=0.5, anchor="center")
        
        # Store the stat box and its data
        box_data = {
            'frame': stat_box,
            'container': container_frame,
            'label': stat_label,
            'stat': stat,
            'index': index,
            'hovered': False  # Track hover state
        }
        
        self.stat_boxes.append(box_data)
        
        # Bind click events for swapping positions - bind to ALL elements for better click detection
        container_frame.bind('<Button-1>', lambda e, b=box_data: self.on_stat_box_click(e, b))
        stat_box.bind('<Button-1>', lambda e, b=box_data: self.on_stat_box_click(e, b))
        stat_label.bind('<Button-1>', lambda e, b=box_data: self.on_stat_box_click(e, b))
        
        # Add hover effects for better interactivity - bind to all elements
        container_frame.bind('<Enter>', lambda e, b=box_data: self.on_hover_enter(e, b))
        container_frame.bind('<Leave>', lambda e, b=box_data: self.on_hover_leave(e, b))
        stat_box.bind('<Enter>', lambda e, b=box_data: self.on_hover_enter(e, b))
        stat_box.bind('<Leave>', lambda e, b=box_data: self.on_hover_leave(e, b))
        stat_label.bind('<Enter>', lambda e, b=box_data: self.on_hover_enter(e, b))
        stat_label.bind('<Leave>', lambda e, b=box_data: self.on_hover_leave(e, b))
        
        # Make the entire area look clickable
        container_frame.configure(cursor="hand2")
        stat_box.configure(cursor="hand2")
        stat_label.configure(cursor="hand2")
        
        # Create variable for the stat value
        var = tk.StringVar(value=stat)
        self.priority_vars.append(var)
    
    def on_stat_box_click(self, event, box_data):
        """Handle click on stat box for swapping positions"""
        # If no box is currently selected, select this one
        if not hasattr(self, 'selected_box') or self.selected_box is None:
            self.selected_box = box_data
            # Highlight the selected box
            box_data['frame'].configure(fg_color=self.colors['accent_yellow'])
            print(f"Selected {box_data['stat']} for swapping")
        else:
            # If a box is already selected, swap with this one
            if self.selected_box != box_data:
                # Swap the positions
                old_index = self.selected_box['index']
                new_index = box_data['index']
                self.swap_stat_boxes(old_index, new_index)
                print(f"Swapped {self.selected_box['stat']} with {box_data['stat']}")
            
            # Reset selection
            self.selected_box['frame'].configure(fg_color=self.colors['accent_blue'])
            self.selected_box = None
    
    def on_hover_enter(self, event, box_data):
        """Handle mouse enter hover effect"""
        # Don't change color if this box is currently selected for swapping
        if not hasattr(self, 'selected_box') or self.selected_box != box_data:
            if not box_data.get('hovered', False):
                box_data['hovered'] = True
                box_data['frame'].configure(fg_color=self.colors['accent_green'])
    
    def on_hover_leave(self, event, box_data):
        """Handle mouse leave hover effect"""
        # Don't change color if this box is currently selected for swapping
        if not hasattr(self, 'selected_box') or self.selected_box != box_data:
            if box_data.get('hovered', False):
                # Add a small delay to prevent flickering
                def delayed_leave():
                    if not box_data.get('hovered', False):
                        box_data['frame'].configure(fg_color=self.colors['accent_blue'])
                
                # Schedule the color change with a small delay
                self.config_panel.after(50, delayed_leave)
                box_data['hovered'] = False
    
    def swap_stat_boxes(self, index1, index2):
        """Swap two stat boxes at the given indices"""
        # Swap the boxes in the list
        self.stat_boxes[index1], self.stat_boxes[index2] = self.stat_boxes[index2], self.stat_boxes[index1]
        
        # Swap the variables
        self.priority_vars[index1], self.priority_vars[index2] = self.priority_vars[index2], self.priority_vars[index1]
        
        # Update indices
        for i, box_data in enumerate(self.stat_boxes):
            box_data['index'] = i
        
        # Repack all containers in the new order
        for box_data in self.stat_boxes:
            box_data['container'].pack_forget()
        
        for box_data in self.stat_boxes:
            box_data['container'].pack(side=tk.LEFT, padx=(0, 8))
        
        # Trigger auto-save after swapping
        self.on_training_setting_change()
    
    def toggle_race_settings(self):
        """Toggle visibility of race-related settings"""
        if self.do_race_var.get():
            self.race_settings_frame.pack(fill=tk.X, pady=5)
        else:
            self.race_settings_frame.pack_forget()
        # Auto-save is already triggered by the variable trace
    
    def toggle_training_score(self, event):
        """Toggle training score section visibility"""
        if self.score_content_frame.winfo_viewable():
            self.score_content_frame.pack_forget()
        else:
            self.score_content_frame.pack(fill=tk.X, pady=(10, 15), padx=15)
            self.populate_training_score_content()
    
    def populate_training_score_content(self):
        """Populate the training score content"""
        # Clear existing content
        for widget in self.score_content_frame.winfo_children():
            widget.destroy()
        
        # Rainbow Support
        rainbow_frame = ctk.CTkFrame(self.score_content_frame, fg_color="transparent")
        rainbow_frame.pack(fill=tk.X, pady=5)
        ctk.CTkLabel(rainbow_frame, text="Rainbow Support:", text_color=self.colors['text_light'], font=get_font('label')).pack(side=tk.LEFT)
        ctk.CTkEntry(rainbow_frame, textvariable=self.rainbow_support_var, width=100, corner_radius=8).pack(side=tk.RIGHT)
        
        # Low Bond Support
        low_bond_frame = ctk.CTkFrame(self.score_content_frame, fg_color="transparent")
        low_bond_frame.pack(fill=tk.X, pady=5)
        ctk.CTkLabel(low_bond_frame, text="Low Bond (<4) Support:", text_color=self.colors['text_light'], font=get_font('label')).pack(side=tk.LEFT)
        ctk.CTkEntry(low_bond_frame, textvariable=self.low_bond_support_var, width=100, corner_radius=8).pack(side=tk.RIGHT)
        
        # High Bond Different Type Support
        high_bond_frame = ctk.CTkFrame(self.score_content_frame, fg_color="transparent")
        high_bond_frame.pack(fill=tk.X, pady=5)
        ctk.CTkLabel(high_bond_frame, text="High Bond (>=4) Different Type:", text_color=self.colors['text_light'], font=get_font('label')).pack(side=tk.LEFT)
        ctk.CTkEntry(high_bond_frame, textvariable=self.high_bond_support_var, width=100, corner_radius=8).pack(side=tk.RIGHT)
        
        # Hint
        hint_frame = ctk.CTkFrame(self.score_content_frame, fg_color="transparent")
        hint_frame.pack(fill=tk.X, pady=5)
        ctk.CTkLabel(hint_frame, text="Hint:", text_color=self.colors['text_light'], font=get_font('label')).pack(side=tk.LEFT)
        ctk.CTkEntry(hint_frame, textvariable=self.hint_var, width=100, corner_radius=8).pack(side=tk.RIGHT)
    
    def save_training_settings(self):
        """Save training settings to config"""
        try:
            config = self.main_window.get_config()
            
            # Ensure training section exists
            if 'training' not in config:
                config['training'] = {}
            
            # Update priority stats (in current order)
            config['training']['priority_stat'] = [box_data['stat'] for box_data in self.stat_boxes]
            
            # Update training settings
            config['training']['minimum_mood'] = self.minimum_mood_var.get()
            config['training']['maximum_failure'] = self.maximum_failure_var.get()
            config['training']['min_energy'] = self.min_energy_var.get()
            config['training']['do_race_when_bad_training'] = self.do_race_var.get()
            
            # Update race-related settings
            if self.do_race_var.get():
                config['training']['min_score'] = self.min_score_var.get()
                config['training']['min_wit_score'] = self.min_wit_score_var.get()
            
            # Update stat caps
            if 'stat_caps' not in config['training']:
                config['training']['stat_caps'] = {}
            for stat, var in self.stat_cap_vars.items():
                config['training']['stat_caps'][stat] = var.get()
            
            # Save training score config
            self.save_training_score_config()
            
            # Update main config
            self.main_window.set_config(config)
            messagebox.showinfo("Success", "Training settings saved successfully!")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save training settings: {e}")
    
    def save_training_score_config(self):
        """Save training score configuration"""
        try:
            config = {
                "scoring_rules": {
                    "rainbow_support": {
                        "description": "Same type support card with bond level >= 4",
                        "points": self.rainbow_support_var.get()
                    },
                    "not_rainbow_support_low": {
                        "description": "Support with bond level < 4",
                        "points": self.low_bond_support_var.get()
                    },
                    "not_rainbow_support_high": {
                        "description": "Not same type support with bond level >= 4 (no need to get more bond)",
                        "points": self.high_bond_support_var.get()
                    },
                    "hint": {
                        "description": "Hint icon present",
                        "points": self.hint_var.get()
                    }
                }
            }
            
            with open('training_score.json', 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            print(f"Error saving training score config: {e}")
    
    def load_training_score_config(self):
        """Load training score configuration from file"""
        try:
            if os.path.exists('training_score.json'):
                with open('training_score.json', 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                # Update the variables with loaded values
                scoring_rules = config.get('scoring_rules', {})
                
                # Rainbow support
                rainbow_config = scoring_rules.get('rainbow_support', {})
                self.rainbow_support_var.set(rainbow_config.get('points', 1.0))
                
                # Low bond support
                low_bond_config = scoring_rules.get('not_rainbow_support_low', {})
                self.low_bond_support_var.set(low_bond_config.get('points', 0.7))
                
                # High bond different type support
                high_bond_config = scoring_rules.get('not_rainbow_support_high', {})
                self.high_bond_support_var.set(high_bond_config.get('points', 0.0))
                
                # Hint
                hint_config = scoring_rules.get('hint', {})
                self.hint_var.set(hint_config.get('points', 0.3))
                
        except Exception as e:
            print(f"Error loading training score config: {e}")
            # Keep default values if loading fails
    
    def refresh_training_score_values(self):
        """Refresh training score values from the loaded configuration"""
        # This method can be called when the config is refreshed
        self.load_training_score_config()
    
    def on_training_score_change(self, *args):
        """Called when any training score variable changes - auto-save"""
        try:
            # Auto-save training score config
            self.save_training_score_config()
        except Exception as e:
            print(f"Error auto-saving training score config: {e}")
    
    def update_config(self, config):
        """Update the config dictionary with current values"""
        # Ensure training section exists
        if 'training' not in config:
            config['training'] = {}
        
        # Update priority stats (in current order)
        config['training']['priority_stat'] = [box_data['stat'] for box_data in self.stat_boxes]
        
        # Update training settings
        config['training']['minimum_mood'] = self.minimum_mood_var.get()
        config['training']['maximum_failure'] = self.maximum_failure_var.get()
        config['training']['min_energy'] = self.min_energy_var.get()
        config['training']['do_race_when_bad_training'] = self.do_race_var.get()
        
        # Update race-related settings
        if self.do_race_var.get():
            config['training']['min_score'] = self.min_score_var.get()
            config['training']['min_wit_score'] = self.min_wit_score_var.get()
        
        # Update stat caps
        if 'stat_caps' not in config['training']:
            config['training']['stat_caps'] = {}
        for stat, var in self.stat_cap_vars.items():
            config['training']['stat_caps'][stat] = var.get()
    
    def on_training_setting_change(self, *args):
        """Called when any training setting variable changes - auto-save"""
        self.on_setting_change(*args)
