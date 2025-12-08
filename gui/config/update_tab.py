"""
Update Tab for Uma Musume Auto-Train Bot GUI Configuration

Handles automatic update settings and manual update controls.
"""

import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
import threading

try:
    from .base_tab import BaseTab
    from ..font_manager import get_font
except ImportError:
    from base_tab import BaseTab
    from font_manager import get_font

class UpdateTab(BaseTab):
    """Update configuration tab"""
    
    def __init__(self, tabview, config_panel, colors):
        """Initialize the Update tab"""
        super().__init__(tabview, config_panel, colors, "Update")
        self.updating = False
    
    def create_tab(self):
        """Create the Update tab"""
        # Add tab to tabview
        update_tab = self.tabview.add("Update")
        
        # Create scrollable content
        update_scroll = self.create_scrollable_content(update_tab)
        
        config = self.main_window.get_config()
        update_config = config.get('update', {})
        
        # Update Settings Section
        settings_frame, _ = self.create_section_frame(update_scroll, "Update Settings")
        
        # Auto Update checkbox
        auto_update_var = tk.BooleanVar(value=update_config.get('auto_update', False))
        _, auto_update_check = self.create_setting_row(
            settings_frame,
            "Auto Update on Launch",
            widget_type='checkbox',
            variable=auto_update_var
        )
        self.add_variable_with_autosave('auto_update', auto_update_var)
        
        # Install Dependencies checkbox
        install_deps_var = tk.BooleanVar(value=update_config.get('install_dependencies', True))
        _, install_deps_check = self.create_setting_row(
            settings_frame,
            "Auto Install Dependencies",
            widget_type='checkbox',
            variable=install_deps_var
        )
        self.add_variable_with_autosave('install_dependencies', install_deps_var)
        
        # Branch setting
        branch_var = tk.StringVar(value=update_config.get('branch', 'main'))
        _, branch_entry = self.create_setting_row(
            settings_frame,
            "Git Branch",
            widget_type='entry',
            textvariable=branch_var,
            width=150
        )
        self.add_variable_with_autosave('branch', branch_var)
        
        # Remote setting (hidden, always 'origin')
        remote_var = tk.StringVar(value=update_config.get('remote', 'origin'))
        self.add_variable_with_autosave('remote', remote_var)
        
        # Manual Update Section
        manual_frame, _ = self.create_section_frame(update_scroll, "Manual Update")
        
        # Status label
        self.status_label = ctk.CTkLabel(
            manual_frame,
            text="Ready to check for updates",
            text_color=self.colors['text_gray'],
            font=get_font('body_medium')
        )
        self.status_label.pack(pady=10, padx=15)
        
        # Current commit info
        self.commit_label = ctk.CTkLabel(
            manual_frame,
            text="",
            text_color=self.colors['text_gray'],
            font=get_font('body_small')
        )
        self.commit_label.pack(pady=5, padx=15)
        
        # Button frame (centered)
        button_frame = ctk.CTkFrame(manual_frame, fg_color="transparent")
        button_frame.pack(pady=15, padx=15)
        
        # Inner frame for buttons (to center them)
        inner_button_frame = ctk.CTkFrame(button_frame, fg_color="transparent")
        inner_button_frame.pack()
        
        # Check for updates button
        self.check_button = ctk.CTkButton(
            inner_button_frame,
            text="Check for Updates",
            command=self.check_for_updates,
            fg_color=self.colors['accent_blue'],
            hover_color=self.colors['accent_green'],
            font=get_font('button'),
            width=200
        )
        self.check_button.pack(side=tk.LEFT, padx=5)
        
        # Update button (initially disabled)
        self.update_button = ctk.CTkButton(
            inner_button_frame,
            text="Update Now",
            command=self.update_now,
            fg_color=self.colors['accent_green'],
            hover_color=self.colors['accent_blue'],
            font=get_font('button'),
            width=200,
            state='disabled'
        )
        self.update_button.pack(side=tk.LEFT, padx=5)
        
        # Auto-save info
        self.create_autosave_info_label(update_scroll)
        
        # Load current commit info
        self.refresh_commit_info()
    
    def update_config(self, config):
        """Update the config dictionary with current values"""
        if 'update' not in config:
            config['update'] = {}
        
        config['update']['auto_update'] = self.variables.get('auto_update', tk.BooleanVar()).get()
        config['update']['install_dependencies'] = self.variables.get('install_dependencies', tk.BooleanVar()).get()
        config['update']['branch'] = self.variables.get('branch', tk.StringVar()).get()
        config['update']['remote'] = self.variables.get('remote', tk.StringVar()).get()
    
    def refresh_commit_info(self):
        """Refresh current commit information"""
        try:
            from utils.git_manager import GitManager
            
            git_manager = GitManager()
            if git_manager.is_git_repo():
                commit = git_manager.get_current_commit(short=True)
                commit_info = git_manager.get_commit_info()
                
                if commit:
                    text = f"Current commit: {commit}"
                    if commit_info:
                        text += f" - {commit_info['message'][:50]}"
                    self.commit_label.configure(text=text)
                else:
                    self.commit_label.configure(text="Could not get commit information")
            else:
                self.commit_label.configure(text="Not a git repository")
        except Exception as e:
            self.commit_label.configure(text=f"Error: {str(e)}")
    
    def check_for_updates(self):
        """Check for available updates"""
        if self.updating:
            return
        
        self.check_button.configure(state='disabled')
        self.status_label.configure(text="Checking for updates...", text_color=self.colors['text_gray'])
        
        def check_thread():
            try:
                from utils.updater import Updater
                
                branch = self.variables.get('branch', tk.StringVar(value='main')).get()
                remote = self.variables.get('remote', tk.StringVar(value='origin')).get()
                
                updater = Updater(branch=branch, remote=remote)
                
                if not updater.git_manager.test_git():
                    self.root.after(0, lambda: self._update_status("Git is not available", "error"))
                    return
                
                available = updater.check_update()
                
                if available:
                    self.root.after(0, lambda: self._update_status("Update available!", "success", True))
                else:
                    self.root.after(0, lambda: self._update_status("Repository is up to date", "info"))
                    
            except Exception as e:
                self.root.after(0, lambda: self._update_status(f"Error: {str(e)}", "error"))
            finally:
                self.root.after(0, lambda: self.check_button.configure(state='normal'))
        
        thread = threading.Thread(target=check_thread, daemon=True)
        thread.start()
    
    def update_now(self):
        """Update the application now"""
        if self.updating:
            return
        
        result = messagebox.askyesno(
            "Confirm Update",
            "This will update the code and install dependencies.\n"
            "The application will need to be restarted.\n\n"
            "Continue?"
        )
        
        if not result:
            return
        
        self.updating = True
        self.check_button.configure(state='disabled')
        self.update_button.configure(state='disabled')
        self.status_label.configure(text="Updating...", text_color=self.colors['accent_yellow'])
        
        def update_thread():
            try:
                from utils.updater import Updater
                
                branch = self.variables.get('branch', tk.StringVar(value='main')).get()
                remote = self.variables.get('remote', tk.StringVar(value='origin')).get()
                install_deps = self.variables.get('install_dependencies', tk.BooleanVar(value=True)).get()
                
                updater = Updater(branch=branch, remote=remote)
                success = updater.update(install_dependencies=install_deps)
                
                if success:
                    self.root.after(0, lambda: self._update_status("Update completed! Please restart the application.", "success"))
                    self.root.after(0, lambda: messagebox.showinfo("Update Complete", "Update completed successfully!\n\nPlease restart the application to use the new version."))
                else:
                    self.root.after(0, lambda: self._update_status("Update failed. Check logs for details.", "error"))
                    
            except Exception as e:
                self.root.after(0, lambda: self._update_status(f"Error: {str(e)}", "error"))
            finally:
                self.root.after(0, lambda: self._reset_update_buttons())
        
        thread = threading.Thread(target=update_thread, daemon=True)
        thread.start()
    
    def _update_status(self, message, status_type="info", enable_update=False):
        """Update status label"""
        color_map = {
            'info': self.colors['text_gray'],
            'success': self.colors['accent_green'],
            'error': self.colors['accent_red'],
            'warning': self.colors['accent_yellow']
        }
        
        self.status_label.configure(text=message, text_color=color_map.get(status_type, self.colors['text_gray']))
        
        if enable_update:
            self.update_button.configure(state='normal')
        
        # Refresh commit info after update check
        if status_type in ['success', 'info']:
            self.refresh_commit_info()
    
    def _reset_update_buttons(self):
        """Reset update button states"""
        self.updating = False
        self.check_button.configure(state='normal')
        self.update_button.configure(state='disabled')
    
    @property
    def root(self):
        """Get root window"""
        return self.main_window.root

