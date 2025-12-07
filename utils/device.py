import subprocess
import time
import json
from utils.log import log_debug, log_info, log_warning, log_error

def _load_adb_config():
    try:
        with open('config.json', 'r', encoding='utf-8') as f:
            cfg = json.load(f)
        return cfg.get('adb_config', {})
    except Exception:
        return {}

def run_adb(command, binary=False, add_input_delay=False):
    """
    Execute an ADB command using settings from config.json (adb_config).

    Args:
        command: list[str] like ['shell','input','tap','x','y']
        binary: when True, return raw bytes stdout
        add_input_delay: if True, sleep input_delay when invoking 'input' commands
                         Set to False to skip delay (faster but may cause input conflicts on some emulators)

    Returns:
        str|bytes|None: stdout text (default) or bytes (when binary=True) on success; None on error
    
    Note:
        input_delay exists to prevent input conflicts when sending rapid commands to emulators.
        Some emulators may drop or ignore inputs if sent too quickly. However, modern emulators
        (LDPlayer, Nemu, etc.) often work fine without delay. You can:
        - Set input_delay to 0.0 in config.json to disable globally
        - Use add_input_delay=False for specific calls that need speed
        - Reduce input_delay to 0.05-0.1s for a balance between speed and reliability
    """
    try:
        adb_cfg = _load_adb_config()
        adb_path = adb_cfg.get('adb_path', 'adb')
        device_address = adb_cfg.get('device_address', '')
        input_delay = float(adb_cfg.get('input_delay', 0.5))

        full_cmd = [adb_path]
        if device_address:
            full_cmd.extend(['-s', device_address])
        full_cmd.extend(command)

        # Only apply delay if requested and delay > 0
        if add_input_delay and 'input' in command and input_delay > 0:
            time.sleep(input_delay)

        result = subprocess.run(full_cmd, capture_output=True, check=True)
        return result.stdout if binary else result.stdout.decode(errors='ignore').strip()
    except subprocess.CalledProcessError as e:
        log_error(f"ADB command failed: {e}")
        return None
    except Exception as e:
        log_error(f"Error running ADB command: {e}")
        return None


