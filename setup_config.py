#!/usr/bin/env python3
"""
Configuration Setup Script for Uma Musume Auto Trainer

This script helps users set up their configuration files by copying the example templates.
This prevents conflicts when pulling updates from the repository.
"""

import os
import shutil
import sys

def copy_example_files():
    """Copy example configuration files to working copies"""
    
    config_files = [
        ('config.example.json', 'config.json'),
        ('event_priority.example.json', 'event_priority.json'),
        ('training_score.example.json', 'training_score.json')
    ]
    
    print("Uma Musume Auto Trainer - Configuration Setup")
    print("=" * 50)
    
    for example_file, target_file in config_files:
        if os.path.exists(example_file):
            if os.path.exists(target_file):
                print(f"⚠️  {target_file} already exists. Skipping...")
            else:
                try:
                    shutil.copy2(example_file, target_file)
                    print(f"✅ Created {target_file} from {example_file}")
                except Exception as e:
                    print(f"❌ Error copying {example_file}: {e}")
        else:
            print(f"❌ {example_file} not found!")
    
    print("\n" + "=" * 50)
    print("Configuration setup complete!")
    print("\nNext steps:")
    print("1. Edit the copied .json files to customize your settings")
    print("2. Your customizations will be preserved when pulling updates")
    print("3. Run the bot with: python main_adb.py")
    print("\nNote: The .example files are templates and won't be modified.")

if __name__ == "__main__":
    copy_example_files()
