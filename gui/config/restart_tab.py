"""
Restart Tab for Uma Musume Auto-Train Bot GUI Configuration

Contains restart conditions and career management settings.
"""

import customtkinter as ctk
import tkinter as tk
import os
from tkinter import messagebox, simpledialog
from PIL import Image, ImageTk

try:
    from .base_tab import BaseTab
except ImportError:
    from base_tab import BaseTab

from utils.screenshot import take_screenshot
from utils.recognizer import match_template

class RestartTab(BaseTab):
    """Restart configuration tab containing restart career settings"""
    
    def __init__(self, tabview, config_panel, colors):
        """Initialize the Restart tab"""
        super().__init__(tabview, config_panel, colors, "Restart")
        self.support_templates = []
        self.support_template_images = {}
    
    def create_tab(self):
        """Create the Restart tab with restart career settings"""
        # Add tab to tabview
        restart_tab = self.tabview.add("Restart")
        
        # Create scrollable content
        restart_scroll = self.create_scrollable_content(restart_tab)
        
        config = self.main_window.get_config()
        
        # Restart Career Settings Section
        self._create_restart_settings_section(restart_scroll, config)
        
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
    
    def _create_support_settings_section(self, parent, config):
        """Create the support settings section"""
        self.support_frame = ctk.CTkFrame(parent, fg_color=self.colors['bg_light'], corner_radius=10)
        if self.restart_enabled_var.get():
            self.support_frame.pack(fill=tk.X, pady=10, padx=10)
        
        support_title = ctk.CTkLabel(self.support_frame, text="Support Templates", 
                                   font=get_font('section_title'), text_color=self.colors['text_light'])
        support_title.pack(pady=(15, 10))

        # Use templates toggle
        use_template_frame = ctk.CTkFrame(self.support_frame, fg_color="transparent")
        use_template_frame.pack(fill=tk.X, padx=15, pady=5)
        self.use_support_template_var = tk.BooleanVar(value=config.get('auto_start_career', {}).get('use_support_templates', False))
        self.use_support_template_var.trace('w', self.on_restart_setting_change)
        use_checkbox = ctk.CTkCheckBox(use_template_frame, text="Use Support cards template", variable=self.use_support_template_var,
                                       text_color=self.colors['text_light'], font=get_font('checkbox'),
                                       command=self.toggle_template_controls)
        use_checkbox.pack(anchor=tk.W)

        # Template selection row
        templates = self._load_support_templates()
        current_template = config.get('auto_start_career', {}).get('support_template_name', '')
        if current_template and current_template not in templates:
            templates.append(current_template)
        templates = sorted([t for t in templates if t])

        template_row = ctk.CTkFrame(self.support_frame, fg_color="transparent")
        template_row.pack(fill=tk.X, padx=15, pady=5)
        ctk.CTkLabel(template_row, text="Template:", text_color=self.colors['text_light'], font=get_font('label')).pack(side=tk.LEFT)

        self.support_template_var = tk.StringVar(value=current_template if current_template else (templates[0] if templates else ""))
        self.support_template_var.trace('w', self.on_restart_setting_change)
        self.template_dropdown = ctk.CTkOptionMenu(template_row,
                                                  values=templates if templates else ["No templates"],
                                                  variable=self.support_template_var,
                                                  fg_color=self.colors['accent_blue'],
                                                  corner_radius=8, button_color=self.colors['accent_blue'],
                                                  button_hover_color=self.colors['accent_green'],
                                                  width=180)
        self.template_dropdown.pack(side=tk.LEFT, padx=(10, 10))

        # Add / Remove buttons on the right of dropdown
        add_btn = ctk.CTkButton(template_row, text="Add New", command=self.add_support_template,
                                fg_color=self.colors['accent_blue'], hover_color=self.colors['accent_green'], width=90)
        add_btn.pack(side=tk.LEFT, padx=(0, 8))
        remove_btn = ctk.CTkButton(template_row, text="Remove", command=self.remove_support_template,
                                   fg_color=self.colors['accent_red'], hover_color="#a83244", width=90)
        remove_btn.pack(side=tk.LEFT)

        self.template_controls = (template_row, self.template_dropdown, add_btn, remove_btn)
        self.toggle_template_controls()
    
    def toggle_restart_settings(self):
        """Toggle visibility of restart settings based on restart enabled checkbox"""
        if self.restart_enabled_var.get():
            self.restart_criteria_frame.pack(fill=tk.X, pady=5)
            self.support_frame.pack(fill=tk.X, pady=10, padx=10)
        else:
            self.restart_criteria_frame.pack_forget()
            self.support_frame.pack_forget()
        # Auto-save is already triggered by the variable trace
    
    def on_criteria_change(self):
        """Handle changes in restart criteria selection"""
        # When criteria changes, update the other field to 0
        if self.restart_criteria_var.get() == "times":
            self.total_fans_requirement_var.set(0)
        else:  # fans
            self.restart_times_var.set(0)
    
    def _get_supports_dir(self):
        """Return the absolute path to the supports template directory."""
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        supports_dir = os.path.join(project_root, "template", "supports")
        os.makedirs(supports_dir, exist_ok=True)
        return supports_dir

    def _load_support_templates(self):
        """Load available support templates from the supports directory."""
        supports_dir = self._get_supports_dir()
        templates = [f for f in os.listdir(supports_dir) if f.lower().endswith(".png")]
        templates.sort()
        self.support_templates = templates
        return templates

    def _refresh_template_dropdown(self):
        """Refresh dropdown values after add/remove."""
        templates = self._load_support_templates()
        if not templates:
            templates = ["No templates"]
            self.support_template_var.set("")
        self.template_dropdown.configure(values=templates)
        # If the current selection is missing, set to first template
        if self.support_template_var.get() not in templates:
            self.support_template_var.set("" if templates == ["No templates"] else templates[0])

    def toggle_template_controls(self):
        """Show/hide and enable/disable template controls based on checkbox."""
        enabled = self.use_support_template_var.get()
        # Show or hide the entire row
        if enabled:
            if not self.template_controls[0].winfo_ismapped():
                self.template_controls[0].pack(fill=tk.X, padx=15, pady=5)
        else:
            if self.template_controls[0].winfo_ismapped():
                self.template_controls[0].pack_forget()
        # Enable/disable individual widgets
        state = "normal" if enabled else "disabled"
        dropdown_state = state if (enabled and self.support_templates) else "disabled"
        self.template_controls[1].configure(state=dropdown_state)
        for btn in self.template_controls[2:]:
            btn.configure(state=state)

    def add_support_template(self):
        """Capture emulator screen, crop, and save as a new template."""
        try:
            screenshot = take_screenshot()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to take screenshot: {e}")
            return

        cropped = self._crop_image_with_tk(screenshot)
        if cropped is None:
            return

        name = self._prompt_template_name()
        if not name:
            return

        safe_name = f"{name.strip()}.png"
        save_path = os.path.join(self._get_supports_dir(), safe_name)
        try:
            cropped.save(save_path)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save template: {e}")
            return

        self._refresh_template_dropdown()
        self.support_template_var.set(safe_name)
        messagebox.showinfo("Saved", f"Template saved to {save_path}")

    def remove_support_template(self):
        """Remove the selected template file."""
        template = self.support_template_var.get()
        if not template:
            messagebox.showwarning("No selection", "No template selected.")
            return
        path = os.path.join(self._get_supports_dir(), template)
        if not os.path.exists(path):
            messagebox.showwarning("Missing", "Selected template file does not exist.")
            return
        if not messagebox.askyesno("Confirm", f"Remove template '{template}'?"):
            return
        try:
            os.remove(path)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to remove template: {e}")
            return
        self._refresh_template_dropdown()
        messagebox.showinfo("Removed", f"Removed template '{template}'.")

    def _crop_image_with_tk(self, pil_image):
        """Open a simple crop UI and return the cropped PIL image or None."""
        if pil_image is None:
            return None

        top = ctk.CTkToplevel(self.tabview)
        top.title("Crop Template")
        max_dim = 1200
        w, h = pil_image.size
        scale = min(max_dim / w, max_dim / h, 1.0)
        display_img = pil_image.resize((int(w * scale), int(h * scale)), Image.LANCZOS) if scale < 1.0 else pil_image
        photo = ImageTk.PhotoImage(display_img)

        canvas = tk.Canvas(top, width=display_img.width, height=display_img.height, cursor="cross")
        canvas.pack()
        canvas.create_image(0, 0, anchor="nw", image=photo)

        selection = {}
        rect = None

        def on_press(event):
            selection['x1'], selection['y1'] = event.x, event.y

        def on_drag(event):
            nonlocal rect
            if rect:
                canvas.delete(rect)
            rect = canvas.create_rectangle(selection.get('x1', 0), selection.get('y1', 0), event.x, event.y, outline="red", width=2)

        def on_release(event):
            selection['x2'], selection['y2'] = event.x, event.y
            on_drag(event)

        canvas.bind("<ButtonPress-1>", on_press)
        canvas.bind("<B1-Motion>", on_drag)
        canvas.bind("<ButtonRelease-1>", on_release)

        result = {'bbox': None}

        def confirm():
            if not {'x1', 'y1', 'x2', 'y2'} <= selection.keys():
                messagebox.showwarning("No selection", "Please drag to select an area.")
                return
            x1, y1, x2, y2 = selection['x1'], selection['y1'], selection['x2'], selection['y2']
            if abs(x2 - x1) < 5 or abs(y2 - y1) < 5:
                messagebox.showwarning("Too small", "Selection is too small.")
                return
            if scale != 0:
                # Convert back to original coordinates
                ox1 = int(min(x1, x2) / scale)
                oy1 = int(min(y1, y2) / scale)
                ox2 = int(max(x1, x2) / scale)
                oy2 = int(max(y1, y2) / scale)
            else:
                ox1, oy1, ox2, oy2 = min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2)
            result['bbox'] = (ox1, oy1, ox2, oy2)
            top.destroy()

        def cancel():
            top.destroy()

        btn_frame = ctk.CTkFrame(top, fg_color="transparent")
        btn_frame.pack(fill=tk.X, pady=5)
        ctk.CTkButton(btn_frame, text="Confirm", command=confirm, fg_color=self.colors['accent_green']).pack(side=tk.LEFT, padx=5)
        ctk.CTkButton(btn_frame, text="Cancel", command=cancel, fg_color=self.colors['accent_red']).pack(side=tk.LEFT, padx=5)

        # Keep reference to PhotoImage
        canvas.image = photo
        top.grab_set()
        top.wait_window()

        if result['bbox']:
            return pil_image.crop(result['bbox'])
        return None

    def _prompt_template_name(self):
        """Prompt for template name using a themed CTk dialog."""
        top = ctk.CTkToplevel(self.tabview)
        top.title("Template Name")
        top.configure(fg_color=self.colors['bg_light'])
        top.resizable(False, False)

        frame = ctk.CTkFrame(top, fg_color="transparent")
        frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        label = ctk.CTkLabel(frame, text="Enter template name (without extension):",
                             text_color=self.colors['text_light'], font=get_font('label'))
        label.pack(anchor=tk.W, pady=(0, 10))

        entry = ctk.CTkEntry(frame, corner_radius=8, width=260)
        entry.pack(fill=tk.X)
        entry.focus_set()

        result = {'name': None}

        def on_ok():
            text = entry.get().strip()
            if text:
                result['name'] = text
            top.destroy()

        def on_cancel():
            top.destroy()

        btn_frame = ctk.CTkFrame(frame, fg_color="transparent")
        btn_frame.pack(fill=tk.X, pady=(15, 0))
        ok_btn = ctk.CTkButton(btn_frame, text="OK", command=on_ok,
                               fg_color=self.colors['accent_green'], hover_color="#357a38", width=80)
        ok_btn.pack(side=tk.RIGHT, padx=(5, 0))
        cancel_btn = ctk.CTkButton(btn_frame, text="Cancel", command=on_cancel,
                                   fg_color=self.colors['accent_red'], hover_color="#a83244", width=80)
        cancel_btn.pack(side=tk.RIGHT, padx=(0, 5))

        # Center the dialog relative to the parent
        top.update_idletasks()
        w = top.winfo_width()
        h = top.winfo_height()
        px = top.winfo_screenwidth() // 2 - w // 2
        py = top.winfo_screenheight() // 2 - h // 2
        top.geometry(f"+{px}+{py}")

        top.grab_set()
        top.wait_window()
        return result['name']
    
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
            
            config['auto_start_career']['use_support_templates'] = self.use_support_template_var.get()
            config['auto_start_career']['support_template_name'] = self.support_template_var.get()
            
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
        config['auto_start_career']['use_support_templates'] = self.use_support_template_var.get()
        config['auto_start_career']['support_template_name'] = self.support_template_var.get()
        # Note: auto_charge_tp is not currently in the GUI, but preserve it if it exists in the original config
        original_config = self.main_window.get_config()
        if 'auto_start_career' in original_config and 'auto_charge_tp' in original_config['auto_start_career']:
            config['auto_start_career']['auto_charge_tp'] = original_config['auto_start_career']['auto_charge_tp']
        # Preserve old speciality/rarity values if present in original config even though UI is hidden
        for legacy_key in ('support_speciality', 'support_rarity'):
            if 'auto_start_career' in original_config and legacy_key in original_config['auto_start_career']:
                config['auto_start_career'][legacy_key] = original_config['auto_start_career'][legacy_key]
    
    def on_restart_setting_change(self, *args):
        """Called when any restart setting variable changes - auto-save"""
        self.on_setting_change(*args)