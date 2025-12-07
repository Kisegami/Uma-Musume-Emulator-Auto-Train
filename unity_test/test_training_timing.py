"""
Test for training checking workflow with detailed timing measurements.
Uses utils modules for connection, screenshots, and input operations.
"""

import time
import json
import os
import sys
import cv2
import numpy as np
from PIL import Image
from typing import Dict, Tuple, Optional, List
from collections import defaultdict

# Add parent directory to path to import utils
# This allows the script to be run from any directory
_script_dir = os.path.dirname(os.path.abspath(__file__))
_parent_dir = os.path.dirname(_script_dir)
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)

# Import utils for connection, screenshots, and input
from utils.screenshot import take_screenshot
from utils.input import tap, tap_on_image
from utils.device import run_adb
from utils.recognizer import locate_on_screen, match_template, locate_all_on_screen
from utils.template_matching import deduplicated_matches
from utils.constants_unity import (
    SUPPORT_CARD_ICON_REGION,
    FAILURE_REGION_SPD,
    FAILURE_REGION_STA,
    FAILURE_REGION_PWR,
    FAILURE_REGION_GUTS,
    FAILURE_REGION_WIT,
)

# Custom swipe function without input delay for faster hover operations
def swipe_no_delay(start_x: int, start_y: int, end_x: int, end_y: int, duration_ms: int = 50):
    """Swipe without input delay for faster operations"""
    return run_adb(['shell', 'input', 'swipe', str(start_x), str(start_y), str(end_x), str(end_y), str(duration_ms)], add_input_delay=False)



# ============================================================================
# Configuration and Constants
# ============================================================================

# Training coordinates (fixed positions)
TRAINING_COORDS = {
    "spd": (165, 1557),
    "sta": (357, 1563),
    "pwr": (546, 1557),
    "guts": (735, 1566),
    "wit": (936, 1572)
}

# Bond sample offset from support icon center
BOND_SAMPLE_OFFSET = (-2, 116)

# Bond level colors (RGB)
BOND_LEVEL_COLORS = {
    5: (255, 235, 120),
    4: (255, 173, 30),
    3: (162, 230, 30),
    2: (42, 192, 255),
    1: (109, 108, 117),
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

# Failure regions per training type (from constants_unity)
FAILURE_REGIONS = {
    "spd": FAILURE_REGION_SPD,
    "sta": FAILURE_REGION_STA,
    "pwr": FAILURE_REGION_PWR,
    "guts": FAILURE_REGION_GUTS,
    "wit": FAILURE_REGION_WIT,
}


# ============================================================================
# Timing Decorator
# ============================================================================

class TimingContext:
    """Context manager for timing operations"""
    def __init__(self, name: str, timings: Dict):
        self.name = name
        self.timings = timings
        self.start_time = None
        
    def __enter__(self):
        self.start_time = time.time()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        elapsed = time.time() - self.start_time
        if self.name not in self.timings:
            self.timings[self.name] = []
        self.timings[self.name].append(elapsed)
        return False


# ============================================================================
# Training Check Functions
# ============================================================================









# ============================================================================
# Training Check Functions
# ============================================================================



def check_support_cards(screenshot: Image.Image, timings: Dict) -> Dict[str, int]:
    """Check support card counts - optimized implementation"""
    with TimingContext("check_support_cards", timings):
        count_result = {}
        left, top, right, bottom = SUPPORT_CARD_ICON_REGION
        region_cv = (left, top, right - left, bottom - top)
        
        for key, icon_path in SUPPORT_ICON_PATHS.items():
            with TimingContext(f"check_support_{key}", timings):
                matches = match_template(screenshot, icon_path, 0.8, region_cv)
                filtered = deduplicated_matches(matches, threshold=30) if matches else []
                count_result[key] = len(filtered) if filtered else 0
        
        return count_result


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


def _filtered_template_matches(screenshot: Image.Image, template_path: str, region_cv: Tuple, confidence: float = 0.8) -> List[Tuple]:
    """Get filtered template matches with deduplication"""
    raw = match_template(screenshot, template_path, confidence, region_cv)
    if not raw:
        return []
    return deduplicated_matches(raw, threshold=30)


def check_bond_levels(screenshot: Image.Image, timings: Dict) -> Dict[str, List[Dict]]:
    """Check bond levels for each support card - optimized implementation"""
    with TimingContext("check_bond_levels", timings):
        detailed_support = {}
        rgb_img = screenshot.convert("RGB")
        width, height = rgb_img.size
        dx, dy = BOND_SAMPLE_OFFSET
        left, top, right, bottom = SUPPORT_CARD_ICON_REGION
        region_cv = (left, top, right - left, bottom - top)
        
        for t_key, template_path in SUPPORT_ICON_PATHS.items():
            with TimingContext(f"check_bond_{t_key}", timings):
                matches = _filtered_template_matches(screenshot, template_path, region_cv, confidence=0.8)
                if not matches:
                    continue
                
                entries = []
                for (x, y, w, h) in matches:
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


def check_hint_wrapper(screenshot: Image.Image, timings: Dict) -> bool:
    """Check for hint icon - optimized implementation"""
    with TimingContext("check_hint", timings):
        left, top, right, bottom = SUPPORT_CARD_ICON_REGION
        region_cv = (left, top, right - left, bottom - top)
        matches = match_template(screenshot, "assets/icons/hint.png", 0.8, region_cv)
        return bool(matches and len(matches) > 0)


def check_spirit_training(screenshot: Image.Image, train_type: str, timings: Dict) -> int:
    """Check spirit training count - optimized implementation"""
    with TimingContext(f"check_spirit_{train_type}", timings):
        left, top, right, bottom = SUPPORT_CARD_ICON_REGION
        region_cv = (left, top, right - left, bottom - top)
        matches = match_template(screenshot, "assets/unity/spirit_training.png", 0.8, region_cv)
        filtered = deduplicated_matches(matches, threshold=30) if matches else []
        return len(filtered)


def check_failure_rate(screenshot: Image.Image, train_type: str, timings: Dict) -> Tuple[float, float]:
    """Check failure rate using OCR - direct OCR without preprocessing"""
    import pytesseract
    import re
    from datetime import datetime
    
    region = FAILURE_REGIONS.get(train_type)
    if not region:
        return (0.0, 0.0)
    
    percentage_patterns = [
        r"(\d{1,3})\s*%",  # "29%", "29 %" - most reliable
        r"%\s*(\d{1,3})",  # "% 29" - reversed format
        r"(\d{1,3})",      # Just the number - fallback
    ]
    
    # Direct OCR on cropped region - no preprocessing
    # Crop region
    with TimingContext(f"failure_crop_{train_type}", timings):
        img = screenshot.crop(region)
        
        # Save cropped region to debug folder
        debug_dir = os.path.join("unity_test", "debug_failure_regions")
        os.makedirs(debug_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]  # milliseconds
        debug_path = os.path.join(debug_dir, f"failure_{train_type}_{timestamp}.png")
        img.save(debug_path)
        print(f"  [DEBUG] Saved failure region to: {debug_path}")
    
    # Direct OCR execution (no preprocessing)
    with TimingContext(f"failure_ocr_{train_type}", timings):
        ocr_data = pytesseract.image_to_data(np.array(img), config='--oem 3 --psm 6', output_type=pytesseract.Output.DICT)
        text = pytesseract.image_to_string(np.array(img), config='--oem 3 --psm 6').strip()
        print(f"  [DEBUG] OCR text: '{text}'")
    
    # Calculate confidence
    with TimingContext(f"failure_confidence_{train_type}", timings):
        confidences = [conf for conf in ocr_data['conf'] if conf != -1]
        avg_confidence = (sum(confidences) / len(confidences) / 100.0) if confidences else 0.0
    
    # Pattern matching
    with TimingContext(f"failure_pattern_{train_type}", timings):
        for pattern in percentage_patterns:
            match = re.search(pattern, text)
            if match:
                rate = int(match.group(1))
                if 0 <= rate <= 100:
                    return (rate, avg_confidence)
    
    # If OCR failed, return safe fallback
    return (100, 0.0)


# ============================================================================
# Main Test Function
# ============================================================================

def go_to_training(timings: Dict) -> bool:
    """Navigate to training screen"""
    with TimingContext("go_to_training", timings):
        print("[STEP] Going to training screen...")
        success = tap_on_image("assets/buttons/training_btn.png", min_search=10)
        if success:
            time.sleep(0.5)  # Wait for screen to stabilize
        return success


def check_single_training(train_type: str, coords: Tuple[int, int], timings: Dict) -> Dict:
    """Check a single training type"""
    print(f"\n[CHECK] Checking {train_type.upper()} training at {coords}...")
    
    # Step 1: Hover simulation with detailed timing
    print(f"  [SUB] Hovering over {train_type.upper()} training...")
    with TimingContext(f"hover_{train_type}", timings):
        start_x, start_y = coords
        end_x, end_y = start_x, start_y - 200
        
        # Time the swipe operation (reduced to 50ms, no input delay)
        with TimingContext(f"hover_swipe_{train_type}", timings):
            swipe_no_delay(start_x, start_y, end_x, end_y, duration_ms=50)
        
        # Wait 100ms after swipe for UI to stabilize
        with TimingContext(f"hover_wait_{train_type}", timings):
            time.sleep(0.5)
    
    # Step 2: Take screenshot
    with TimingContext(f"screenshot_{train_type}", timings):
        print(f"  [SUB] Taking screenshot...")
        screenshot = take_screenshot()
        if not screenshot:
            print(f"  [ERROR] Failed to take screenshot for {train_type}")
            return {}
    
    # Step 3: Check support cards
    with TimingContext(f"support_check_{train_type}", timings):
        print(f"  [SUB] Checking support cards...")
        support_counts = check_support_cards(screenshot, timings)
        total_support = sum(support_counts.values())
        print(f"  [RESULT] Support cards: {support_counts} (total: {total_support})")
    
    # Step 4: Check bond levels
    with TimingContext(f"bond_check_{train_type}", timings):
        print(f"  [SUB] Checking bond levels...")
        detailed_support = check_bond_levels(screenshot, timings)
        print(f"  [RESULT] Bond levels: {len(detailed_support)} types found")
    
    # Step 5: Check hint
    with TimingContext(f"hint_check_{train_type}", timings):
        print(f"  [SUB] Checking for hint...")
        hint_found = check_hint_wrapper(screenshot, timings)
        print(f"  [RESULT] Hint found: {hint_found}")
    
    # Step 6: Check spirit training
    with TimingContext(f"spirit_check_{train_type}", timings):
        print(f"  [SUB] Checking spirit training...")
        spirit_count = check_spirit_training(screenshot, train_type, timings)
        print(f"  [RESULT] Spirit training count: {spirit_count}")
    
    # Step 7: Check failure rate
    print(f"  [SUB] Checking failure rate...")
    failure_chance, confidence = check_failure_rate(screenshot, train_type, timings)
    print(f"  [RESULT] Failure: {failure_chance}% (confidence: {confidence:.2f})")
    
    return {
        "support": support_counts,
        "support_detail": detailed_support,
        "hint": hint_found,
        "spirit_count": spirit_count,
        "failure": failure_chance,
        "confidence": confidence,
    }


def print_timing_summary(timings: Dict):
    """Print detailed timing summary"""
    print("\n" + "="*80)
    print("TIMING SUMMARY")
    print("="*80)
    
    # Calculate totals
    total_times = {}
    for key, times in timings.items():
        total_times[key] = sum(times)
    
    # Sort by total time
    sorted_times = sorted(total_times.items(), key=lambda x: x[1], reverse=True)
    
    print("\nTotal Time by Operation:")
    print("-" * 80)
    for key, total_time in sorted_times:
        count = len(timings[key])
        avg_time = total_time / count if count > 0 else 0
        print(f"  {key:40s} | Total: {total_time:8.3f}s | Count: {count:3d} | Avg: {avg_time:6.3f}s")
    
    # Hover timing breakdown
    print("\nHover Operation Breakdown:")
    print("-" * 80)
    hover_total = sum(timings.get("hover_spd", []) + timings.get("hover_sta", []) + 
                      timings.get("hover_pwr", []) + timings.get("hover_guts", []) + 
                      timings.get("hover_wit", []))
    hover_swipe_total = sum(timings.get("hover_swipe_spd", []) + timings.get("hover_swipe_sta", []) + 
                            timings.get("hover_swipe_pwr", []) + timings.get("hover_swipe_guts", []) + 
                            timings.get("hover_swipe_wit", []))
    hover_wait_total = sum(timings.get("hover_wait_spd", []) + timings.get("hover_wait_sta", []) + 
                           timings.get("hover_wait_pwr", []) + timings.get("hover_wait_guts", []) + 
                           timings.get("hover_wait_wit", []))
    
    if hover_total > 0:
        print(f"  Total hover time: {hover_total:.3f}s")
        print(f"    - Swipe operations: {hover_swipe_total:.3f}s ({hover_swipe_total/hover_total*100:.1f}%)")
        print(f"    - Wait time: {hover_wait_total:.3f}s ({hover_wait_total/hover_total*100:.1f}%)")
        print(f"    - Average per training: {hover_total/5:.3f}s")
    
    # Failure check timing breakdown
    print("\nFailure Check Operation Breakdown:")
    print("-" * 80)
    failure_keys = [k for k in timings.keys() if k.startswith("failure_")]
    if failure_keys:
        # Group by operation type
        failure_ops = {}
        for key in failure_keys:
            # Extract operation type (e.g., "ocr_white_1", "mask_yellow_2", etc.)
            parts = key.split("_")
            if len(parts) >= 3:
                op_type = "_".join(parts[1:-1])  # Everything between "failure" and train_type
                if op_type not in failure_ops:
                    failure_ops[op_type] = []
                failure_ops[op_type].extend(timings[key])
        
        # Calculate totals
        failure_total = sum(sum(timings[k]) for k in failure_keys)
        white_total = sum(sum(timings[k]) for k in failure_keys if "white" in k)
        yellow_total = sum(sum(timings[k]) for k in failure_keys if "yellow" in k)
        screenshot_total = sum(sum(timings[k]) for k in failure_keys if "screenshot" in k)
        ocr_total = sum(sum(timings[k]) for k in failure_keys if "ocr" in k)
        mask_total = sum(sum(timings[k]) for k in failure_keys if "mask" in k)
        enhance_total = sum(sum(timings[k]) for k in failure_keys if "enhance" in k)
        pattern_total = sum(sum(timings[k]) for k in failure_keys if "pattern" in k)
        
        print(f"  Total failure check time: {failure_total:.3f}s")
        print(f"    - White OCR attempts: {white_total:.3f}s ({white_total/failure_total*100:.1f}%)")
        print(f"    - Yellow OCR attempts: {yellow_total:.3f}s ({yellow_total/failure_total*100:.1f}%)")
        print(f"    - Screenshot operations: {screenshot_total:.3f}s ({screenshot_total/failure_total*100:.1f}%)")
        print(f"    - OCR execution: {ocr_total:.3f}s ({ocr_total/failure_total*100:.1f}%)")
        print(f"    - Image processing (mask/enhance): {mask_total + enhance_total:.3f}s ({(mask_total + enhance_total)/failure_total*100:.1f}%)")
        print(f"    - Pattern matching: {pattern_total:.3f}s ({pattern_total/failure_total*100:.1f}%)")
        print(f"    - Average per training: {failure_total/5:.3f}s")
        
        # Detailed breakdown by operation type
        print("\n  Detailed Step Breakdown:")
        for op_type in sorted(failure_ops.keys()):
            total_op_time = sum(failure_ops[op_type])
            count = len(failure_ops[op_type])
            avg_time = total_op_time / count if count > 0 else 0
            print(f"    - {op_type:35s}: {total_op_time:8.3f}s total | {count:2d} ops | {avg_time:6.3f}s avg")
    
    # Group by training type
    print("\nTime by Training Type:")
    print("-" * 80)
    for train_type in ["spd", "sta", "pwr", "guts", "wit"]:
        train_times = {}
        nested_keys = set()  # Track nested timings to exclude from total
        
        for key, times in timings.items():
            if key.startswith(train_type + "_") or (train_type in key and f"_{train_type}" in key):
                train_times[key] = sum(times)
                # Mark nested timings (children of parent timings)
                if f"hover_swipe_{train_type}" in key or f"hover_wait_{train_type}" in key:
                    nested_keys.add(key)
                elif key.startswith(f"check_") and train_type in key:
                    # check_support_spd, check_bond_spd, check_spirit_spd are nested
                    nested_keys.add(key)
        
        if train_times:
            # Calculate total excluding nested timings (they're already included in parents)
            top_level_times = {k: v for k, v in train_times.items() if k not in nested_keys}
            total_train_time = sum(top_level_times.values())
            print(f"\n  {train_type.upper()}: {total_train_time:.3f}s total")
            # Show hover breakdown first if available
            if f"hover_{train_type}" in train_times:
                hover_time = train_times[f"hover_{train_type}"]
                swipe_time = train_times.get(f"hover_swipe_{train_type}", 0)
                wait_time = train_times.get(f"hover_wait_{train_type}", 0)
                print(f"    - hover_{train_type:25s}: {hover_time:8.3f}s (swipe: {swipe_time:.3f}s, wait: {wait_time:.3f}s)")
            for key, time_val in sorted(top_level_times.items(), key=lambda x: x[1], reverse=True):
                if not key.startswith("hover_"):  # Skip hover keys, already shown
                    print(f"    - {key:35s}: {time_val:8.3f}s")
    
    # Overall statistics
    all_times = [t for times in timings.values() for t in times]
    if all_times:
        print("\nOverall Statistics:")
        print("-" * 80)
        print(f"  Total operations: {len(all_times)}")
        print(f"  Total time: {sum(all_times):.3f}s")
        print(f"  Average operation time: {sum(all_times)/len(all_times):.3f}s")
        print(f"  Min operation time: {min(all_times):.3f}s")
        print(f"  Max operation time: {max(all_times):.3f}s")


def main():
    """Main test function"""
    print("="*80)
    print("TRAINING CHECK TIMING TEST")
    print("="*80)
    print("\nThis test will:")
    print("  1. Connect to emulator")
    print("  2. Navigate to training screen")
    print("  3. Check each training type (SPD, STA, PWR, GUTS, WIT)")
    print("  4. Output detailed timing for each step")
    print("\n" + "="*80 + "\n")
    
    timings = defaultdict(list)
    
    # Step 1: Connect to emulator (test screenshot)
    print("[STEP] Testing emulator connection...")
    with TimingContext("emulator_connection", timings):
        test_screenshot = take_screenshot()
        if not test_screenshot:
            print("[ERROR] Failed to connect to emulator. Please check:")
            print("  - ADB is installed and in PATH")
            print("  - Emulator is running")
            print("  - config.json has correct adb_config settings")
            return
        print(f"[SUCCESS] Emulator connected. Screenshot size: {test_screenshot.size}")
    
    # Step 2: Go to training screen
    if not go_to_training(timings):
        print("[ERROR] Failed to navigate to training screen")
        return
    
    # Step 3: Check each training type
    results = {}
    for train_type, coords in TRAINING_COORDS.items():
        result = check_single_training(train_type, coords, timings)
        results[train_type] = result
    
    # Step 4: Go back (optional)
    print("\n[STEP] Going back to lobby...")
    with TimingContext("go_back", timings):
        tap_on_image("assets/buttons/back_btn.png", min_search=3)
    
    # Step 5: Print timing summary
    print_timing_summary(timings)
    
    # Step 6: Print results summary
    print("\n" + "="*80)
    print("RESULTS SUMMARY")
    print("="*80)
    for train_type, result in results.items():
        if result:
            print(f"\n{train_type.upper()}:")
            print(f"  Support cards: {result.get('support', {})}")
            print(f"  Hint: {result.get('hint', False)}")
            print(f"  Spirit training: {result.get('spirit_count', 0)}")
            print(f"  Failure rate: {result.get('failure', 0)}%")
    
    print("\n" + "="*80)
    print("TEST COMPLETED")
    print("="*80)


if __name__ == "__main__":
    main()

