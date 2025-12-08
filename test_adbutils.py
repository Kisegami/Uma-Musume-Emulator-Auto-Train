"""
Simple test script to verify adbutils is working correctly
"""
import sys
import os
from pathlib import Path

def test_adbutils():
    """Test adbutils installation and functionality"""
    print("=" * 60)
    print("ADB Utils Test")
    print("=" * 60)
    print()
    
    # Test 1: Check if adbutils is installed
    print("Test 1: Checking if adbutils is installed...")
    try:
        import adbutils
        print(f"✓ adbutils imported successfully")
        print(f"  Version: {adbutils.__version__ if hasattr(adbutils, '__version__') else 'unknown'}")
    except ImportError as e:
        print(f"✗ adbutils not installed: {e}")
        print("  Install with: pip install adbutils==0.11.0")
        return False
    print()
    
    # Test 2: Check if ADB binary is available
    print("Test 2: Checking for ADB binary...")
    adb_path = None
    
    # Try to find bundled ADB from adbutils
    try:
        import site
        site_packages = site.getsitepackages()
        
        for site_pkg in site_packages:
            adb_exe = Path(site_pkg) / 'adbutils' / 'binaries' / 'adb.exe'
            if adb_exe.exists():
                adb_path = str(adb_exe)
                print(f"✓ Found bundled ADB: {adb_path}")
                break
            
            # Linux/Mac
            adb_bin = Path(site_pkg) / 'adbutils' / 'binaries' / 'adb'
            if adb_bin.exists() and os.access(adb_bin, os.X_OK):
                adb_path = str(adb_bin)
                print(f"✓ Found bundled ADB: {adb_path}")
                break
        
        # Check relative to current Python executable (for venv)
        if not adb_path:
            python_dir = Path(sys.executable).parent
            adb_exe = python_dir / 'Lib' / 'site-packages' / 'adbutils' / 'binaries' / 'adb.exe'
            if adb_exe.exists():
                adb_path = str(adb_exe)
                print(f"✓ Found bundled ADB: {adb_path}")
            
            if not adb_path:
                adb_bin = python_dir / 'lib' / f'python{sys.version_info.major}.{sys.version_info.minor}' / 'site-packages' / 'adbutils' / 'binaries' / 'adb'
                if adb_bin.exists() and os.access(adb_bin, os.X_OK):
                    adb_path = str(adb_bin)
                    print(f"✓ Found bundled ADB: {adb_path}")
        
    except Exception as e:
        print(f"⚠ Error searching for bundled ADB: {e}")
    
    # Fallback to system ADB
    if not adb_path:
        import shutil
        system_adb = shutil.which('adb')
        if system_adb:
            adb_path = system_adb
            print(f"✓ Found system ADB: {adb_path}")
        else:
            print("✗ ADB binary not found")
            print("  adbutils should include ADB, but it's not found")
            print("  Make sure adbutils is properly installed: pip install adbutils==0.11.0")
            return False
    print()
    
    # Test 3: Test ADB version
    print("Test 3: Testing ADB version...")
    try:
        import subprocess
        result = subprocess.run(
            [adb_path, 'version'],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            print(f"✓ ADB is working")
            print(f"  {result.stdout.strip()}")
        else:
            print(f"✗ ADB version check failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"✗ Error testing ADB: {e}")
        return False
    print()
    
    # Test 4: List connected devices
    print("Test 4: Checking for connected devices...")
    try:
        result = subprocess.run(
            [adb_path, 'devices'],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')[1:]  # Skip header
            devices = [line for line in lines if line.strip() and '\tdevice' in line]
            
            if devices:
                print(f"✓ Found {len(devices)} connected device(s):")
                for device in devices:
                    print(f"  - {device.split()[0]}")
            else:
                print("⚠ No devices connected")
                print("  This is normal if no emulator/device is running")
                print("  ADB is working, but you need to connect a device to use it")
        else:
            print(f"⚠ ADB devices command failed: {result.stderr}")
    except Exception as e:
        print(f"⚠ Error checking devices: {e}")
    print()
    
    # Test 5: Test adbutils API
    print("Test 5: Testing adbutils API...")
    try:
        from adbutils import adb
        
        # Try to get devices using adbutils
        devices = list(adb.device_list())
        print("✓ adbutils API is accessible")
        
        if devices:
            print(f"✓ Found {len(devices)} device(s) via adbutils API:")
            for device in devices:
                print(f"  - {device.serial}")
        else:
            print("⚠ No devices found via adbutils API")
            print("  This is normal if no emulator/device is running")
    except Exception as e:
        print(f"⚠ Error testing adbutils API: {e}")
        print("  This might be normal if no devices are connected")
    print()
    
    # Summary
    print("=" * 60)
    print("Test Summary")
    print("=" * 60)
    print("✓ adbutils is installed")
    print("✓ ADB binary is available")
    print("✓ ADB is working")
    print()
    print("Note: If no devices are shown, make sure:")
    print("  1. Your emulator/device is running")
    print("  2. ADB debugging is enabled")
    print("  3. Device is connected via ADB")
    print()
    
    return True

if __name__ == '__main__':
    try:
        success = test_adbutils()
        if success:
            print("All tests passed! ✓")
            sys.exit(0)
        else:
            print("Some tests failed! ✗")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nTest failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

