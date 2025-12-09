"""
Helper functions for skill list management in the Skill Tab
"""

import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
import json
import os

try:
    from ..font_manager import get_font
except ImportError:
    from font_manager import get_font

def open_skill_list_window(skill_tab_instance):
    """Open window to edit skill lists"""
    try:
        # Load current skill data
        skill_file = skill_tab_instance.get_skill_file_path()
        if not os.path.exists(skill_file):
            messagebox.showerror("Error", f"Skill file {skill_file} not found!")
            return
        
        with open(skill_file, 'r', encoding='utf-8') as f:
            skill_data = json.load(f)
        
        # Create new window
        window = ctk.CTkToplevel(skill_tab_instance.config_panel.winfo_toplevel())
        window.title("Edit Skill Lists")
        window.geometry("800x600")
        window.configure(fg_color=skill_tab_instance.colors['bg_dark'])
        try:
            window.transient(skill_tab_instance.config_panel.winfo_toplevel())
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
        title_label = ctk.CTkLabel(window, text="Edit Skill Lists", font=get_font('title_medium'), 
                                  text_color=skill_tab_instance.colors['text_light'])
        title_label.pack(pady=(15, 10))
        
        # Main content frame
        content_frame = ctk.CTkFrame(window, fg_color="transparent")
        content_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=10)
        
        # Create skill list interface
        create_skill_lists_interface(content_frame, skill_data, skill_tab_instance, window, skill_file)
        
    except Exception as e:
        messagebox.showerror("Error", f"Failed to open skill list window: {e}")

def create_skill_lists_interface(parent, skill_data, skill_tab, window, skill_file):
    """Create the skill lists interface"""
    # Left side - Priority Skills
    left_frame = ctk.CTkFrame(parent, fg_color=skill_tab.colors['bg_medium'], corner_radius=10)
    left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
    
    ctk.CTkLabel(left_frame, text="Priority Skills", font=get_font('section_title'), 
                text_color=skill_tab.colors['text_light']).pack(pady=(15, 10))
    
    # Priority skills listbox
    priority_listbox = tk.Listbox(left_frame, bg=skill_tab.colors['bg_light'], fg=skill_tab.colors['text_light'], 
                                selectmode=tk.SINGLE, font=get_font('body_large'))
    priority_listbox.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 15))
    
    priority_skills = skill_data.get('skill_priority', [])
    for i, skill in enumerate(priority_skills, 1):
        priority_listbox.insert(tk.END, f"{i}. {skill}")
    
    # Priority skills buttons
    priority_btn_frame = ctk.CTkFrame(left_frame, fg_color="transparent")
    priority_btn_frame.pack(fill=tk.X, padx=15, pady=(0, 15))
    
    ctk.CTkButton(priority_btn_frame, text="Add", 
                 command=lambda: add_priority_skill(priority_listbox, priority_skills),
                 fg_color=skill_tab.colors['accent_green'], corner_radius=8, 
                 font=get_font('button')).pack(side=tk.LEFT, padx=(0, 5))
    ctk.CTkButton(priority_btn_frame, text="Remove", 
                 command=lambda: remove_priority_skill(priority_listbox, priority_skills),
                 fg_color=skill_tab.colors['accent_red'], corner_radius=8).pack(side=tk.LEFT, padx=(0, 5))
    ctk.CTkButton(priority_btn_frame, text="↑", 
                 command=lambda: move_priority_skill(priority_listbox, priority_skills, -1),
                 fg_color=skill_tab.colors['accent_blue'], corner_radius=8, width=40).pack(side=tk.LEFT, padx=(0, 5))
    ctk.CTkButton(priority_btn_frame, text="↓", 
                 command=lambda: move_priority_skill(priority_listbox, priority_skills, 1),
                 fg_color=skill_tab.colors['accent_blue'], corner_radius=8, width=40).pack(side=tk.LEFT, padx=(0, 5))
    
    # Right side - Gold Skill Relationships
    right_frame = ctk.CTkFrame(parent, fg_color=skill_tab.colors['bg_medium'], corner_radius=10)
    right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))
    
    ctk.CTkLabel(right_frame, text="Gold Skill Relationships", font=get_font('section_title'), 
                text_color=skill_tab.colors['text_light']).pack(pady=(15, 10))
    
    # Gold skill relationships frame
    gold_frame = ctk.CTkFrame(right_frame, fg_color=skill_tab.colors['bg_light'], corner_radius=8)
    gold_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 15))
    
    # Headers
    header_frame = ctk.CTkFrame(gold_frame, fg_color="transparent")
    header_frame.pack(fill=tk.X, padx=10, pady=5)
    ctk.CTkLabel(header_frame, text="Gold Skill", font=get_font('body_large'), 
                text_color=skill_tab.colors['text_gray']).pack(side=tk.LEFT)
    ctk.CTkLabel(header_frame, text="Base Skill", font=get_font('body_large'), 
                text_color=skill_tab.colors['text_gray']).pack(side=tk.RIGHT)
    
    # Gold skill relationships listbox
    gold_listbox = tk.Listbox(gold_frame, bg=skill_tab.colors['bg_light'], fg=skill_tab.colors['text_light'], 
                            selectmode=tk.SINGLE, font=get_font('body_medium'))
    gold_listbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
    
    gold_relationships = skill_data.get('gold_skill_upgrades', {})
    for gold_skill, base_skill in gold_relationships.items():
        gold_listbox.insert(tk.END, f"{gold_skill} → {base_skill}")
    
    # Gold skill buttons
    gold_btn_frame = ctk.CTkFrame(right_frame, fg_color="transparent")
    gold_btn_frame.pack(fill=tk.X, padx=15, pady=(0, 15))
    
    ctk.CTkButton(gold_btn_frame, text="Add", 
                 command=lambda: add_gold_relationship(gold_listbox, gold_relationships),
                 fg_color=skill_tab.colors['accent_green'], corner_radius=8).pack(side=tk.LEFT, padx=(0, 5))
    ctk.CTkButton(gold_btn_frame, text="Remove", 
                 command=lambda: remove_gold_relationship(gold_listbox, gold_relationships),
                 fg_color=skill_tab.colors['accent_red'], corner_radius=8).pack(side=tk.LEFT, padx=(0, 5))
    
    # Save button
    save_btn = ctk.CTkButton(window, text="Save All Changes", 
                           command=lambda: save_skill_lists(window, skill_file, priority_skills, gold_relationships),
                           fg_color=skill_tab.colors['accent_green'], corner_radius=8, height=35)
    save_btn.pack(pady=(0, 15))

def add_priority_skill(listbox, skills):
    """Add a new priority skill"""
    dialog = ctk.CTkInputDialog(text="Enter new skill:", title="Add Priority Skill")
    skill = dialog.get_input()
    if skill and skill.strip():
        skills.append(skill.strip())
        listbox.insert(tk.END, f"{len(skills)}. {skill.strip()}")

def remove_priority_skill(listbox, skills):
    """Remove selected priority skill"""
    selection = listbox.curselection()
    if selection:
        index = selection[0]
        skills.pop(index)
        # Refresh listbox
        listbox.delete(0, tk.END)
        for i, skill in enumerate(skills, 1):
            listbox.insert(tk.END, f"{i}. {skill}")

def move_priority_skill(listbox, skills, direction):
    """Move priority skill up or down"""
    selection = listbox.curselection()
    if selection:
        index = selection[0]
        new_index = index + direction
        if 0 <= new_index < len(skills):
            skills[index], skills[new_index] = skills[new_index], skills[index]
            # Refresh listbox
            listbox.delete(0, tk.END)
            for i, skill in enumerate(skills, 1):
                listbox.insert(tk.END, f"{i}. {skill}")
            listbox.selection_set(new_index)

def add_gold_relationship(listbox, relationships):
    """Add a new gold skill relationship"""
    dialog = ctk.CTkInputDialog(text="Enter gold skill:", title="Add Gold Skill")
    gold_skill = dialog.get_input()
    if gold_skill and gold_skill.strip():
        dialog2 = ctk.CTkInputDialog(text="Enter base skill:", title="Add Base Skill")
        base_skill = dialog2.get_input()
        if base_skill and base_skill.strip():
            relationships[gold_skill.strip()] = base_skill.strip()
            listbox.insert(tk.END, f"{gold_skill.strip()} → {base_skill.strip()}")

def remove_gold_relationship(listbox, relationships):
    """Remove selected gold skill relationship"""
    selection = listbox.curselection()
    if selection:
        index = selection[0]
        item = listbox.get(index)
        gold_skill = item.split(" → ")[0]
        if gold_skill in relationships:
            del relationships[gold_skill]
            listbox.delete(index)

def save_skill_lists(window, skill_file, priority_skills, gold_relationships):
    """Save skill lists to file"""
    try:
        skill_data = {
            "skill_priority": priority_skills,
            "gold_skill_upgrades": gold_relationships
        }
        
        with open(skill_file, 'w', encoding='utf-8') as f:
            json.dump(skill_data, f, indent=4, ensure_ascii=False)
        
        messagebox.showinfo("Success", "Skill lists saved successfully!")
        window.destroy()
        
    except Exception as e:
        messagebox.showerror("Error", f"Failed to save skill lists: {e}")
