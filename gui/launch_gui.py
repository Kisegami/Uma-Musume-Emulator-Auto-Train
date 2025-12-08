#!/usr/bin/env python3
"""
Uma Musume Auto-Train Bot - New GUI Launcher

This script launches the redesigned GUI application with dark theme.
Simply run this file to start the graphical interface.

Usage:
    python gui/launch_gui.py
    or
    python3 gui/launch_gui.py
"""

import sys
import os

def check_python_version():
    """Check if Python version is compatible"""
    if sys.version_info < (3, 7):
        print("Error: Python 3.7 or higher is required!")
        print(f"Current version: {sys.version}")
        input("Press Enter to exit...")
        sys.exit(1)

def check_tkinter():
    """Check if tkinter is available"""
    try:
        import tkinter
        return True
    except ImportError:
        print("Error: tkinter is not available!")
        print("Please install Python with tkinter support.")
        input("Press Enter to exit...")
        return False

def check_gui_files():
    """Check if all required GUI files exist"""
    required_files = [
        'gui/__init__.py',
        'gui/main_window.py',
        'gui/config_panel.py',
        'gui/status_panel.py',
        'gui/log_panel.py',
        'gui/bot_controller.py'
    ]
    
    missing_files = []
    for file_path in required_files:
        if not os.path.exists(file_path):
            missing_files.append(file_path)
    
    if missing_files:
        print("Error: The following required GUI files are missing:")
        for file_path in missing_files:
            print(f"  - {file_path}")
        print("\nPlease ensure you're running this from the correct directory.")
        input("Press Enter to exit...")
        return False
    
    return True


def check_configuration_files():
    """Check and create configuration files if needed"""
    try:
        from gui.config_checker import check_configs_from_gui
        config_summary = check_configs_from_gui()
        
        print(f"Configuration files check:")
        print(f"  - Total required: {config_summary['total_required']}")
        print(f"  - Existing: {config_summary['existing']}")
        print(f"  - Created: {config_summary['created']}")
        if 'updated' in config_summary:
            print(f"  - Updated: {config_summary['updated']}")
        
        if config_summary['created']:
            print("  ✓ New configuration files created from examples")
        
        if 'updated' in config_summary and config_summary['updated']:
            print("  ✓ Configuration files updated with missing keys from examples")
        
        if config_summary['errors']:
            print("  ⚠ Some errors occurred during config file creation:")
            for error in config_summary['errors']:
                print(f"    - {error}")
        
        if config_summary['invalid']:
            print("  ⚠ Some configuration files have invalid JSON:")
            for invalid in config_summary['invalid']:
                print(f"    - {invalid}")
        
        return True
        
    except ImportError:
        print("Warning: Could not import config checker module")
        print("Configuration files will not be automatically created.")
        return False
    except Exception as e:
        print(f"Error checking configuration files: {e}")
        return False

def main():
    """Main launcher function"""
    print("Uma Musume Auto-Train Bot - New GUI Launcher")
    print("=" * 50)
    
    # Check Python version
    check_python_version()
    print("✓ Python version check passed")
    
    # Check tkinter availability
    if not check_tkinter():
        sys.exit(1)
    print("✓ tkinter availability check passed")
    
    # Check if GUI files exist
    if not check_gui_files():
        sys.exit(1)
    print("✓ GUI files check passed")
    
    # Check and create configuration files if needed
    check_configuration_files()
    print("✓ Configuration files check completed")
    
    print("\nStarting new GUI application...")
    print("=" * 50)
    
    try:
        # Import and run the GUI
        try:
            from gui.main_window import main as gui_main
        except ImportError:
            from main_window import main as gui_main
        gui_main()
    except Exception as e:
        print(f"Error starting GUI: {e}")
        print("\nPlease check the error message above and try again.")
        input("Press Enter to exit...")
        sys.exit(1)

if __name__ == "__main__":
    main()
