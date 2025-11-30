#!/usr/bin/env python3
import os
import sys
import time

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from utils.screenshot import take_screenshot
from core.state import check_energy_bar

if __name__ == "__main__":
    # One-shot capture and energy read; always save debug images into Energy test/
    shot = take_screenshot()
    value = check_energy_bar(shot, debug_visualization=True)
    print(f"Energy read: {value:.1f}%")
    print("Saved debug images to 'Energy test' folder (with timestamp).")


