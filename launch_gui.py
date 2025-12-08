#!/usr/bin/env python3
from utils.log import log_info, log_warning, log_error, log_debug, log_success
"""
Uma Musume Auto-Train Bot - GUI Launcher (Root Directory)

This script launches the redesigned GUI application from the root directory.
Simply run this file to start the new dark-themed GUI.

Usage:
    python launch_gui.py
    or
    python3 launch_gui.py
"""

import sys
import os
import json

def main():
    """Main launcher function"""
    print("Uma Musume Auto-Train Bot - GUI Launcher")
    print("=" * 50)
    
    # Check for updates before starting GUI
    try:
        # Load config
        if os.path.exists('config.json'):
            with open('config.json', 'r', encoding='utf-8') as f:
                config = json.load(f)
        else:
            config = {}
        
        update_config = config.get('update', {})
        auto_update = update_config.get('auto_update', False)
        install_dependencies = update_config.get('install_dependencies', True)
        branch = update_config.get('branch', 'main')
        remote = update_config.get('remote', 'origin')
        
        # Check and update
        from utils.updater import check_and_update
        if check_and_update(branch=branch, remote=remote, auto_update=auto_update, install_dependencies=install_dependencies):
            log_info("Application was updated. Please restart to use the new version.")
            input("Press Enter to exit...")
            sys.exit(0)
    except Exception as e:
        log_warning(f"Could not check for updates: {e}")
        log_info("Continuing without update check...")
    
    # Check if GUI directory exists
    if not os.path.exists('gui'):
        print("Error: GUI directory not found!")
        print("Please ensure you're running this from the correct directory.")
        input("Press Enter to exit...")
        sys.exit(1)
    
    # Add GUI directory to Python path
    gui_path = os.path.join(os.getcwd(), 'gui')
    sys.path.insert(0, gui_path)
    
    # Check configuration files before starting GUI
    try:
        from gui.config_checker import check_configs_from_gui
        print("Checking configuration files...")
        config_summary = check_configs_from_gui()
        
        if config_summary['created']:
            print(f"✓ Created {len(config_summary['created'])} new configuration files")
        if config_summary['updated']:
            print(f"✓ Updated {len(config_summary['updated'])} configuration files with missing keys")
        if config_summary['errors']:
            print(f"⚠ {len(config_summary['errors'])} errors occurred during config creation")
        
    except Exception as e:
        print(f"Warning: Could not check configuration files: {e}")
        print("GUI will continue without automatic config file creation.")
    
    try:
        # Import and run the GUI
        from gui.launch_gui import main as gui_main
        gui_main()
        
    except Exception as e:
        print(f"Error starting GUI: {e}")
        print("\nPlease check the error message above and try again.")
        input("Press Enter to exit...")
        sys.exit(1)

if __name__ == "__main__":
    main()

