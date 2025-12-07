"""
Simplified test for training checking - minimal overhead, just measure total time per check.
"""

import time
import os
import sys
import numpy as np
from PIL import Image
from typing import Tuple

# Add parent directory to path to import utils
_script_dir = os.path.dirname(os.path.abspath(__file__))
_parent_dir = os.path.dirname(_script_dir)
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)

# Import utils
from utils.screenshot import take_screenshot
from utils.input import tap_on_image
from utils.device import run_adb
from utils.recognizer import match_template
from utils.template_matching import deduplicated_matches
from utils.constants_unity import (
    SUPPORT_CARD_ICON_REGION,
    FAILURE_REGION_SPD,
    FAILURE_REGION_STA,
    FAILURE_REGION_PWR,
    FAILURE_REGION_GUTS,
    FAILURE_REGION_WIT,
)

# Training coordinates
TRAINING_COORDS = {
    "spd": (165, 1557),
    "sta": (357, 1563),
    "pwr": (546, 1557),
    "guts": (735, 1566),
    "wit": (936, 1572)
}

# Failure regions
FAILURE_REGIONS = {
    "spd": FAILURE_REGION_SPD,
    "sta": FAILURE_REGION_STA,
    "pwr": FAILURE_REGION_PWR,
    "guts": FAILURE_REGION_GUTS,
    "wit": FAILURE_REGION_WIT,
}

# Support icon templates
SUPPORT_ICON_PATHS = {
    "spd": "assets/icons/support_card_type_spd.png",
    "sta": "assets/icons/support_card_type_sta.png",
    "pwr": "assets/icons/support_card_type_pwr.png",
    "guts": "assets/icons/support_card_type_guts.png",
    "wit": "assets/icons/support_card_type_wit.png",
    "friend": "assets/icons/support_card_type_friend.png",
}

# Bond level colors (RGB)
BOND_LEVEL_COLORS = {
    5: (255, 235, 120),
    4: (255, 173, 30),
    3: (162, 230, 30),
    2: (42, 192, 255),
    1: (109, 108, 117),
}

# Bond sample offset from support icon center
BOND_SAMPLE_OFFSET = (-2, 116)

def swipe_no_delay(start_x: int, start_y: int, end_x: int, end_y: int, duration_ms: int = 50):
    """Swipe without input delay"""
    return run_adb(['shell', 'input', 'swipe', str(start_x), str(start_y), str(end_x), str(end_y), str(duration_ms)], add_input_delay=False)

def _classify_bond_level(rgb_tuple: Tuple[int, int, int]) -> int:
    """Classify bond level based on RGB color values"""
    r, g, b = rgb_tuple
    best_level, best_dist = 1, float('inf')
    for level, (cr, cg, cb) in BOND_LEVEL_COLORS.items():
        dr, dg, db = r - cr, g - cg, b - cb
        dist = dr*dr + dg*dg + db*db
        if dist < best_dist:
            best_dist, best_level = dist, level
    return best_level

def check_support_cards(screenshot: Image.Image) -> dict:
    """Check support card counts"""
    count_result = {}
    left, top, right, bottom = SUPPORT_CARD_ICON_REGION
    region_cv = (left, top, right - left, bottom - top)
    
    for key, icon_path in SUPPORT_ICON_PATHS.items():
        matches = match_template(screenshot, icon_path, 0.8, region_cv)
        filtered = deduplicated_matches(matches, threshold=30) if matches else []
        count_result[key] = len(filtered) if filtered else 0
    
    return count_result

def check_bond_levels(screenshot: Image.Image) -> dict:
    """Check bond levels for each support card"""
    detailed_support = {}
    rgb_img = screenshot.convert("RGB")
    width, height = rgb_img.size
    dx, dy = BOND_SAMPLE_OFFSET
    left, top, right, bottom = SUPPORT_CARD_ICON_REGION
    region_cv = (left, top, right - left, bottom - top)
    
    for t_key, template_path in SUPPORT_ICON_PATHS.items():
        matches = match_template(screenshot, template_path, 0.8, region_cv)
        if not matches:
            continue
        filtered = deduplicated_matches(matches, threshold=30) if matches else []
        
        entries = []
        for (x, y, w, h) in filtered:
            cx, cy = int(x + w // 2), int(y + h // 2)
            sx, sy = cx + dx, cy + dy
            sx = max(0, min(width - 1, sx))
            sy = max(0, min(height - 1, sy))
            r, g, b = rgb_img.getpixel((sx, sy))
            level = _classify_bond_level((r, g, b))
            entries.append({
                "center": [cx, cy],
                "bond_level": int(level),
                "bond_color": [int(r), int(g), int(b)],
            })
        if entries:
            detailed_support[t_key] = entries
    
    return detailed_support

def check_hint(screenshot: Image.Image) -> bool:
    """Check for hint icon"""
    left, top, right, bottom = SUPPORT_CARD_ICON_REGION
    region_cv = (left, top, right - left, bottom - top)
    matches = match_template(screenshot, "assets/icons/hint.png", 0.8, region_cv)
    return bool(matches and len(matches) > 0)

def check_spirit_training(screenshot: Image.Image, train_type: str) -> int:
    """Check spirit training count"""
    left, top, right, bottom = SUPPORT_CARD_ICON_REGION
    region_cv = (left, top, right - left, bottom - top)
    matches = match_template(screenshot, "assets/unity/spirit_training.png", 0.8, region_cv)
    filtered = deduplicated_matches(matches, threshold=30) if matches else []
    return len(filtered)

def check_failure_rate(screenshot: Image.Image, train_type: str) -> float:
    """Minimal failure rate check - just OCR"""
    import pytesseract
    import re
    
    region = FAILURE_REGIONS.get(train_type)
    if not region:
        return 0.0
    
    img = screenshot.crop(region)
    text = pytesseract.image_to_string(np.array(img), config='--oem 3 --psm 6').strip()
    
    # Simple pattern matching
    match = re.search(r"(\d{1,3})\s*%", text)
    if match:
        rate = int(match.group(1))
        if 0 <= rate <= 100:
            return rate
    return 100.0

def go_to_training() -> bool:
    """Navigate to training screen"""
    return tap_on_image("assets/buttons/training_btn.png", min_search=10)

def check_single_training(train_type: str, coords: Tuple[int, int]) -> dict:
    """Check a single training - all checks"""
    # Hover
    start_x, start_y = coords
    end_x, end_y = start_x, start_y - 200
    swipe_no_delay(start_x, start_y, end_x, end_y, duration_ms=20)
    time.sleep(0.4)  # Wait for UI
    
    # Screenshot
    screenshot = take_screenshot()
    if not screenshot:
        return {}
    
    # All checks
    support_counts = check_support_cards(screenshot)
    bond_levels = check_bond_levels(screenshot)
    hint_found = check_hint(screenshot)
    spirit_count = check_spirit_training(screenshot, train_type)
    failure_rate = check_failure_rate(screenshot, train_type)
    
    return {
        "support": support_counts,
        "bond_levels": bond_levels,
        "hint": hint_found,
        "spirit": spirit_count,
        "failure": failure_rate
    }

def main():
    """Simplified test - measure total time per check"""
    print("="*80)
    print("SIMPLIFIED TRAINING CHECK TEST")
    print("="*80)
    
    # Connect
    print("\n[STEP] Connecting to emulator...")
    test_screenshot = take_screenshot()
    if not test_screenshot:
        print("[ERROR] Failed to connect")
        return
    print(f"[SUCCESS] Connected. Size: {test_screenshot.size}")
    
    # Start timer after connection
    start_time = time.time()
    
    # Go to training
    print("\n[STEP] Going to training screen...")
    if not go_to_training():
        print("[ERROR] Failed to go to training")
        return
    time.sleep(0.5)
    
    # Check each training type
    print("\n[STEP] Checking each training type...")
    results = {}
    for train_type, coords in TRAINING_COORDS.items():
        check_start = time.time()
        result = check_single_training(train_type, coords)
        check_time = time.time() - check_start
        
        results[train_type] = result
        
        # Output results
        print(f"\n  {train_type.upper()}: {check_time:.3f}s")
        if result:
            support_total = sum(result.get("support", {}).values())
            print(f"    Support cards: {result.get('support', {})} (total: {support_total})")
            print(f"    Bond levels: {len(result.get('bond_levels', {}))} types")
            print(f"    Hint: {result.get('hint', False)}")
            print(f"    Spirit training: {result.get('spirit', 0)}")
            print(f"    Failure rate: {result.get('failure', 0)}%")
    
    total_time = time.time() - start_time
    
    # Summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    print(f"Total time: {total_time:.3f}s")
    print(f"Average per check: {total_time / len(TRAINING_COORDS):.3f}s")

if __name__ == "__main__":
    main()

