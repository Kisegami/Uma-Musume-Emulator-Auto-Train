#!/usr/bin/env python3
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

# Add script's directory to Python path (for embeddable Python compatibility)
# This ensures utils/ and other modules can be found regardless of how Python is invoked
# Handle case where __file__ might not be defined (e.g., when executed via exec)
if '__file__' in globals():
    script_dir = os.path.dirname(os.path.abspath(__file__))
else:
    # Fallback: use current working directory or sys.argv[0] if available
    script_dir = os.path.dirname(os.path.abspath(sys.argv[0])) if sys.argv else os.getcwd()
if script_dir and script_dir not in sys.path:
    sys.path.insert(0, script_dir)

import json
from utils.log import log_info, log_warning, log_error, log_debug, log_success
from utils.config_loader import load_main_config
from utils.emulator_detect import list_emulator_types

def main():
    """Main launcher function"""
    print("Uma Musume Auto-Train Bot - GUI Launcher")
    print("=" * 50)
    
    # Check for updates before starting GUI
    try:
        # Load config
        config = load_main_config() if os.path.exists('config.json') else {}
        
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
        
        created = config_summary.get("created", 0)
        updated = config_summary.get("updated", 0)
        errors = config_summary.get("errors", 0)

        if created:
            print(f"✓ Created {created} new configuration files")
        if updated:
            print(f"✓ Updated {updated} configuration files with missing keys")
        if errors:
            print(f"⚠ {errors} errors occurred during config creation")
        
    except Exception as e:
        print(f"Warning: Could not check configuration files: {e}")
        print("GUI will continue without automatic config file creation.")
    
    # Detect emulator types up front and pass via environment
    try:
        detected_types = list_emulator_types()
        os.environ["UMA_DETECTED_EMULATOR_TYPES"] = json.dumps(detected_types)
        print(f"Detected emulator types: {detected_types}")
    except Exception as e:
        print(f"Warning: Emulator detection failed: {e}")
        os.environ.pop("UMA_DETECTED_EMULATOR_TYPES", None)
    
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

