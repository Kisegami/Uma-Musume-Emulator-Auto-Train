import time

from PIL import ImageStat

from core.config import Config
from core.event_handling import debug_print
from core.templates_adb import BACK_BUTTON_TEMPLATE, INFIRMARY_BUTTON_TEMPLATE, RECREATION_BUTTON_TEMPLATE, REST_BUTTON_TEMPLATE, REST_SUMMER_BUTTON_TEMPLATE
from utils.adb_recognizer import locate_on_screen, match_template
from utils.adb_input import tap
from utils.adb_screenshot import take_screenshot

# Load config and check debug mode
config = Config.load()
DEBUG_MODE = Config.get("debug_mode", False)
RETRY_RACE = Config.get("retry_race", True)

def needs_infirmary(screenshot):
    # Use match_template to get full bounding box for brightness check
    infirmary_matches = match_template(screenshot, INFIRMARY_BUTTON_TEMPLATE, confidence=0.9)

    if infirmary_matches:
        debuffed_box = infirmary_matches[0]  # Get first match (x, y, w, h)

        # Check if the button is actually active (bright) or just disabled (dark)
        if _is_infirmary_active(screenshot, debuffed_box):
            print("[INFO] Character has debuff, go to infirmary instead.")
            return True
        else:
            debug_print("[DEBUG] Infirmary button found but is disabled (dark)")
    else:
            debug_print("[DEBUG] No infirmary button detected")
    
    return False

def do_infirmary(screenshot):
    # Use match_template to get full bounding box for brightness check
    infirmary_matches = match_template(screenshot, INFIRMARY_BUTTON_TEMPLATE, confidence=0.9)

    x, y, w, h = infirmary_matches[0]
    center_x, center_y = x + w//2, y + h//2
    tap(center_x, center_y)

def _is_infirmary_active(screenshot, button_location):
    """
    Check if the infirmary button is active (bright) or disabled (dark).
    Args:
        button_location: tuple (x, y, w, h) of the button location
    Returns:
        bool: True if button is active (bright), False if disabled (dark)
    """
    try:
        x, y, w, h = button_location
        
        # Take screenshot and crop the button region
        button_region = screenshot.crop((x, y, x + w, y + h))
        
        # Convert to grayscale and calculate average brightness
        grayscale = button_region.convert("L")
        stat = ImageStat.Stat(grayscale)
        avg_brightness = stat.mean[0]
        
        # Threshold for active button (same as PC version)
        is_active = avg_brightness > 150
        debug_print(f"[DEBUG] Infirmary brightness: {avg_brightness:.1f} ({'active' if is_active else 'disabled'})")
        
        return is_active
    except Exception as e:
        print(f"[ERROR] Failed to check infirmary button brightness: {e}")
        return False

def do_rest(main_screenshot):
    screenshot = take_screenshot()

    """Perform rest action"""
    debug_print("[DEBUG] Performing rest action...")
    print("[INFO] Performing rest action...")
    
    # Rest button is in the lobby, not on training screen
    # If we're on training screen, go back to lobby first
    back_btn = locate_on_screen(screenshot, BACK_BUTTON_TEMPLATE, confidence=0.8)
    if back_btn:
        debug_print("[DEBUG] Going back to lobby to find rest button...")
        print("[INFO] Going back to lobby to find rest button...")
        from utils.adb_input import tap
        tap(back_btn[0], back_btn[1])
        
    time.sleep(1.0)  # Wait for lobby to load
    screenshot = take_screenshot()
    
    # Now look for rest buttons in the lobby
    rest_btn = locate_on_screen(screenshot, REST_BUTTON_TEMPLATE, confidence=0.5)
    rest_summer_btn = locate_on_screen(screenshot, REST_SUMMER_BUTTON_TEMPLATE, confidence=0.5)
    
    debug_print(f"[DEBUG] Rest button found: {rest_btn}")
    debug_print(f"[DEBUG] Summer rest button found: {rest_summer_btn}")
    
    if rest_btn:
        debug_print(f"[DEBUG] Clicking rest button at {rest_btn}")
        print(f"[INFO] Clicking rest button at {rest_btn}")
        from utils.adb_input import tap
        tap(rest_btn[0], rest_btn[1])
        debug_print("[DEBUG] Clicked rest button")
        print("[INFO] Rest button clicked")
    elif rest_summer_btn:
        debug_print(f"[DEBUG] Clicking summer rest button at {rest_summer_btn}")
        print(f"[INFO] Clicking summer rest button at {rest_summer_btn}")
        from utils.adb_input import tap
        tap(rest_summer_btn[0], rest_summer_btn[1])
        debug_print("[DEBUG] Clicked summer rest button")
        print("[INFO] Summer rest button clicked")
    else:
        debug_print("[DEBUG] No rest button found in lobby")
        print("[WARNING] No rest button found in lobby")

def do_recreation(screenshot):
    """Perform recreation action"""
    debug_print("[DEBUG] Performing recreation action...")
    recreation_btn = locate_on_screen(screenshot, RECREATION_BUTTON_TEMPLATE, confidence=0.8)
    recreation_summer_btn = locate_on_screen(screenshot, REST_SUMMER_BUTTON_TEMPLATE, confidence=0.8)
    
    if recreation_btn:
        debug_print(f"[DEBUG] Found recreation button at {recreation_btn}")
        tap(recreation_btn[0], recreation_btn[1])
        debug_print("[DEBUG] Clicked recreation button")
    elif recreation_summer_btn:
        debug_print(f"[DEBUG] Found summer recreation button at {recreation_summer_btn}")
        tap(recreation_summer_btn[0], recreation_summer_btn[1])
        debug_print("[DEBUG] Clicked summer recreation button")
    else:
        debug_print("[DEBUG] No recreation button found")