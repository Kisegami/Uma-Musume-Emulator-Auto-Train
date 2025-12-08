"""
Setup script for Uma Musume Auto-Train Bot
Checks system requirements and installs dependencies
"""
import sys
import os
import subprocess
import platform
from pathlib import Path

def print_header(text):
    """Print a formatted header"""
    print("\n" + "=" * 60)
    print(f"  {text}")
    print("=" * 60)

def print_success(text):
    """Print success message"""
    print(f"✓ {text}")

def print_error(text):
    """Print error message"""
    print(f"✗ {text}")

def print_warning(text):
    """Print warning message"""
    print(f"⚠ {text}")

def print_info(text):
    """Print info message"""
    print(f"  {text}")

# Note: Python version, Git, and requirements.txt checks are done by setup.bat
# This script only handles things that batch scripts can't do easily

def install_dependencies():
    """Install Python dependencies from requirements.txt"""
    print_header("Installing Dependencies")
    
    if not os.path.exists('requirements.txt'):
        print_error("requirements.txt not found")
        return False
    
    print_info("Installing packages from requirements.txt...")
    print_info("This may take a few minutes...")
    
    try:
        # Use pip to install requirements
        result = subprocess.run(
            [sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'],
            capture_output=False,
            text=True
        )
        
        if result.returncode == 0:
            print_success("All dependencies installed successfully")
            return True
        else:
            print_error("Failed to install some dependencies")
            print_info("Try running manually: pip install -r requirements.txt")
            return False
            
    except Exception as e:
        print_error(f"Error installing dependencies: {e}")
        return False

def check_adbutils():
    """Check if adbutils is installed and working"""
    print_header("Checking ADB (via adbutils)")
    
    try:
        import adbutils
        print_success(f"adbutils is installed (version: {getattr(adbutils, '__version__', 'unknown')})")
        
        # Check for bundled ADB
        import site
        site_packages = site.getsitepackages()
        
        adb_found = False
        for site_pkg in site_packages:
            adb_path = Path(site_pkg) / 'adbutils' / 'binaries' / 'adb.exe'
            if adb_path.exists():
                print_success(f"Bundled ADB found: {adb_path}")
                adb_found = True
                break
        
        if not adb_found:
            # Check relative to Python executable
            python_dir = Path(sys.executable).parent
            adb_path = python_dir / 'Lib' / 'site-packages' / 'adbutils' / 'binaries' / 'adb.exe'
            if adb_path.exists():
                print_success(f"Bundled ADB found: {adb_path}")
                adb_found = True
        
        if not adb_found:
            print_warning("ADB binary not found in adbutils")
            print_info("This might be normal - adbutils should include it")
        
        return True
        
    except ImportError:
        print_error("adbutils is not installed")
        print_info("It should be installed from requirements.txt")
        return False

def check_config_files():
    """Check if config files exist, create from examples if needed"""
    print_header("Checking Configuration Files")
    
    config_files = {
        'config.json': 'config.example.json',
        'event_priority.json': 'event_priority.example.json',
        'training_score.json': 'training_score.example.json',
    }
    
    created = []
    for config_file, example_file in config_files.items():
        if os.path.exists(config_file):
            print_success(f"{config_file} exists")
        elif os.path.exists(example_file):
            try:
                import shutil
                shutil.copy(example_file, config_file)
                print_success(f"Created {config_file} from {example_file}")
                created.append(config_file)
            except Exception as e:
                print_error(f"Failed to create {config_file}: {e}")
        else:
            print_warning(f"{config_file} not found and no example file available")
    
    return len(created) > 0

def main():
    """Main setup function (called by setup.bat)
    
    Note: setup.bat handles:
    - Python version check (3.11.x)
    - Git check (bundled or system)
    - requirements.txt existence check
    
    This script only handles things batch can't do:
    - Installing Python dependencies
    - Checking adbutils installation
    - Creating config files
    """
    print_header("Installing Dependencies and Checking Setup")
    
    all_checks_passed = True
    
    # Install dependencies (batch can't do pip install easily)
    if not install_dependencies():
        all_checks_passed = False
        print_warning("Some dependencies may not be installed correctly")
    
    # Check adbutils (requires Python imports)
    check_adbutils()
    
    # Check config files (requires file operations)
    check_config_files()
    
    # Summary
    print_header("Setup Summary")
    
    if all_checks_passed:
        print_success("Setup completed successfully!")
        return True
    else:
        print_warning("Setup completed with some issues")
        print_info("Please review the messages above and fix any errors")
        return False

if __name__ == '__main__':
    # This script is designed to be called by setup.bat on Windows
    # It can be run standalone, but setup.bat is the recommended way
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nSetup interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nSetup failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

