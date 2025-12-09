"""
Skill Tab for Uma Musume Auto-Train Bot GUI Configuration

Contains skill purchase settings, support card configuration, and skill priorities.
"""

import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
import json
import os
import shutil

try:
    from .base_tab import BaseTab
    from .skill_list_helper import open_skill_list_window
except ImportError:
    from base_tab import BaseTab
    from skill_list_helper import open_skill_list_window

class SkillTab(BaseTab):
    """Skill configuration tab containing skill management settings"""
    
    def __init__(self, tabview, config_panel, colors):
        """Initialize the Skill tab"""
        super().__init__(tabview, config_panel, colors, "Skill")
    
    def create_tab(self):
        """Create the Skill tab with skill management settings"""
        # Add tab to tabview
        skill_tab = self.tabview.add("Skill")
        
        config = self.main_window.get_config()
        skills_config = config.get('skills', {})
        
        # Fixed header section (always visible)
        header_frame, _ = self.create_section_frame(skill_tab, "Skill Management", 
                                                   {'fill': tk.X, 'pady': (10, 5), 'padx': 10})
        
        # Enable Skill Point Check
        enable_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        enable_frame.pack(fill=tk.X, padx=15, pady=5)
        self.enable_skill_check_var = tk.BooleanVar(value=skills_config.get('enable_skill_point_check', True))
        self.enable_skill_check_var.trace('w', self.on_skill_setting_change)
        enable_checkbox = ctk.CTkCheckBox(enable_frame, text="Enable Skill Point check and Skill Purchase", 
                                        variable=self.enable_skill_check_var, text_color=self.colors['text_light'],
                                        font=get_font('checkbox'), command=self.toggle_skill_settings)
        enable_checkbox.pack(anchor=tk.W)
        
        self._create_skill_settings(header_frame, config)
        self.create_autosave_info_label(skill_tab, {'side': tk.BOTTOM, 'pady': 20})
    
    def _create_skill_settings(self, parent, config):
        """Create skill settings section"""
        # Container for all skill settings (hidden when checkbox is unchecked)
        self.skill_settings_container = ctk.CTkFrame(parent, fg_color=self.colors['bg_light'], corner_radius=10)
        if self.enable_skill_check_var.get():
            self.skill_settings_container.pack(fill=tk.X, pady=5)
        
        skills_config = config.get('skills', {})
        
        # Skill Point Cap
        self.skill_point_cap_var = tk.IntVar(value=skills_config.get('skill_point_cap', 400))
        self.add_variable_with_autosave('skill_point_cap', self.skill_point_cap_var)
        _, cap_entry = self.create_setting_row(self.skill_settings_container, "Skill Point Cap:", 'entry', 
                                              textvariable=self.skill_point_cap_var, width=100)
        
        # Skill Purchase Mode
        self.skill_purchase_var = tk.StringVar(value=skills_config.get('skill_purchase', 'auto'))
        self.add_variable_with_autosave('skill_purchase', self.skill_purchase_var)
        _, mode_combo = self.create_setting_row(self.skill_settings_container, "Skill Purchase Mode:", 'optionmenu', 
                                               values=['auto', 'manual'], 
                                               variable=self.skill_purchase_var,
                                               command=self.toggle_skill_purchase_settings)
        
        # Auto-specific settings (initially visible if mode is auto and skill check is enabled)
        self.auto_settings_frame = ctk.CTkFrame(self.skill_settings_container, fg_color="transparent")
        if self.enable_skill_check_var.get() and self.skill_purchase_var.get() == 'auto':
            self.auto_settings_frame.pack(fill=tk.X, pady=5)
        
        # Skill Template
        template_frame = ctk.CTkFrame(self.auto_settings_frame, fg_color="transparent")
        template_frame.pack(fill=tk.X, pady=15, padx=15)
        
        template_label = ctk.CTkLabel(template_frame, text="Skill Template:", text_color=self.colors['text_light'])
        template_label.pack(side=tk.LEFT)
        
        # Dropdown + buttons container
        file_container = ctk.CTkFrame(template_frame, fg_color="transparent")
        file_container.pack(side=tk.RIGHT)

        templates = self._load_skill_templates()
        current_template = os.path.basename(skills_config.get('skill_file', 'skills.json'))
        if current_template and current_template not in templates:
            templates.append(current_template)
        templates = sorted([t for t in templates if t])

        self.skill_file_var = tk.StringVar(value=current_template if current_template else (templates[0] if templates else ""))
        self.skill_file_var.trace('w', self.on_skill_setting_change)

        self.skill_dropdown = ctk.CTkOptionMenu(
            file_container,
            values=templates if templates else ["No templates"],
            variable=self.skill_file_var,
            fg_color=self.colors['accent_blue'],
            corner_radius=8,
            button_color=self.colors['accent_blue'],
            button_hover_color=self.colors['accent_green'],
            width=180
        )
        self.skill_dropdown.pack(side=tk.LEFT, padx=(10, 10))
        self._refresh_skill_dropdown(select=self.skill_file_var.get())

        ctk.CTkButton(file_container, text="Add New", command=self.add_skill_template, fg_color=self.colors['accent_blue'], corner_radius=8, height=30, width=90).pack(side=tk.LEFT, padx=(0,5))
        ctk.CTkButton(file_container, text="Remove", command=self.remove_skill_template, fg_color=self.colors['accent_red'], corner_radius=8, height=30, width=90).pack(side=tk.LEFT, padx=(0,5))
        ctk.CTkButton(file_container, text="Edit", command=self.open_skill_list_window, fg_color=self.colors['accent_green'], corner_radius=8, height=30, width=90).pack(side=tk.LEFT)
    
    def _create_save_button(self, parent):
        """Create auto-save info label"""
        info_label = ctk.CTkLabel(parent, text="✓ All changes are automatically saved", 
                                 text_color=self.colors['accent_green'], font=get_font('body_medium'))
        info_label.pack(side=tk.BOTTOM, pady=20)
    
    def toggle_skill_settings(self):
        """Toggle visibility of skill-related settings"""
        if self.enable_skill_check_var.get():
            # Show all skill settings
            self.skill_settings_container.pack(fill=tk.X, pady=5)
            # Also check if auto settings should be shown
            self.toggle_skill_purchase_settings()
        else:
            # Hide all skill settings including auto settings
            self.skill_settings_container.pack_forget()
            self.auto_settings_frame.pack_forget()
        # Auto-save is already triggered by the variable trace
    
    def toggle_skill_purchase_settings(self, value=None):
        """Toggle visibility of auto-specific skill settings"""
        # Only show auto settings if skill check is enabled AND mode is auto
        if self.enable_skill_check_var.get() and self.skill_purchase_var.get() == 'auto':
            self.auto_settings_frame.pack(fill=tk.X, pady=5)
        else:
            self.auto_settings_frame.pack_forget()
    
    def save_skill_settings(self):
        """Save skill settings to config"""
        try:
            config = self.main_window.get_config()
            
            # Ensure skills section exists
            if 'skills' not in config:
                config['skills'] = {}
            
            config['skills']['enable_skill_point_check'] = self.enable_skill_check_var.get()
            config['skills']['skill_point_cap'] = self.skill_point_cap_var.get()
            config['skills']['skill_purchase'] = self.skill_purchase_var.get()
            config['skills']['skill_file'] = self.skill_file_var.get()
            
            self.main_window.set_config(config)
            messagebox.showinfo("Success", "Skill settings saved successfully!")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save skill settings: {e}")
    
    def update_config(self, config):
        """Update the config dictionary with current values"""
        # Ensure skills section exists
        if 'skills' not in config:
            config['skills'] = {}
        
        config['skills']['enable_skill_point_check'] = self.enable_skill_check_var.get()
        config['skills']['skill_point_cap'] = self.skill_point_cap_var.get()
        config['skills']['skill_purchase'] = self.skill_purchase_var.get()
        config['skills']['skill_file'] = self._build_skill_path(self.skill_file_var.get())
        config['skills']['skill_file'] = self._build_skill_path(self.skill_file_var.get())
    
    def on_skill_setting_change(self, *args):
        """Called when any skill setting variable changes - auto-save"""
        self.on_setting_change(*args)
    
    def open_skill_list_window(self):
        """Open window to edit skill lists"""
        # Ensure file exists before opening editor
        self._ensure_skill_file_exists(self.skill_file_var.get())
        open_skill_list_window(self)

    # ---------------- Helpers for skill templates ---------------- #
    def _get_skills_dir(self):
        """Ensure and return the skills templates directory."""
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        skills_dir = os.path.join(project_root, "template", "skills")
        os.makedirs(skills_dir, exist_ok=True)
        return skills_dir

    def _load_skill_templates(self):
        """List available skill template JSON files."""
        skills_dir = self._get_skills_dir()
        templates = [f for f in os.listdir(skills_dir) if f.lower().endswith(".json")]
        templates.sort()
        return templates

    def _build_skill_path(self, filename):
        """Normalize stored skill path."""
        if not filename:
            return ""
        if os.path.isabs(filename):
            return filename
        normalized = filename.replace("\\", "/")
        if normalized.startswith("template/skills/"):
            return normalized
        return os.path.join("template", "skills", filename).replace("\\", "/")

    def get_skill_file_path(self):
        """Return absolute path for the selected skill file."""
        filename = self.skill_file_var.get()
        rel_path = self._build_skill_path(filename)
        if os.path.isabs(rel_path):
            return rel_path
        skills_dir = self._get_skills_dir()
        if rel_path.startswith("template/skills/"):
            project_root = os.path.abspath(os.path.join(skills_dir, "..", ".."))
            return os.path.join(project_root, rel_path)
        return os.path.join(skills_dir, os.path.basename(filename))

    def _ensure_skill_file_exists(self, filename):
        """Create the selected skill file from example if missing."""
        target = self.get_skill_file_path()
        if not target:
            return ""
        if not os.path.exists(target):
            example = os.path.join(self._get_skills_dir(), "skills.example.json")
            try:
                if os.path.exists(example):
                    shutil.copy(example, target)
                else:
                    with open(target, 'w', encoding='utf-8') as f:
                        json.dump({"skill_priority": [], "gold_skill_upgrades": {}}, f, indent=2, ensure_ascii=False)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to create skill template: {e}")
        return target

    def _refresh_skill_dropdown(self, select=None):
        """Refresh skill dropdown after add/remove."""
        templates = self._load_skill_templates()
        if select and select not in templates:
            templates.append(select)
        templates = sorted([t for t in templates if t])
        values = templates if templates else ["No templates"]
        self.skill_dropdown.configure(values=values, state=("normal" if templates else "disabled"))
        if self.skill_file_var.get() not in templates:
            self.skill_file_var.set(select if select in templates else (templates[0] if templates else ""))

    def add_skill_template(self):
        """Create a new skill template from the example file."""
        dialog = ctk.CTkInputDialog(text="Enter new skill template name (without extension):", title="Add Skill Template")
        name = dialog.get_input() if dialog else None
        if not name or not name.strip():
            return
        safe_name = name.strip()
        if not safe_name.lower().endswith(".json"):
            safe_name += ".json"
        target = os.path.join(self._get_skills_dir(), safe_name)
        if os.path.exists(target):
            messagebox.showwarning("Exists", f"'{safe_name}' already exists.")
            return
        example = os.path.join(self._get_skills_dir(), "skills.example.json")
        try:
            if os.path.exists(example):
                shutil.copy(example, target)
            else:
                with open(target, 'w', encoding='utf-8') as f:
                    json.dump({"skill_priority": [], "gold_skill_upgrades": {}}, f, indent=2, ensure_ascii=False)
            self._refresh_skill_dropdown(select=safe_name)
            self.skill_file_var.set(safe_name)
            messagebox.showinfo("Created", f"Created {safe_name} in skills/")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to create skill template: {e}")

    def remove_skill_template(self):
        """Delete the selected skill template file."""
        filename = self.skill_file_var.get()
        if not filename:
            messagebox.showwarning("No selection", "No template selected.")
            return
        path = os.path.join(self._get_skills_dir(), filename)
        if not os.path.exists(path):
            messagebox.showwarning("Missing", "Selected template file does not exist.")
            return
        if not messagebox.askyesno("Confirm", f"Remove template '{filename}'?"):
            return
        try:
            os.remove(path)
            self._refresh_skill_dropdown()
            messagebox.showinfo("Removed", f"Removed template '{filename}'.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to remove template: {e}")
