import time
from core.templates_adb import TRAINING_BUTTON_TEMPLATE
import cv2

from core.config import Config
from core.event_handling import click, debug_print
from core.state_adb import check_failure, check_hint, check_support_card
from utils.adb_recognizer import match_template
from utils.adb_input import triple_click
from utils.adb_screenshot import take_screenshot
from utils.constants_phone import SUPPORT_CARD_ICON_REGION

# Load config and check debug mode
config = Config.load()
DEBUG_MODE = Config.get("debug_mode", False)
RETRY_RACE = Config.get("retry_race", True)

BOND_LEVEL_COLORS = {
    5: (255, 235, 120),
    4: (255, 173, 30),
    3: (162, 230, 30),
    2: (42, 192, 255),
    1: (109, 108, 117),
}

# Bond color classification helpers
BOND_SAMPLE_OFFSET = (-2, 116)
BOND_LEVEL_COLORS = {
    5: (255, 235, 120),
    4: (255, 173, 30),
    3: (162, 230, 30),
    2: (42, 192, 255),
    1: (109, 108, 117),
}

# Support icon templates for detailed detection
SUPPORT_ICON_PATHS = {
    "spd": "assets/icons/support_card_type_spd.png",
    "sta": "assets/icons/support_card_type_sta.png",
    "pwr": "assets/icons/support_card_type_pwr.png",
    "guts": "assets/icons/support_card_type_guts.png",
    "wit": "assets/icons/support_card_type_wit.png",
    "friend": "assets/icons/support_card_type_friend.png",
}

SUPPORT_ICON_TMPLS = {
    key: cv2.imread(path, cv2.IMREAD_COLOR)
    for key, path in SUPPORT_ICON_PATHS.items()
}

def _classify_bond_level(rgb_tuple):
    r, g, b = rgb_tuple
    best_level, best_dist = 1, float('inf')
    for level, (cr, cg, cb) in BOND_LEVEL_COLORS.items():
        dr, dg, db = r - cr, g - cg, b - cb
        dist = dr*dr + dg*dg + db*db
        if dist < best_dist:
            best_dist, best_level = dist, level
    return best_level

def _filtered_template_matches(screenshot, template_path, region_cv, confidence=0.8):
    raw = match_template(screenshot, template_path, confidence, region_cv)
    if not raw:
        return []
    filtered = []
    for (x, y, w, h) in raw:
        cx, cy = x + w // 2, y + h // 2
        duplicate = False
        for (ex, ey, ew, eh) in filtered:
            ecx, ecy = ex + ew // 2, ey + eh // 2
            if abs(cx - ecx) < 30 and abs(cy - ecy) < 30:
                duplicate = True
                break
        if not duplicate:
            filtered.append((x, y, w, h))
    return filtered

def go_to_training():
    """Go to training screen"""
    debug_print("[DEBUG] Going to training screen...")
    time.sleep(1)
    return click(TRAINING_BUTTON_TEMPLATE, minSearch=10)

def check_training():
    """Check training results using fixed coordinates, collecting support counts,
    bond levels and hint presence in one hover pass before computing failure rates."""
    debug_print("[DEBUG] Checking training options...")

    # Check skill points cap before race day (if enabled)
    # Fixed coordinates for each training type
    training_coords_base = {
        "spd": (165, 1557),
        "sta": (357, 1563),
        "pwr": (546, 1557),
        "guts": (735, 1566),
        "wit": (936, 1572)
    }

    training_coords = {}
    for training in config.get('priority_stat'):
        training_coords[training] = training_coords_base[training]

    results = {}
    high_score_found = False

    for key, coords in training_coords.items():
        if high_score_found:
            results[key] = {
                "support": 0,
                "support_detail": {},
                "hint": False,
                "total_support": 0,
                "failure": 100,
                "confidence": 0.0,
                "score": 0
            }
            print(f"[INFO] Skipping {key.upper()} because high training score found")
            continue
            
        debug_print(f"[DEBUG] Checking {key.upper()} training at coordinates {coords}...")
        
        # Proper hover simulation: move to position, hold, check, move away, release
        debug_print(f"[DEBUG] Hovering over {key.upper()} training to check support cards...")
        
        # Step 1: Hold at button position and move mouse up 300 pixels to simulate hover
        debug_print(f"[DEBUG] Holding at {key.upper()} training button and moving mouse up...")
        from utils.adb_input import swipe
        # Swipe from button position up 300 pixels with longer duration to simulate holding and moving
        start_x, start_y = coords
        end_x, end_y = start_x, start_y - 300  # Move up 300 pixels
        swipe(start_x, start_y, end_x, end_y, duration_ms=200)  # Longer duration for hover effect
        time.sleep(0.3)  # Wait for hover effect to register
        
        # Step 2: One pass: capture screenshot, evaluate support counts, bond levels, and hint
        screenshot = take_screenshot()
        left, top, right, bottom = SUPPORT_CARD_ICON_REGION
        region_cv = (left, top, right - left, bottom - top)

        # Support counts
        support_counts = check_support_card(screenshot)
        total_support = sum(support_counts.values())

        # Bond levels per type
        detailed_support = {}
        rgb_img = screenshot.convert("RGB")
        width, height = rgb_img.size
        dx, dy = BOND_SAMPLE_OFFSET
        for t_key, tpl in SUPPORT_ICON_TMPLS.items():
            matches = _filtered_template_matches(screenshot, tpl, region_cv, confidence=0.8)
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
                    "bbox": [int(x), int(y), int(w), int(h)],
                    "center": [cx, cy],
                    "bond_sample_point": [int(sx), int(sy)],
                    "bond_color": [int(r), int(g), int(b)],
                    "bond_level": int(level),
                })
            if entries:
                detailed_support[t_key] = entries

        # Hint
        hint_found = check_hint(screenshot)

        # Calculate score for this training type
        from core.state_adb import calculate_training_score
        score = calculate_training_score(detailed_support, hint_found, key)

        debug_print(f"[DEBUG] Support counts: {support_counts} | hint_found={hint_found} | score={score}")

        debug_print(f"[DEBUG] Checking failure rate for {key.upper()} training...")
        failure_chance, confidence = check_failure(screenshot, key)
        
        results[key] = {
            "support": support_counts,
            "support_detail": detailed_support,
            "hint": bool(hint_found),
            "total_support": total_support,
            "failure": failure_chance,
            "confidence": confidence,
            "score": score
        }

        if score >= 2.0:
            high_score_found = True
        
        # Use clean format matching training_score_test.py exactly
        print(f"\n[{key.upper()}]")
        
        # Show support card details (similar to test script)
        if detailed_support:
            support_lines = []
            for card_type, entries in detailed_support.items():
                for idx, entry in enumerate(entries, start=1):
                    level = entry['bond_level']
                    is_rainbow = (card_type == key and level >= 4)
                    label = f"{card_type.upper()}{idx}: {level}"
                    if is_rainbow:
                        label += " (Rainbow)"
                    support_lines.append(label)
            print(", ".join(support_lines))
        else:
            print("-")
        
        print(f"hint={hint_found}")
        print(f"Fail: {failure_chance}% - Confident: {confidence:.2f}")
        print(f"Score: {score}")
    
    # Print overall summary
    print("\n=== Overall ===")
    for k in ["spd", "sta", "pwr", "guts", "wit"]:
        if k in results:
            data = results[k]
            print(f"{k.upper()}: Score={data['score']:.2f}, Fail={data['failure']}% - Confident: {data['confidence']:.2f}")
    
    return results

def do_train(train):
    """Perform training of specified type"""
    debug_print(f"[DEBUG] Performing {train.upper()} training...")
    
    # Fixed coordinates for each training type
    training_coords = {
        "spd": (165, 1557),
        "sta": (357, 1563),
        "pwr": (546, 1557),
        "guts": (735, 1566),
        "wit": (936, 1572)
    }
    
    # Check if the requested training type exists
    if train not in training_coords:
        debug_print(f"[DEBUG] Unknown training type: {train}")
        return
    
    # Get the coordinates for the requested training type
    train_coords = training_coords[train]
    debug_print(f"[DEBUG] Found {train.upper()} training at coordinates {train_coords}")
    triple_click(train_coords[0], train_coords[1], interval=0.1)
    debug_print(f"[DEBUG] Triple clicked {train.upper()} training button")