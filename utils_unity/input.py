import subprocess
import time
import json
from utils.device import run_adb
from utils.recognizer import locate_on_screen

from utils.log import log_info, log_warning, log_error, log_debug, log_success
def load_config():
    """Load ADB configuration from config.json"""
    try:
        with open('config.json', 'r') as f:
            config = json.load(f)
            return config.get('adb_config', {})
    except Exception as e:
        log_error(f"Error loading config: {e}")
        return {}

def tap(x, y):
    """Tap at coordinates (x, y)"""
    return run_adb(['shell', 'input', 'tap', str(x), str(y)])

def swipe(start_x, start_y, end_x, end_y, duration_ms=100):
    """Swipe from (start_x, start_y) to (end_x, end_y) with duration in milliseconds"""
    return run_adb(['shell', 'input', 'swipe', str(start_x), str(start_y), str(end_x), str(end_y), str(duration_ms)])

def long_press(x, y, duration_ms=1000):
    """Long press at coordinates (x, y) for duration_ms milliseconds"""
    return swipe(x, y, x, y, duration_ms)

def triple_click(x, y, interval=0.1):
    """Perform triple click at coordinates (x, y)"""
    for i in range(3):
        tap(x, y)
        if i < 2:  # Don't wait after the last click
            time.sleep(interval)

def tap_on_image(img, confidence=0.8, min_search=1, text="", region=None):
    """Find image on screen and tap on it with retry logic"""
    for attempt in range(int(min_search)):
        btn = locate_on_screen(img, confidence=confidence, region=region)
        if btn:
            if text:
                log_info(text)
            tap(btn[0], btn[1])
            return True
        if attempt < int(min_search) - 1:  # Don't sleep on last attempt
            time.sleep(0.05)
    return False 