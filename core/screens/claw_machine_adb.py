import time
import random

from core.templates_adb import CLAW_BUTTON_TEMPLATE
from utils.adb_recognizer import locate_on_screen, match_template
from utils.adb_input import long_press

def do_claw_machine(screenshot):
    """Handle claw machine interaction"""
    print("[INFO] Claw machine detected, starting interaction...")
    
    # Wait 2 seconds before interacting
    time.sleep(2)
    
    # Find the claw button location
    claw_location = locate_on_screen(screenshot, CLAW_BUTTON_TEMPLATE, confidence=0.8)
    if not claw_location:
        print("[WARNING] Claw button not found for interaction")
        return False
    
    # Get center coordinates (locate_on_screen returns center coordinates)
    center_x, center_y = claw_location
    
    # Generate random hold duration between 3-4 seconds (in milliseconds)
    hold_duration = random.randint(1000, 3000)
    print(f"[INFO] Holding claw button for {hold_duration}ms...")
    
    # Use ADB long press to hold the claw button
    long_press(center_x, center_y, hold_duration)
    
    print("[INFO] Claw machine interaction completed")
    return True
