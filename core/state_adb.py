import time
import json
import os
from core.logic import filter_by_stat_caps
import cv2
import pytesseract
import re
import numpy as np
import tkinter as tk
from tkinter import messagebox

from utils.skill_auto_purchase import cache_skill_points
from PIL import Image, ImageEnhance
from core.templates_adb import BACK_BUTTON_TEMPLATE, HINT_TEMPLATE, SKILLS_BUTTON_TEMPLATE
from utils.adb_screenshot import capture_region, enhanced_screenshot, take_screenshot
from core.ocr import extract_text, extract_number, extract_mood_text
from utils.adb_recognizer import match_template
from utils.skill_auto_purchase import execute_skill_purchases, click_image_button, extract_skill_points
from utils.skill_recognizer import scan_all_skills_with_scroll
from utils.skill_purchase_optimizer import load_skill_config, create_purchase_plan, filter_affordable_skills

from utils.constants_phone import (
    FAILURE_REGION_GUTS, FAILURE_REGION_PWR, FAILURE_REGION_SPD, FAILURE_REGION_STA, FAILURE_REGION_WIT, SUPPORT_CARD_ICON_REGION, MOOD_REGION, TURN_REGION, YEAR_REGION, 
    MOOD_LIST, CRITERIA_REGION, SPD_REGION, STA_REGION, PWR_REGION, GUTS_REGION, WIT_REGION,
    SKILL_PTS_REGION
)

from core.config import Config

# Load config and check debug mode
config = Config.load()
DEBUG_MODE = config.get("debug_mode", False)

def debug_print(message):
    """Print debug message only if DEBUG_MODE is enabled"""
    if DEBUG_MODE:
        print(message)

SUPPORT_ICON_PATHS = {
    "spd": "assets/icons/support_card_type_spd.png",
    "sta": "assets/icons/support_card_type_sta.png",
    "pwr": "assets/icons/support_card_type_pwr.png",
    "guts": "assets/icons/support_card_type_guts.png",
    "wit": "assets/icons/support_card_type_wit.png",
    "friend": "assets/icons/support_card_type_friend.png"
}

SUPPORT_ICON_TMPLS = {
    key: cv2.imread(path, cv2.IMREAD_COLOR)
    for key, path in SUPPORT_ICON_PATHS.items()
}

# Get Stat
def stat_state(screenshot):
    stat_regions = {
        "spd": SPD_REGION,
        "sta": STA_REGION,
        "pwr": PWR_REGION,
        "guts": GUTS_REGION,
        "wit": WIT_REGION
    }

    result = {}
    for stat, region in stat_regions.items():
        img = enhanced_screenshot(screenshot, region)
        val = extract_number(img)
        digits = ''.join(filter(str.isdigit, val))
        result[stat] = int(digits) if digits.isdigit() else 0
    return result

# Check support card in each training
def check_support_card(screenshot, threshold=0.85):
    count_result = {}

    # Save full screenshot for debugging only in debug mode
    if DEBUG_MODE:
        screenshot.save("debug_support_cards_screenshot.png")
        debug_print(f"[DEBUG] Saved full screenshot to debug_support_cards_screenshot.png")

    # Convert PIL region format (left, top, right, bottom) to OpenCV format (x, y, width, height)
    left, top, right, bottom = SUPPORT_CARD_ICON_REGION
    region_cv = (left, top, right - left, bottom - top)
    debug_print(f"[DEBUG] Searching in region: {region_cv} (PIL format: {SUPPORT_CARD_ICON_REGION})")
    
    # Crop and save the search region for debugging only in debug mode
    if DEBUG_MODE:
        search_region = screenshot.crop(SUPPORT_CARD_ICON_REGION)
        search_region.save("debug_support_cards_search_region.png")
        debug_print(f"[DEBUG] Saved search region to debug_support_cards_search_region.png")

    for key, icon_path in SUPPORT_ICON_TMPLS.items():
        debug_print(f"\n[DEBUG] Testing {key.upper()} support card detection...")
        
        # Use single threshold for faster detection
        matches = match_template(screenshot, icon_path, 0.8, region_cv)
        filtered_matches = []
        
        if matches:
            # Efficient duplicate filtering
            for match in matches:
                x, y, w, h = match
                center_x, center_y = x + w//2, y + h//2
                
                # Check if this match is too close to existing matches
                is_duplicate = False
                for existing in filtered_matches:
                    ex, ey, ew, eh = existing
                    existing_center_x, existing_center_y = ex + ew//2, ey + eh//2
                    # If centers are within 30 pixels, consider it a duplicate
                    if abs(center_x - existing_center_x) < 30 and abs(center_y - existing_center_y) < 30:
                        is_duplicate = True
                        break
                
                if not is_duplicate:
                    filtered_matches.append(match)
            
            debug_print(f"[DEBUG] Found {len(filtered_matches)} {key.upper()} support cards (filtered from {len(matches)})")
            
            # Show coordinates of each match
            for i, match in enumerate(filtered_matches):
                x, y, w, h = match
                center_x, center_y = x + w//2, y + h//2
                debug_print(f"[DEBUG]   {key.upper()} match {i+1}: center=({center_x}, {center_y}), bbox=({x}, {y}, {w}, {h})")
        
        # Skip expensive image annotation and only save debug images when DEBUG_MODE is true
        if not filtered_matches:
            debug_print(f"[DEBUG] No {key.upper()} support cards found")
        
        count_result[key] = len(filtered_matches) if filtered_matches else 0
        
        # Debug output for each support card type
        if count_result[key] > 0:
            debug_print(f"[DEBUG] {key.upper()} support cards found: {count_result[key]}")

    return count_result

def check_hint(screenshot, template = HINT_TEMPLATE, confidence: float = 0.6) -> bool:
    """Detect presence of a hint icon within the support card search region.

    Args:
        template_path: Path to the hint icon template image.
        confidence: Minimum confidence threshold for template matching.

    Returns:
        True if at least one hint icon is found in `SUPPORT_CARD_ICON_REGION`, otherwise False.
    """
    try:
        # Convert PIL (left, top, right, bottom) to OpenCV (x, y, width, height)
        left, top, right, bottom = SUPPORT_CARD_ICON_REGION
        region_cv = (left, top, right - left, bottom - top)
        debug_print(f"[DEBUG] Checking hint in region: {region_cv}")

        if DEBUG_MODE:
            try:
                screenshot.crop(SUPPORT_CARD_ICON_REGION).save("debug_hint_search_region.png")
                debug_print("[DEBUG] Saved hint search region to debug_hint_search_region.png")
            except Exception:
                pass

        matches = match_template(screenshot, template, confidence, region_cv)

        found = bool(matches and len(matches) > 0)
        debug_print(f"[DEBUG] Hint icon found: {found}")
        return found
    except Exception as e:
        debug_print(f"[DEBUG] check_hint failed: {e}")
        return False

def check_failure(screenshot, train_type):
    """
    Check failure rate for a specific training type using direct region OCR.
    Args:
        train_type (str): One of 'spd', 'sta', 'pwr', 'guts', 'wit'
    Returns:
        (rate, confidence)
    """
    debug_print(f"[DEBUG] ===== STARTING FAILURE DETECTION for {train_type.upper()} =====")

    region_map = {
        'spd': FAILURE_REGION_SPD,
        'sta': FAILURE_REGION_STA,
        'pwr': FAILURE_REGION_PWR,
        'guts': FAILURE_REGION_GUTS,
        'wit': FAILURE_REGION_WIT
    }
    region = region_map[train_type]
    percentage_patterns = [
        r"(\d{1,3})\s*%",  # "29%", "29 %" - most reliable
        r"%\s*(\d{1,3})",  # "% 29" - reversed format
        r"(\d{1,3})",      # Just the number - fallback
    ]
    # Step 1: Try white-specialized OCR 3 times
    for attempt in range(3):
        debug_print(f"[DEBUG] White OCR attempt {attempt+1}/3 for {train_type.upper()}")
        img = enhanced_screenshot(screenshot, region)
        if DEBUG_MODE:
            img.save(f"debug_failure_{train_type}_white_attempt_{attempt+1}.png")
        
        # Get OCR data with confidence
        ocr_data = pytesseract.image_to_data(np.array(img), config='--oem 3 --psm 6', output_type=pytesseract.Output.DICT)
        text = pytesseract.image_to_string(np.array(img), config='--oem 3 --psm 6').strip()
        debug_print(f"[DEBUG] White OCR result: '{text}'")
        
        # Calculate average confidence from OCR data
        confidences = [conf for conf in ocr_data['conf'] if conf != -1]
        avg_confidence = (sum(confidences) / len(confidences) / 100.0) if confidences else 0.0
        
        for pattern in percentage_patterns:
            match = re.search(pattern, text)
            if match:
                rate = int(match.group(1))
                if 0 <= rate <= 100:
                    debug_print(f"[DEBUG] Found percentage: {rate}% (white) confidence: {avg_confidence:.2f} for {train_type.upper()}")
                    if avg_confidence >= 0.7:
                        debug_print(f"[DEBUG] Confidence {avg_confidence:.2f} meets minimum 0.7, accepting result")
                        return (rate, avg_confidence)
                    else:
                        debug_print(f"[DEBUG] Confidence {avg_confidence:.2f} below minimum 0.7, continuing to retry")
        if attempt < 2:
            debug_print("[DEBUG] No valid percentage found, retrying...")
            time.sleep(0.1)
    # Step 2: Try yellow threshold OCR 3 times
    for attempt in range(3):
        debug_print(f"[DEBUG] Yellow OCR attempt {attempt+1}/3 for {train_type.upper()}")
        raw_img = take_screenshot().crop(region)
        raw_img = raw_img.resize((raw_img.width * 2, raw_img.height * 2), Image.BICUBIC)
        raw_img = raw_img.convert("RGB")
        raw_np = np.array(raw_img)
        yellow_mask = (
            (raw_np[:, :, 0] > 180) &  # High red
            (raw_np[:, :, 1] > 120) &  # High green
            (raw_np[:, :, 2] < 80)     # Low blue
        )
        yellow_result = np.zeros_like(raw_np)
        yellow_result[yellow_mask] = [255, 255, 255]
        yellow_img = Image.fromarray(yellow_result).convert("L")
        yellow_img = ImageEnhance.Contrast(yellow_img).enhance(1.5)
        if DEBUG_MODE:
            yellow_img.save(f"debug_failure_{train_type}_yellow_attempt_{attempt+1}.png")
        
        # Get OCR data with confidence
        ocr_data = pytesseract.image_to_data(np.array(yellow_img), config='--oem 3 --psm 6', output_type=pytesseract.Output.DICT)
        text = pytesseract.image_to_string(np.array(yellow_img), config='--oem 3 --psm 6').strip()
        debug_print(f"[DEBUG] Yellow OCR result: '{text}'")
        
        # Calculate average confidence from OCR data
        confidences = [conf for conf in ocr_data['conf'] if conf != -1]
        avg_confidence = (sum(confidences) / len(confidences) / 100.0) if confidences else 0.0
        
        for pattern in percentage_patterns:
            match = re.search(pattern, text)
            if match:
                rate = int(match.group(1))
                if 0 <= rate <= 100:
                    debug_print(f"[DEBUG] Found percentage: {rate}% (yellow) confidence: {avg_confidence:.2f} for {train_type.upper()}")
                    if avg_confidence >= 0.7:
                        debug_print(f"[DEBUG] Confidence {avg_confidence:.2f} meets minimum 0.7, accepting result")
                        return (rate, avg_confidence)
                    else:
                        debug_print(f"[DEBUG] Confidence {avg_confidence:.2f} below minimum 0.7, continuing to retry")
        if attempt < 2:
            debug_print("[DEBUG] No valid yellow percentage found, retrying...")
            time.sleep(0.1)
    debug_print(f"[DEBUG] No valid failure rate found for {train_type.upper()}, returning 100% (safe fallback)")
    return (100, 0.0)  # 100% failure rate when detection completely fails (prevents choosing unknown training)

def fuzzy_match_mood(text):
    """
    Perform fuzzy matching for mood detection using pattern-based approach.
    
    Args:
        text (str): The OCR text to match (should be uppercase)
    
    Returns:
        str: The matched mood or "UNKNOWN" if no match found
    """
    # First, try exact match
    if text in MOOD_LIST:
        return text
    
    # Clean common OCR errors
    cleaned_text = text.replace('0', 'O').replace('1', 'I').replace('5', 'S')
    
    # Fuzzy pattern matching with priority order (most restrictive first)
    # AWFUL patterns - check first since it's most likely to be misread
    if any(pattern in cleaned_text for pattern in ['AWF', 'AWFUL', 'AWFU', 'VAWF', 'WAWF']):
        debug_print(f"[DEBUG] AWFUL pattern match in: '{text}'")
        return "AWFUL"
    
    # GREAT patterns - check before GOOD to avoid conflicts
    if any(pattern in cleaned_text for pattern in ['GREAT', 'GREA', 'REAT', 'EA']):
        debug_print(f"[DEBUG] GREAT pattern match in: '{text}'")
        return "GREAT"
    
    # GOOD patterns
    if any(pattern in cleaned_text for pattern in ['GOOD', 'GOO', 'OOD', 'OO']):
        debug_print(f"[DEBUG] GOOD pattern match in: '{text}'")
        return "GOOD"
    
    # NORMAL patterns
    if any(pattern in cleaned_text for pattern in ['NORMAL', 'NORMA', 'ORMA', 'RMAL']):
        debug_print(f"[DEBUG] NORMAL pattern match in: '{text}'")
        return "NORMAL"
    
    # BAD patterns - check last since it's short and might false positive
    if any(pattern in cleaned_text for pattern in ['BAD']) and 'AWF' not in cleaned_text:
        debug_print(f"[DEBUG] BAD pattern match in: '{text}'")
        return "BAD"
    
    # Final fallback: check for partial substring matches
    for mood in MOOD_LIST:
        if mood in cleaned_text:
            debug_print(f"[DEBUG] Substring match: '{mood}' in '{text}'")
            return mood
    
    debug_print(f"[DEBUG] No fuzzy match found for: '{text}'")
    return "UNKNOWN"

def check_mood(screenshot):
    # Try up to 3 times to detect mood
    max_attempts = 3
    
    for attempt in range(1, max_attempts + 1):
        mood_img = enhanced_screenshot(screenshot, MOOD_REGION)
        mood_text = extract_mood_text(mood_img)
        
        # Apply fuzzy matching for mood detection
        mood_text_upper = mood_text.upper()
        detected_mood = fuzzy_match_mood(mood_text_upper)
        
        if detected_mood != "UNKNOWN":
            if mood_text != detected_mood:
                debug_print(f"[DEBUG] Fuzzy mood match: '{mood_text}' -> '{detected_mood}'")
            return detected_mood
        
        print(f"[WARNING] Mood not recognized on attempt {attempt}/{max_attempts}: {mood_text}")
        
        if attempt < max_attempts:
            print(f"{attempt}). Retrying...")
            time.sleep(0.5)
    
    print(f"[WARNING] Mood not recognized after {max_attempts} attempts: {mood_text}")
    return "UNKNOWN"

def check_turn(screenshot):
    """Fast turn detection with minimal OCR"""
    debug_print("[DEBUG] Starting turn detection...")
    
    try:
        turn_img = enhanced_screenshot(screenshot, TURN_REGION)
        debug_print(f"[DEBUG] Turn region screenshot taken: {TURN_REGION}")
        
        # Save the turn region image for debugging
        turn_img.save("debug_turn_region.png")
        debug_print("[DEBUG] Saved turn region image to debug_turn_region.png")
        
        # Apply additional enhancement for better digit recognition
        # Increase contrast more aggressively for turn detection
        contrast_enhancer = ImageEnhance.Contrast(turn_img)
        turn_img = contrast_enhancer.enhance(2.0)  # More aggressive contrast
        
        # Increase sharpness to make digits clearer
        sharpness_enhancer = ImageEnhance.Sharpness(turn_img)
        turn_img = sharpness_enhancer.enhance(2.0)
        
        # Save the enhanced version
        turn_img.save("debug_turn_enhanced.png")
        debug_print("[DEBUG] Saved enhanced turn image to debug_turn_enhanced.png")
        
        # Apply basic grayscale processing (like test_turn_basic_grayscale)
        turn_img = turn_img.convert("L")
        turn_img = turn_img.resize((turn_img.width * 2, turn_img.height * 2), Image.BICUBIC)
        
        # Use PSM 7 (single line) which had 94% confidence in testing
        turn_text = pytesseract.image_to_string(turn_img, config='--oem 3 --psm 7').strip()
        debug_print(f"[DEBUG] Turn OCR raw result: '{turn_text}'")
        
        # Check for "Race Day" first (before character replacements that would corrupt it)
        if "Race Day" in turn_text or "RaceDay" in turn_text or "Race Da" in turn_text:
            debug_print(f"[DEBUG] Race Day detected: {turn_text}")
            return "Race Day"
        
        # Character replacements for common OCR errors (only for digit extraction)
        original_text = turn_text
        turn_text = turn_text.replace('y', '9').replace(']', '1').replace('l', '1').replace('I', '1').replace('o', '0').replace('O', '0').replace('/', '7')
        debug_print(f"[DEBUG] Turn OCR after character replacement: '{turn_text}' (was '{original_text}')")
        
        # Extract all consecutive digits (not just first digit)
        digit_match = re.search(r'(\d+)', turn_text)
        if digit_match:
            turn_num = int(digit_match.group(1))
            debug_print(f"[DEBUG] Turn OCR result: {turn_num} (from '{turn_text}')")
            return turn_num
        
        debug_print(f"[DEBUG] No digits found in turn text: '{turn_text}', defaulting to 1")
        return 1  # Default to turn 1
        
    except Exception as e:
        debug_print(f"[DEBUG] Turn detection failed with error: {e}")
        return 1

def is_pre_debut_year(year):
    return ("Pre-Debut" in year or "PreDebut" in year or 
            "PreeDebut" in year or "Pre" in year)

def check_current_year(screenshot):
    """Fast year detection using regular screenshot"""
    year_img = enhanced_screenshot(screenshot, YEAR_REGION)
    
    # Simple OCR with PSM 7 (single line text)
    text = pytesseract.image_to_string(year_img, config='--oem 3 --psm 7').strip()
    
    if text:
        debug_print(f"[DEBUG] Year OCR result: '{text}'")
        return text
    
    return "Unknown Year"

def check_criteria(screenshot):
    """Enhanced criteria detection"""
    criteria_img = enhanced_screenshot(screenshot, CRITERIA_REGION)
    
    # Use single, fast OCR configuration
    text = pytesseract.image_to_string(criteria_img, config='--oem 3 --psm 7').strip()
    
    if text:
        # Apply common OCR corrections
        text = text.replace("Entrycriteriamet", "Entry criteria met")
        text = text.replace("Entrycriteria", "Entry criteria")  
        text = text.replace("criteriamet", "criteria met")
        text = text.replace("Goalachieved", "Goal achieved")
        
        debug_print(f"[DEBUG] Criteria OCR result: '{text}'")
    else:
        # Single fallback attempt
        fallback_text = extract_text(criteria_img)
        if fallback_text.strip():
            debug_print(f"[DEBUG] Using fallback criteria OCR result: '{fallback_text}'")
            text = fallback_text.strip()
        else:
            text = "Unknown Criteria"
    
    return text

def check_goal_name(screenshot):
    """Detect the current goal name using simple Tesseract OCR.

    Captures the region (372, 113, 912, 152) and returns the recognized
    goal name as a string. Mirrors the lightweight OCR approach used in
    check_criteria (PSM 7, single line) with a single fallback to the
    shared extract_text helper.
    """
    GOAL_REGION = (372, 113, 912, 152)

    # Capture enhanced image of the goal name region for better OCR
    goal_img = enhanced_screenshot(screenshot, GOAL_REGION)

    # Save debug images if enabled
    if DEBUG_MODE:
        try:
            raw_img = capture_region(GOAL_REGION)
            raw_img.save("debug_goal_region_raw.png")
        except Exception:
            pass
        try:
            goal_img.save("debug_goal_region_enhanced.png")
        except Exception:
            pass

    # Primary OCR path: single line recognition
    text = pytesseract.image_to_string(goal_img, config='--oem 3 --psm 7').strip()

    if not text:
        # Fallback once to the shared OCR helper
        fallback_text = extract_text(goal_img)
        if fallback_text.strip():
            debug_print(f"[DEBUG] Using fallback goal OCR result: '{fallback_text}'")
            text = fallback_text.strip()

    if DEBUG_MODE:
        debug_print(f"[DEBUG] Goal name OCR result: '{text}'")

    return text

def check_goal_name_with_g1_requirement(screenshot):
    """Detect the current goal name and check if it requires G1 races.
    
    Returns:
        dict: Dictionary with goal name text and G1 race requirement flag
    """
    goal_name = check_goal_name(screenshot)
    
    # Check if goal name contains G1 race requirements
    requires_g1_races = False
    if goal_name and "G1" in goal_name.upper():
        requires_g1_races = True
        debug_print(f"[DEBUG] G1 race requirement detected in goal name: '{goal_name}'")
    
    return {
        "text": goal_name,
        "requires_g1_races": requires_g1_races
    }

def check_skill_points(screenshot):
    skill_img = enhanced_screenshot(screenshot, SKILL_PTS_REGION)
    
    # Apply sharpening for better OCR accuracy
    sharpener = ImageEnhance.Sharpness(skill_img)
    skill_img_sharp = sharpener.enhance(2.5)  # Increase sharpness by 2.5x
    
    # Save debug images for skill points OCR troubleshooting
    skill_img.save("debug_skill_points_original.png")
    skill_img_sharp.save("debug_skill_points_sharpened.png")
    debug_print(f"[DEBUG] Saved original skill points image to debug_skill_points_original.png")
    debug_print(f"[DEBUG] Saved sharpened skill points image to debug_skill_points_sharpened.png")
    debug_print(f"[DEBUG] Skill points region: {SKILL_PTS_REGION}")
    
    # Use sharpened image for OCR
    skill_text = extract_number(skill_img_sharp)
    digits = ''.join(filter(str.isdigit, skill_text))
    
    debug_print(f"[DEBUG] Skill points OCR raw result: '{skill_text}'")
    debug_print(f"[DEBUG] Extracted digits: '{digits}'")
    
    result = int(digits) if digits.isdigit() else 0
    debug_print(f"[DEBUG] Final skill points value: {result}")
    
    # Cache the skill points for reuse in skill auto-purchase
    if result > 0:
        cache_skill_points(result)
    
    return result

def check_skills_are_available(bought_skills):
    # Load config
    skill_file = config.get("skill_file", "skills.json")
    print(f"[INFO] Loading skills from: {skill_file}")
    cfg = load_skill_config(skill_file)
    skill_priority = cfg.get("skill_priority", [])

    for skill in skill_priority:
        if skill not in bought_skills:
            return True
    
    print("[INFO] All skills are bought, skipping buying skills")
    return False

def check_skill_points_cap(screenshot, bought_skills):
    """Check skill points and handle cap logic (same as PC version)"""
    skill_point_cap = config.get("skill_point_cap", 9999)
    current_skill_points = check_skill_points(screenshot)
    
    print(f"[INFO] Current skill points: {current_skill_points}, Cap: {skill_point_cap}")
    
    if current_skill_points > skill_point_cap:
        print(f"[WARNING] Skill points ({current_skill_points}) exceed cap ({skill_point_cap})")
        
        # Decide flow based on config
        skill_purchase_mode = config.get("skill_purchase", "manual").lower()
        if skill_purchase_mode == "auto":
            print("[INFO] Auto skill purchase enabled - starting automation")
            try:
                # 1) Enter skill screen
                entered = click_image_button(SKILLS_BUTTON_TEMPLATE, "skills button", max_attempts=5)
                if not entered:
                    print("[ERROR] Could not find/open skills screen")
                    return True
                time.sleep(2.0)

                # 2) Scan skills and prepare purchase plan
                scan_result = scan_all_skills_with_scroll()
                if 'error' in scan_result:
                    print(f"[ERROR] Skill scanning failed: {scan_result['error']}")
                    # Attempt to go back anyway
                    click_image_button(BACK_BUTTON_TEMPLATE, "back button", max_attempts=5)
                    time.sleep(1.5)
                    return True
                all_skills = scan_result.get('all_skills', [])
                if not all_skills:
                    print("[WARNING] No skills detected on skill screen")
                    click_image_button(BACK_BUTTON_TEMPLATE, "back button", max_attempts=5)
                    time.sleep(1.5)
                    return True

                # Read current available skill points from the skill screen
                available_points = extract_skill_points()
                print(f"[INFO] Detected available skill points: {available_points}")

                # Build purchase plan from config priorities
                skill_file = config.get("skill_file", "skills.json")
                print(f"[INFO] Loading skills from: {skill_file}")
                cfg = load_skill_config(skill_file)
                purchase_plan = create_purchase_plan(all_skills, cfg)
                if not purchase_plan:
                    print("[INFO] No skills from priority list are currently available")
                    click_image_button(BACK_BUTTON_TEMPLATE, "back button", max_attempts=5)
                    time.sleep(1.5)
                    return True

                # Filter by budget if we have points
                final_plan = purchase_plan
                if isinstance(available_points, int) and available_points > 0:
                    affordable_skills, total_cost, remaining_points = filter_affordable_skills(purchase_plan, available_points)
                    final_plan = affordable_skills if affordable_skills else []
                    print(f"[INFO] Affordable skills: {len(final_plan)}; Total cost: {total_cost}; Remaining: {remaining_points}")

                if not final_plan:
                    print("[INFO] Nothing affordable to purchase at the moment")
                    click_image_button(BACK_BUTTON_TEMPLATE, "back button", max_attempts=5)
                    time.sleep(1.5)
                    return True

                # Execute automated purchases
                exec_result = execute_skill_purchases(final_plan, bought_skills)
                if not exec_result.get('success'):
                    print(f"[WARNING] Automated purchase completed with issues: {exec_result.get('error', 'unknown error')}")

                # 3) Return to lobby
                back = click_image_button(BACK_BUTTON_TEMPLATE, "back button", max_attempts=5)
                if not back:
                    print("[WARNING] Could not find back button after purchases; ensure you return to lobby manually")
                time.sleep(1.5)
            except Exception as e:
                print(f"[ERROR] Auto skill purchase failed: {e}")
            
            return True
        
        # Manual mode (original prompt)
        try:
            # Create a hidden root window
            root = tk.Tk()
            root.withdraw()  # Hide the main window
            
            # Show the message box
            result = messagebox.showinfo(
                title="Skill Points Cap Reached",
                message=f"Skill points ({current_skill_points}) exceed the cap ({skill_point_cap}).\n\nYou can:\n• Use your skill points manually, then click OK\n• Click OK without spending (automation continues)\n\nNote: This check only happens on race days."
            )
            
            # Destroy the root window
            root.destroy()
            
            print("[INFO] Player acknowledged skill points cap warning")
            
        except Exception as e:
            print(f"[ERROR] Failed to show GUI popup: {e}")
            print("[INFO] Skill points cap reached - automation continuing")
        
        return True
    
    return True

def check_current_stats(screenshot):
    """
    Check current character stats using OCR on the stat regions.
    
    Returns:
        dict: Dictionary of current stats with keys: spd, sta, pwr, guts, wit
    """
    stats = {}
    stat_regions = {
        'spd': SPD_REGION,
        'sta': STA_REGION,
        'pwr': PWR_REGION,
        'guts': GUTS_REGION,
        'wit': WIT_REGION
    }
    
    for stat_name, region in stat_regions.items():
        try:
            # Take screenshot and crop to stat region
            stat_img = screenshot.crop(region)
            
            # Enhance image for better OCR
            stat_img = stat_img.resize((stat_img.width * 2, stat_img.height * 2), Image.BICUBIC)
            stat_img = stat_img.convert("L")  # Convert to grayscale
            stat_img = ImageEnhance.Contrast(stat_img).enhance(2.0)  # Increase contrast
            
            # OCR the stat value
            stat_text = pytesseract.image_to_string(stat_img, config='--oem 3 --psm 7 -c tessedit_char_whitelist=0123456789').strip()
            
            # Try to extract the number
            if stat_text:
                # Remove any non-digit characters and take the first number
                numbers = re.findall(r'\d+', stat_text)
                if numbers:
                    stats[stat_name] = int(numbers[0])
                    debug_print(f"[DEBUG] {stat_name.upper()} stat: {stats[stat_name]}")
                else:
                    stats[stat_name] = 0
                    debug_print(f"[DEBUG] Failed to extract {stat_name.upper()} stat from text: '{stat_text}'")
            else:
                stats[stat_name] = 0
                debug_print(f"[DEBUG] No text found for {stat_name.upper()} stat")
                
        except Exception as e:
            debug_print(f"[DEBUG] Error reading {stat_name.upper()} stat: {e}")
            stats[stat_name] = 0
    
    debug_print(f"[DEBUG] Current stats: {stats}")
    return stats

def calculate_training_score(support_detail, hint_found, training_type):
    """
    Calculate training score based on support cards, bond levels, and hints.
    
    Args:
        support_detail: Dictionary of support card details with bond levels
        hint_found: Boolean indicating if hint is present
        training_type: The type of training being evaluated
    
    Returns:
        float: Calculated score for the training
    """
    # Load scoring rules from training_score.json
    scoring_rules = config.get('scoring_rules', {})
    score = 0.0
    
    # Score support cards based on bond levels
    for card_type, entries in support_detail.items():
        for entry in entries:
            level = entry['bond_level']
            is_rainbow = (card_type == training_type and level >= 4)
            
            if is_rainbow:
                score += scoring_rules.get("rainbow_support", {}).get("points", 1.0)
            else:
                if level < 4:
                    score += scoring_rules.get("not_rainbow_support_low", {}).get("points", 0.7)
                # bond >= 4 for non-rainbow gets points from not_rainbow_support_high (0.0)
    
    # Add hint bonus
    if hint_found:
        score += scoring_rules.get("hint", {}).get("points", 0.3)
    
    return round(score, 2)

def check_energy_bar(screenshot):
    """
    Check the energy bar fill percentage using the same logic as energy_detector.py.
    
    Returns:
        float: Energy percentage (0.0 to 100.0)
    """
    try:
        # Take screenshot and crop to energy bar region (updated coordinates from user)
        x, y, width, height = 294, 203, 648, 102
        cropped = screenshot.crop((x, y, x + width, y + height))
        
        # Convert to numpy array and handle RGBA -> RGB
        cropped_np = np.array(cropped, dtype=np.uint8)
        if cropped_np.shape[2] == 4:
            cropped_np = cropped_np[:, :, :3]  # Keep only RGB channels
        
        # Step 1: Find the white border (253, 253, 253)
        white_tolerance = 5
        white_lower = np.array([253 - white_tolerance, 253 - white_tolerance, 253 - white_tolerance])
        white_upper = np.array([253 + white_tolerance, 253 + white_tolerance, 253 + white_tolerance])
        white_mask = cv2.inRange(cropped_np, white_lower, white_upper)
        
        # Step 2: Find the rounded rectangle contour and create an interior mask
        contours, _ = cv2.findContours(white_mask.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if not contours:
            debug_print("[DEBUG] No energy bar contour found")
            return 0.0
        
        # Find the largest contour (should be the energy bar's outer white border)
        largest_contour = max(contours, key=cv2.contourArea)
        
        # Create a mask for the area enclosed by the white border
        border_mask = np.zeros(cropped_np.shape[:2], dtype=np.uint8)
        cv2.drawContours(border_mask, [largest_contour], -1, 255, cv2.FILLED)
        
        # Erode the border mask to get the interior (remove the border itself)
        kernel = np.ones((5,5), np.uint8)
        interior_mask = cv2.erode(border_mask, kernel, iterations=1)
        
        # Step 3: Count gray pixels vs total pixels in the interior using horizontal line analysis
        # Create mask for gray pixels (117, 117, 117)
        gray_tolerance = 10
        gray_lower = np.array([117 - gray_tolerance, 117 - gray_tolerance, 117 - gray_tolerance])
        gray_upper = np.array([117 + gray_tolerance, 117 + gray_tolerance, 117 + gray_tolerance])
        gray_mask = cv2.inRange(cropped_np, gray_lower, gray_upper)
        
        # Apply interior mask to only consider gray pixels inside the rounded rectangle
        gray_pixels_inside = cv2.bitwise_and(gray_mask, interior_mask)
        
        # Horizontal line analysis
        contours_interior, _ = cv2.findContours(interior_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if not contours_interior:
            debug_print("[DEBUG] No interior contour found")
            return 0.0
        
        x_rect, y_rect, w_rect, h_rect = cv2.boundingRect(contours_interior[0])
        
        # Use the middle horizontal line for analysis
        middle_y = y_rect + h_rect // 2
        
        # Ensure middle_y is within bounds
        if not (0 <= middle_y < interior_mask.shape[0]):
            debug_print("[DEBUG] Middle Y coordinate out of bounds")
            return 0.0
        
        # Extract the horizontal line from both interior and gray masks
        interior_line = interior_mask[middle_y, :]
        gray_line = gray_pixels_inside[middle_y, :]
        
        # Find the leftmost and rightmost points of the bar on this line
        interior_points = np.where(interior_line > 0)[0]
        if len(interior_points) > 0:
            leftmost = interior_points[0]
            rightmost = interior_points[-1]
            total_width = rightmost - leftmost + 1
            
            # Count gray pixels in this horizontal line within the bar's width
            gray_points = np.where(gray_line[leftmost:rightmost+1] > 0)[0]
            gray_width = len(gray_points)
            filled_width = total_width - gray_width
            
            # Calculate fill percentage based on horizontal line
            fill_percentage = (filled_width / total_width) * 100.0 if total_width > 0 else 0.0
            
            debug_print(f"[DEBUG] Energy bar: width={total_width}px, gray={gray_width}px, filled={filled_width}px, percentage={fill_percentage:.1f}%")
            return fill_percentage
        else:
            debug_print("[DEBUG] No interior points found on analysis line")
            return 0.0
            
    except Exception as e:
        debug_print(f"[DEBUG] Energy bar check failed: {e}")
        return 0.0

def choose_best_training(screenshot, training_results, config):
    """
    Choose the best training based on scoring algorithm and stat caps.
    
    Args:
        training_results: Dictionary of training results with scores, failure rates, etc.
        config: Configuration dictionary with thresholds and priorities
    
    Returns:
        str: Best training type to choose, or None if no suitable training
    """
    maximum_failure = config.get("maximum_failure", 15)
    min_score = config.get("min_score", 1.0)
    min_wit_score = config.get("min_wit_score", 1.0)
    priority_order = config.get("priority_stat", ["spd", "sta", "wit", "pwr", "guts"])
    
    # Get current stats for stat cap filtering
    current_stats = check_current_stats(screenshot)
    print(f"[INFO] Current stats: {current_stats}")
    debug_print(f"[DEBUG] Current stats for stat cap filtering: {current_stats}")
    
    # Filter by stat caps first
    filtered_results = filter_by_stat_caps(training_results, current_stats)
    print(f"[INFO] Training options after stat cap filtering: {list(filtered_results.keys())}")
    debug_print(f"[DEBUG] Training results after stat cap filtering: {list(filtered_results.keys())}")
    
    # Filter eligible trainings based on failure rate and score
    eligible = []
    for training_type, data in filtered_results.items():
        if data["failure"] > maximum_failure:
            print(f"[INFO] {training_type.upper()} filtered out: failure rate {data['failure']}% > {maximum_failure}%")
            debug_print(f"[DEBUG] {training_type.upper()} filtered out due to high failure rate: {data['failure']}% > {maximum_failure}%")
            continue
        
        # Apply appropriate score threshold
        threshold = min_wit_score if training_type == "wit" else min_score
        if data["score"] < threshold:
            print(f"[INFO] {training_type.upper()} filtered out: score {data['score']} < {threshold}")
            debug_print(f"[DEBUG] {training_type.upper()} filtered out due to low score: {data['score']} < {threshold}")
            continue
        
        eligible.append((training_type, data))
        print(f"[INFO] {training_type.upper()} eligible: failure={data['failure']}%, score={data['score']}")
        debug_print(f"[DEBUG] {training_type.upper()} is eligible: failure={data['failure']}%, score={data['score']}")
    
    if not eligible:
        print("[INFO] No eligible training found after all filtering")
        debug_print("[DEBUG] No eligible training found after all filtering")
        return None
    
    # Find training with highest score
    max_score = max(d["score"] for _, d in eligible)
    tied_trainings = [t for t, d in eligible if d["score"] == max_score]
    
    if len(tied_trainings) == 1:
        chosen = tied_trainings[0]
        chosen_data = next(d for t, d in eligible if t == chosen)
        print(f"[INFO] Selected {chosen.upper()} training: highest score {max_score} (failure: {chosen_data['failure']}%)")
        debug_print(f"[DEBUG] Single best training found: {chosen.upper()} with score {max_score}")
        return chosen
    
    # Tie-breaker: use priority order from config
    print(f"[INFO] {len(tied_trainings)} trainings tied with score {max_score}: {tied_trainings}")
    debug_print(f"[DEBUG] {len(tied_trainings)} trainings tied with score {max_score}: {tied_trainings}")
    order_index = {name: i for i, name in enumerate(priority_order)}
    chosen = min(tied_trainings, key=lambda x: order_index.get(x, 999))
    chosen_data = next(d for t, d in eligible if t == chosen)
    print(f"[INFO] Tie broken: {chosen.upper()} selected based on priority order (score: {max_score}, failure: {chosen_data['failure']}%)")
    debug_print(f"[DEBUG] Tie broken in favor of {chosen.upper()} based on priority order")
    
    return chosen 