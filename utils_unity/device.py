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

def run_adb(command, binary=False, add_input_delay=True):
    """
    Execute an ADB command using settings from config.json (adb_config).

    Args:
        command: list[str] like ['shell','input','tap','x','y']
        binary: when True, return raw bytes stdout
        add_input_delay: if True, sleep input_delay when invoking 'input' commands

    Returns:
        str|bytes|None: stdout text (default) or bytes (when binary=True) on success; None on error
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

        if add_input_delay and 'input' in command:
            time.sleep(input_delay)

        result = subprocess.run(full_cmd, capture_output=True, check=True)
        return result.stdout if binary else result.stdout.decode(errors='ignore').strip()
    except subprocess.CalledProcessError as e:
        log_error(f"ADB command failed: {e}")
        return None
    except Exception as e:
        log_error(f"Error running ADB command: {e}")
        return None


