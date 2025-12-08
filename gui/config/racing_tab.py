"""
Racing Tab for Uma Musume Auto-Train Bot GUI Configuration

Contains all racing-related settings including allowed grades, tracks, distances,
strategy settings, and custom race management.
"""

import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox, filedialog
import json
import os

try:
    from .base_tab import BaseTab
except ImportError:
    from base_tab import BaseTab

class RacingTab(BaseTab):
    """Racing configuration tab containing all racing-related settings"""
    
    def __init__(self, tabview, config_panel, colors):
        """Initialize the Racing tab"""
        # Initialize variables
        self.allowed_grades_vars = {}
        self.allowed_tracks_vars = {}
        self.allowed_distances_vars = {}
        
        super().__init__(tabview, config_panel, colors, "Racing")
    
    def create_tab(self):
        """Create the Racing tab"""
        # Add tab to tabview
        racing_tab = self.tabview.add("Racing")
        
        # Create scrollable frame inside the racing tab
        racing_scroll = ctk.CTkScrollableFrame(racing_tab, fg_color="transparent", corner_radius=0)
        racing_scroll.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        config = self.main_window.get_config()
        racing_config = config.get('racing', {})
        
        # Racing Settings Frame
        self._create_racing_settings_section(racing_scroll, racing_config)
        
        # Custom Race Settings
        self._create_custom_race_section(racing_scroll, racing_config)
        
        # Auto-save info label
        self.create_autosave_info_label(racing_scroll)
    
    def _create_racing_settings_section(self, parent, config):
        """Create the main racing settings section"""
        racing_frame = ctk.CTkFrame(parent, fg_color=self.colors['bg_light'], corner_radius=10)
        racing_frame.pack(fill=tk.X, pady=10, padx=10)
        
        racing_title = ctk.CTkLabel(racing_frame, text="Racing Settings", font=get_font('section_title'), text_color=self.colors['text_light'])
        racing_title.pack(pady=(15, 10))
        
        # Allowed Grades (multi-select, title on first line, checks below in one row)
        grades_frame = ctk.CTkFrame(racing_frame, fg_color="transparent")
        grades_frame.pack(fill=tk.X, padx=15, pady=5)
        ctk.CTkLabel(grades_frame, text="Allowed Grades:", text_color=self.colors['text_light'], font=get_font('label')).pack(anchor=tk.W)
        grades_options = ['G1', 'G2', 'G3', 'OP', 'Pre-OP']
        existing_grades = config.get('allowed_grades', [])
        grades_checks = ctk.CTkFrame(grades_frame, fg_color="transparent")
        grades_checks.pack(fill=tk.X)
        for i, grade in enumerate(grades_options):
            var = tk.BooleanVar(value=grade in existing_grades)
            var.trace('w', self.on_racing_setting_change)
            self.allowed_grades_vars[grade] = var
            ctk.CTkCheckBox(grades_checks, text=grade, variable=var, text_color=self.colors['text_light'], font=get_font('checkbox'), width=50).pack(side=tk.LEFT, padx=(0, 15))

        # Allowed Tracks (multi-select)
        tracks_frame = ctk.CTkFrame(racing_frame, fg_color="transparent")
        tracks_frame.pack(fill=tk.X, padx=15, pady=5)
        ctk.CTkLabel(tracks_frame, text="Allowed Tracks:", text_color=self.colors['text_light'], font=get_font('label')).pack(anchor=tk.W)
        tracks_options = ['Turf', 'Dirt']
        existing_tracks = config.get('allowed_tracks', [])
        tracks_checks = ctk.CTkFrame(tracks_frame, fg_color="transparent")
        tracks_checks.pack(fill=tk.X)
        for track in tracks_options:
            var = tk.BooleanVar(value=track in existing_tracks)
            var.trace('w', self.on_racing_setting_change)
            self.allowed_tracks_vars[track] = var
            ctk.CTkCheckBox(tracks_checks, text=track, variable=var, text_color=self.colors['text_light'], font=get_font('checkbox'), width=50).pack(side=tk.LEFT, padx=(0, 15), pady=2)

        # Allowed Distances (multi-select, title on first line, checks below in one row)
        distances_frame = ctk.CTkFrame(racing_frame, fg_color="transparent")
        distances_frame.pack(fill=tk.X, padx=15, pady=5)
        ctk.CTkLabel(distances_frame, text="Allowed Distances:", text_color=self.colors['text_light'], font=get_font('label')).pack(anchor=tk.W)
        distances_options = ['Sprint', 'Mile', 'Medium', 'Long']
        existing_distances = config.get('allowed_distances', [])
        distances_checks = ctk.CTkFrame(distances_frame, fg_color="transparent")
        distances_checks.pack(fill=tk.X)
        for i, dist in enumerate(distances_options):
            var = tk.BooleanVar(value=dist in existing_distances)
            var.trace('w', self.on_racing_setting_change)
            self.allowed_distances_vars[dist] = var
            ctk.CTkCheckBox(distances_checks, text=dist, variable=var, text_color=self.colors['text_light'], font=get_font('checkbox'), width=50).pack(side=tk.LEFT, padx=(0,15))
        
        # Strategy
        strategy_frame = ctk.CTkFrame(racing_frame, fg_color="transparent")
        strategy_frame.pack(fill=tk.X, padx=15, pady=10)
        ctk.CTkLabel(strategy_frame, text="Strategy:", text_color=self.colors['text_light'], font=get_font('label')).pack(side=tk.LEFT)
        self.strategy_var = tk.StringVar(value=config.get('strategy', 'FRONT'))
        self.strategy_var.trace('w', self.on_racing_setting_change)
        strategy_combo = ctk.CTkOptionMenu(strategy_frame, values=['FRONT', 'PACE', 'LATE', 'END'], 
                                          variable=self.strategy_var, fg_color=self.colors['accent_blue'], 
                                          corner_radius=8, button_color=self.colors['accent_blue'],
                                          button_hover_color=self.colors['accent_green'],
                                          font=get_font('dropdown'))
        strategy_combo.pack(side=tk.RIGHT)
        
        # Race Retry
        retry_frame = ctk.CTkFrame(racing_frame, fg_color="transparent")
        retry_frame.pack(fill=tk.X, padx=15, pady=(5, 15))
        self.retry_race_var = tk.BooleanVar(value=config.get('retry_race', True))
        self.retry_race_var.trace('w', self.on_racing_setting_change)
        retry_checkbox = ctk.CTkCheckBox(retry_frame, text="Race Retry using Clock", 
                                       variable=self.retry_race_var, text_color=self.colors['text_light'],
                                       font=get_font('checkbox'))
        retry_checkbox.pack(anchor=tk.W)
    
    def _create_custom_race_section(self, parent, config):
        """Create the custom race settings section"""
        # Do Custom Races (placed at bottom above save)
        custom_toggle_frame = ctk.CTkFrame(parent, fg_color=self.colors['bg_light'], corner_radius=10)
        custom_toggle_frame.pack(fill=tk.X, padx=10, pady=5)
        inner_toggle = ctk.CTkFrame(custom_toggle_frame, fg_color="transparent")
        inner_toggle.pack(fill=tk.X, padx=15, pady=5)
        self.do_custom_race_var = tk.BooleanVar(value=config.get('do_custom_race', True))
        self.do_custom_race_var.trace('w', self.on_racing_setting_change)
        ctk.CTkCheckBox(inner_toggle, text="Do Custom Races", variable=self.do_custom_race_var, 
                       text_color=self.colors['text_light'], font=get_font('checkbox'), 
                       command=self.toggle_custom_race_settings).pack(anchor=tk.W)

        # Custom Race Settings (hidden when disabled)
        self.custom_race_settings_frame = ctk.CTkFrame(custom_toggle_frame, fg_color="transparent")
        if self.do_custom_race_var.get():
            self.custom_race_settings_frame.pack(fill=tk.X, padx=15, pady=5)

        # Custom Race File with Browse + Edit button
        file_row = ctk.CTkFrame(self.custom_race_settings_frame, fg_color="transparent")
        file_row.pack(fill=tk.X, pady=(0,5))
        ctk.CTkLabel(file_row, text="Custom Race File:", text_color=self.colors['text_light'], font=get_font('label')).pack(side=tk.LEFT)
        self.custom_race_file_var = tk.StringVar(value=config.get('custom_race_file', 'custom_races.json'))
        self.custom_race_file_var.trace('w', self.on_racing_setting_change)
        file_controls = ctk.CTkFrame(file_row, fg_color="transparent")
        file_controls.pack(side=tk.RIGHT)
        ctk.CTkEntry(file_controls, textvariable=self.custom_race_file_var, width=220, corner_radius=8, font=get_font('input')).pack(side=tk.LEFT, padx=(0, 5))
        ctk.CTkButton(file_controls, text="Open File", command=self.open_custom_race_file, fg_color=self.colors['accent_blue'], corner_radius=8, height=30, width=90, font=get_font('button')).pack(side=tk.LEFT, padx=(0, 5))
        # Edit button below
        ctk.CTkButton(self.custom_race_settings_frame, text="Edit Custom Race List", command=self.open_custom_race_list_window, fg_color=self.colors['accent_green'], corner_radius=8, height=30, width=160, font=get_font('button')).pack(anchor=tk.W, padx=0, pady=(0,5))
    
    def save_racing_settings(self):
        """Save racing settings to config"""
        try:
            config = self.main_window.get_config()
            
            # Ensure racing section exists
            if 'racing' not in config:
                config['racing'] = {}

            config['racing']['strategy'] = self.strategy_var.get()
            config['racing']['retry_race'] = self.retry_race_var.get()
            # Allowed multi-selects
            config['racing']['allowed_grades'] = [g for g, v in self.allowed_grades_vars.items() if v.get()]
            config['racing']['allowed_tracks'] = [t for t, v in self.allowed_tracks_vars.items() if v.get()]
            config['racing']['allowed_distances'] = [d for d, v in self.allowed_distances_vars.items() if v.get()]
            # Custom races
            config['racing']['do_custom_race'] = self.do_custom_race_var.get()
            config['racing']['custom_race_file'] = self.custom_race_file_var.get()
            
            self.main_window.set_config(config)
            messagebox.showinfo("Success", "Racing settings saved successfully!")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save racing settings: {e}")

    def toggle_custom_race_settings(self):
        """Show/hide custom race settings group"""
        if self.do_custom_race_var.get():
            self.custom_race_settings_frame.pack(fill=tk.X, padx=15, pady=(5, 10))
        else:
            self.custom_race_settings_frame.pack_forget()
        # Auto-save is already triggered by the variable trace
    
    def update_config(self, config):
        """Update the config dictionary with current values"""
        # Ensure racing section exists
        if 'racing' not in config:
            config['racing'] = {}
        
        config['racing']['strategy'] = self.strategy_var.get()
        config['racing']['retry_race'] = self.retry_race_var.get()
        # Allowed multi-selects
        config['racing']['allowed_grades'] = [g for g, v in self.allowed_grades_vars.items() if v.get()]
        config['racing']['allowed_tracks'] = [t for t, v in self.allowed_tracks_vars.items() if v.get()]
        config['racing']['allowed_distances'] = [d for d, v in self.allowed_distances_vars.items() if v.get()]
        # Custom races
        config['racing']['do_custom_race'] = self.do_custom_race_var.get()
        config['racing']['custom_race_file'] = self.custom_race_file_var.get()
    
    def on_racing_setting_change(self, *args):
        """Called when any racing setting variable changes - auto-save"""
        self.on_setting_change(*args)

    def open_custom_race_file(self):
        """Open file dialog to choose custom race file"""
        try:
            filename = filedialog.askopenfilename(
                title="Select Custom Race File",
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
                initialfile=self.custom_race_file_var.get(),
                parent=self.config_panel.winfo_toplevel()
            )
            if filename:
                self.custom_race_file_var.set(os.path.basename(filename))
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open file dialog: {e}")

    def open_custom_race_list_window(self):
        """Open the Custom Race List editor window"""
        try:
            # Load race data
            with open('assets/races/clean_race_data.json', 'r', encoding='utf-8') as f:
                all_races = json.load(f)
            # Load current selections; also use its keys to ensure all periods appear
            custom_file = self.custom_race_file_var.get() or 'custom_races.json'
            selections = {}
            period_order = []
            if os.path.exists(custom_file):
                with open(custom_file, 'r', encoding='utf-8') as f:
                    selections = json.load(f)
                    period_order = list(selections.keys())
            # Fallback to race data keys if no custom file
            if not period_order:
                period_order = list(all_races.keys())

            window = ctk.CTkToplevel(self.config_panel.winfo_toplevel())
            window.title("Edit Custom Race List")
            window.geometry("1000x700")
            window.configure(fg_color=self.colors['bg_dark'])
            try:
                window.transient(self.config_panel.winfo_toplevel())
            except Exception:
                pass
            window.lift()
            window.focus_force()
            try:
                window.attributes("-topmost", True)
                window.after(200, lambda: window.attributes("-topmost", False))
            except Exception:
                pass

            # Title
            ctk.CTkLabel(window, text="Custom Race List", font=get_font('title_medium'), text_color=self.colors['text_light']).pack(pady=(15, 10))

            # Content container
            content = ctk.CTkFrame(window, fg_color="transparent")
            content.pack(fill=tk.BOTH, expand=True, padx=15, pady=10)

            # Scrollable table area
            table_scroll = ctk.CTkScrollableFrame(content, fg_color=self.colors['bg_medium'], corner_radius=10)
            table_scroll.pack(fill=tk.BOTH, expand=True)

            # Filters frame
            filters_frame = ctk.CTkFrame(window, fg_color=self.colors['bg_light'], corner_radius=10)
            filters_frame.pack(fill=tk.X, padx=15, pady=(10, 10))
            ctk.CTkLabel(filters_frame, text="Filters", font=get_font('section_title'), text_color=self.colors['text_light']).pack(pady=(10,5))

            # Filter variables (pre-fill from current config)
            filter_grades_vars = {g: tk.BooleanVar(value=self.allowed_grades_vars.get(g, tk.BooleanVar(value=False)).get()) for g in ['G1','G2','G3','OP','Pre-OP']}
            filter_tracks_vars = {t: tk.BooleanVar(value=self.allowed_tracks_vars.get(t, tk.BooleanVar(value=False)).get()) for t in ['Turf','Dirt']}
            filter_dist_vars = {d: tk.BooleanVar(value=self.allowed_distances_vars.get(d, tk.BooleanVar(value=False)).get()) for d in ['Sprint','Mile','Medium','Long']}

            # Filters layout rows
            def build_filter_row(parent, label_text, options, vars_map):
                row = ctk.CTkFrame(parent, fg_color="transparent")
                row.pack(fill=tk.X, padx=15, pady=5)
                ctk.CTkLabel(row, text=label_text, text_color=self.colors['text_light'], font=get_font('label')).pack(side=tk.LEFT)
                checks = ctk.CTkFrame(row, fg_color="transparent")
                checks.pack(side=tk.RIGHT)
                for opt in options:
                    ctk.CTkCheckBox(checks, text=opt, variable=vars_map[opt], text_color=self.colors['text_light'], font=get_font('checkbox'), command=lambda: refresh_rows()).pack(side=tk.LEFT, padx=(0,6))

            build_filter_row(filters_frame, "Allowed Grades:", ['G1','G2','G3','OP','Pre-OP'], filter_grades_vars)
            build_filter_row(filters_frame, "Allowed Tracks:", ['Turf','Dirt'], filter_tracks_vars)
            build_filter_row(filters_frame, "Allowed Distances:", ['Sprint','Mile','Medium','Long'], filter_dist_vars)

            # Grade sort order
            grade_rank = {'G1': 5, 'G2': 4, 'G3': 3, 'OP': 2, 'Pre-OP': 1}

            # Row widgets storage
            row_vars = {}

            def race_passes_filters(r):
                return (
                    filter_grades_vars.get(r.get('grade',''), tk.BooleanVar(value=False)).get() and
                    filter_tracks_vars.get(r.get('surface',''), tk.BooleanVar(value=False)).get() and
                    filter_dist_vars.get(r.get('distance_type',''), tk.BooleanVar(value=False)).get()
                )

            def build_options_for_period(period, races_dict):
                options = []
                for name, r in races_dict.items():
                    if isinstance(r, dict) and race_passes_filters(r):
                        options.append((name, grade_rank.get(r.get('grade',''), 0)))
                # Sort by grade rank desc, then name
                options.sort(key=lambda x: (-x[1], x[0]))
                # Always include blank option to allow clearing selection
                return [''] + [name for name, _ in options]

            def refresh_rows():
                # Rebuild each dropdown's values based on current filters
                for period, widgets in row_vars.items():
                    race_names = build_options_for_period(period, all_races.get(period, {}))
                    widgets['menu'].configure(values=race_names)
                    # Keep current selection if still valid, else clear
                    current = widgets['var'].get()
                    if current not in race_names:
                        widgets['var'].set('')

            # Build table rows (periods from custom file order)
            for period in period_order:
                races = all_races.get(period, {})
                row = ctk.CTkFrame(table_scroll, fg_color=self.colors['bg_light'], corner_radius=8)
                row.pack(fill=tk.X, pady=4, padx=8)
                # Left: period label
                ctk.CTkLabel(row, text=period, text_color=self.colors['text_light'], width=260, anchor='w', font=get_font('label')).pack(side=tk.LEFT, padx=10, pady=8)
                # Middle: dropdown for race name (smaller width)
                middle = ctk.CTkFrame(row, fg_color="transparent")
                middle.pack(side=tk.LEFT, padx=10, pady=8)
                race_names = build_options_for_period(period, races)
                var = tk.StringVar(value=selections.get(period, ''))
                menu = ctk.CTkOptionMenu(middle, values=race_names, variable=var, command=lambda v, p=period: update_details_for(p), fg_color=self.colors['accent_blue'], corner_radius=8, button_color=self.colors['accent_blue'], button_hover_color=self.colors['accent_green'], width=200)
                menu.pack(side=tk.LEFT)
                # Right: details panel
                details = ctk.CTkFrame(row, fg_color=self.colors['bg_medium'], corner_radius=6)
                details.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=10)
                # Layout containers
                top_details = ctk.CTkFrame(details, fg_color="transparent")
                top_details.pack(fill=tk.X, padx=8, pady=4)
                bottom_details = ctk.CTkFrame(details, fg_color="transparent")
                bottom_details.pack(fill=tk.X, padx=8, pady=(0,8))
                # Create labels with correct parents
                detail_labels = {
                    'grade': ctk.CTkLabel(top_details, text="", text_color=self.colors['text_gray']),
                    'surface': ctk.CTkLabel(top_details, text="", text_color=self.colors['text_gray']),
                    'distance_type': ctk.CTkLabel(top_details, text="", text_color=self.colors['text_gray']),
                    'distance_meters': ctk.CTkLabel(top_details, text="", text_color=self.colors['text_gray']),
                    'racetrack': ctk.CTkLabel(bottom_details, text="", text_color=self.colors['text_gray']),
                    'direction': ctk.CTkLabel(bottom_details, text="", text_color=self.colors['text_gray']),
                    'season': ctk.CTkLabel(bottom_details, text="", text_color=self.colors['text_gray']),
                    'time_of_day': ctk.CTkLabel(bottom_details, text="", text_color=self.colors['text_gray'])
                }
                for key in ['grade','surface','distance_type','distance_meters']:
                    detail_labels[key].pack(side=tk.LEFT, padx=8)
                for key in ['racetrack','direction','season','time_of_day']:
                    detail_labels[key].pack(side=tk.LEFT, padx=8)

                row_vars[period] = {'var': var, 'menu': menu, 'details': detail_labels}
                # Trace changes to update details
                def make_trace(p):
                    return lambda *args: update_details_for(p)
                var.trace_add('write', make_trace(period))

            def update_details_for(period):
                widgets = row_vars.get(period)
                if not widgets:
                    return
                name = widgets['var'].get()
                race = all_races.get(period, {}).get(name, {}) if name else {}
                def fmt(k, v):
                    return f"{k}: {v}" if v not in (None, '', []) else f"{k}: -"
                labels = widgets['details']
                labels['grade'].configure(text=fmt('Grade', race.get('grade')))
                labels['surface'].configure(text=fmt('Surface', race.get('surface')))
                labels['distance_type'].configure(text=fmt('Type', race.get('distance_type')))
                labels['distance_meters'].configure(text=fmt('Meters', race.get('distance_meters')))
                labels['racetrack'].configure(text=fmt('Track', race.get('racetrack')))
                labels['direction'].configure(text=fmt('Direction', race.get('direction')))
                labels['season'].configure(text=fmt('Season', race.get('season')))
                labels['time_of_day'].configure(text=fmt('Time', race.get('time_of_day')))

            # Initialize details for current selections (and attach selection change handler command to existing value)
            for p, widgets in row_vars.items():
                # Ensure dropdown has a command too, in case the trace misses
                try:
                    widgets['menu'].configure(command=lambda v, p=p: update_details_for(p))
                except Exception:
                    pass
                update_details_for(p)

            # Save and Close buttons
            btns = ctk.CTkFrame(window, fg_color="transparent")
            btns.pack(fill=tk.X, padx=15, pady=(0, 15))

            def save_custom_races():
                try:
                    out = {period: widgets['var'].get() for period, widgets in row_vars.items()}
                    with open(custom_file, 'w', encoding='utf-8') as f:
                        json.dump(out, f, indent=2, ensure_ascii=False)
                    messagebox.showinfo("Success", f"Custom races saved to {custom_file}")
                    window.destroy()
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to save custom races: {e}")

            ctk.CTkButton(btns, text="Save", command=save_custom_races, fg_color=self.colors['accent_green'], corner_radius=8, height=32, width=100).pack(side=tk.RIGHT, padx=(5,0))
            ctk.CTkButton(btns, text="Close", command=window.destroy, fg_color=self.colors['accent_red'], corner_radius=8, height=32, width=100).pack(side=tk.RIGHT)

            # Initial refresh to ensure filters applied
            refresh_rows()

        except Exception as e:
            messagebox.showerror("Error", f"Failed to open Custom Race List window: {e}")
