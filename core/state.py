import re
import time
import json
import os

from PIL import Image, ImageEnhance
from utils.screenshot import capture_region, enhanced_screenshot, enhanced_screenshot_for_failure, enhanced_screenshot_for_year, take_screenshot
from core.ocr import extract_text, extract_number, extract_turn_number, extract_failure_text, extract_failure_text_with_confidence
from utils.recognizer import match_template, max_match_confidence
from core.skill_auto_purchase import execute_skill_purchases, click_image_button, extract_skill_points
from core.skill_recognizer import scan_all_skills_with_scroll
from core.skill_purchase_optimizer import load_skill_config, create_purchase_plan, filter_affordable_skills

from utils.constants_phone import (
    SUPPORT_CARD_ICON_REGION, TURN_REGION, FAILURE_REGION, YEAR_REGION, 
    CRITERIA_REGION, SPD_REGION, STA_REGION, PWR_REGION, GUTS_REGION, WIT_REGION,
    SKILL_PTS_REGION, FAILURE_REGION_SPD, FAILURE_REGION_STA, FAILURE_REGION_PWR, FAILURE_REGION_GUTS, FAILURE_REGION_WIT
)

# Load config and check debug mode
with open("config.json", "r", encoding="utf-8") as config_file:
    config = json.load(config_file)
    DEBUG_MODE = config.get("debug_mode", False)

from utils.log import log_debug, log_info, log_warning, log_error
from utils.template_matching import deduplicated_matches

# Get Stat
def stat_state(screenshot=None):
    stat_regions = {
        "spd": SPD_REGION,
        "sta": STA_REGION,
        "pwr": PWR_REGION,
        "guts": GUTS_REGION,
        "wit": WIT_REGION
    }

    result = {}
    for stat, region in stat_regions.items():
        img = enhanced_screenshot(region, screenshot)
        val = extract_number(img)
        digits = ''.join(filter(str.isdigit, val))
        result[stat] = int(digits) if digits.isdigit() else 0
    return result


# Old OCR fuzzy mood helper removed after switching to template-based detection

def check_mood(screenshot=None):
    """Detect mood using template matching in a fixed region.

    Uses the new template-based method instead of OCR. Returns one of
    MOOD_LIST values, or "UNKNOWN" if confidence is too low.
    """
    try:
        # Use provided screenshot or take a fresh one
        if screenshot is None:
            screenshot = take_screenshot()

        # Region (left, top, right, bottom) and its (x, y, w, h) variant
        region_pil = (774, 203, 1080, 287)
        x, y = region_pil[0], region_pil[1]
        region_cv = (x, y, region_pil[2] - region_pil[0], region_pil[3] - region_pil[1])

        templates = {
            "AWFUL": os.path.join("assets", "mood", "awful.png"),
            "BAD": os.path.join("assets", "mood", "bad.png"),
            "NORMAL": os.path.join("assets", "mood", "normal.png"),
            "GOOD": os.path.join("assets", "mood", "good.png"),
            "GREAT": os.path.join("assets", "mood", "great.png"),
        }

        # Allow threshold override via config; default to 0.55
        threshold = float(config.get("mood_template_threshold", 0.55))

        best_label = None
        best_score = -1.0
        scores = {}

        for label, path in templates.items():
            score = float(max_match_confidence(screenshot, path, region=region_cv) or 0.0)
            scores[label] = score
            if score > best_score:
                best_label = label
                best_score = score

        if DEBUG_MODE:
            log_debug(f"Mood scores: {scores}")

        if best_label is None or best_score < threshold:
            log_debug(f"Mood confidence too low: best={best_label} score={best_score:.3f} threshold={threshold:.2f}")
            return "UNKNOWN"

        return best_label
    except Exception as e:
        log_debug(f"Template mood detection failed: {e}")
        return "UNKNOWN"

def check_turn(screenshot=None):
    """Fast turn detection with minimal OCR"""
    log_debug(f"Starting turn detection...")
    
    try:
        turn_img = enhanced_screenshot(TURN_REGION, screenshot)
        log_debug(f"Turn region screenshot taken: {TURN_REGION}")
        
        # Save the turn region image for debugging
        if DEBUG_MODE:
            try:
                turn_img.save("debug_turn_region.png")
                log_debug(f"Saved turn region image to debug_turn_region.png")
            except Exception:
                pass
        
        # Apply additional enhancement for better digit recognition
        from PIL import ImageEnhance
        
        # Increase contrast more aggressively for turn detection
        contrast_enhancer = ImageEnhance.Contrast(turn_img)
        turn_img = contrast_enhancer.enhance(2.0)  # More aggressive contrast
        
        # Increase sharpness to make digits clearer
        sharpness_enhancer = ImageEnhance.Sharpness(turn_img)
        turn_img = sharpness_enhancer.enhance(2.0)
        
        # Save the enhanced version
        if DEBUG_MODE:
            try:
                turn_img.save("debug_turn_enhanced.png")
                log_debug(f"Saved enhanced turn image to debug_turn_enhanced.png")
            except Exception:
                pass
        
        # Use the best method found in testing: basic processing + PSM 7
        import pytesseract
        import re
        
        # Apply basic grayscale processing (like test_turn_basic_grayscale)
        turn_img = turn_img.convert("L")
        turn_img = turn_img.resize((turn_img.width * 2, turn_img.height * 2), Image.BICUBIC)
        
        # Use PSM 7 (single line) which had 94% confidence in testing
        turn_text = pytesseract.image_to_string(turn_img, config='--oem 3 --psm 7').strip()
        log_debug(f"Turn OCR raw result: '{turn_text}'")
        
        # Check for "Race Day" first (before character replacements that would corrupt it)
        if "Race Day" in turn_text or "RaceDay" in turn_text or "Race Da" in turn_text:
            log_debug(f"Race Day detected: {turn_text}")
            return "Race Day"
        
        # Character replacements for common OCR errors (only for digit extraction)
        original_text = turn_text
        turn_text = turn_text.replace('y', '9').replace(']', '1').replace('l', '1').replace('I', '1').replace('o', '8').replace('O', '0').replace('/', '7').replace('®', '9')
        log_debug(f"Turn OCR after character replacement: '{turn_text}' (was '{original_text})')")
        
        # Extract all consecutive digits (not just first digit)
        digit_match = re.search(r'(\d+)', turn_text)
        if digit_match:
            turn_num = int(digit_match.group(1))
            log_debug(f"Turn OCR result: {turn_num} (from '{turn_text})')")
            return turn_num
        
        log_debug(f"No digits found in turn text: '{turn_text}', defaulting to 1")
        return 1  # Default to turn 1
        
    except Exception as e:
        log_debug(f"Turn detection failed with error: {e}")
        return 1

def check_current_year(screenshot=None):
    """Fast year detection using regular screenshot"""
    year_img = enhanced_screenshot(YEAR_REGION, screenshot)
    
    import pytesseract
    text = pytesseract.image_to_string(year_img).strip()
    
    if text:
        # Clean OCR result - correct common OCR errors
        if "Pre-Debu" in text:
            text = text.replace("Pre-Debu", "Pre-Debut")
        
        log_debug(f"Year OCR result: '{text}'")
        return text
    
    return "Unknown Year"

def check_criteria(screenshot=None):
    """Enhanced criteria detection"""
    criteria_img = enhanced_screenshot(CRITERIA_REGION, screenshot)
    
    # Use single, fast OCR configuration
    import pytesseract
    text = pytesseract.image_to_string(criteria_img, config='--oem 3 --psm 7').strip()
    
    if text:
        # Apply common OCR corrections
        text = text.replace("Entrycriteriamet", "Entry criteria met")
        text = text.replace("Entrycriteria", "Entry criteria")  
        text = text.replace("criteriamet", "criteria met")
        text = text.replace("Goalachieved", "Goal achieved")
        
        log_debug(f"Criteria OCR result: '{text}'")
    else:
        # Single fallback attempt
        fallback_text = extract_text(criteria_img)
        if fallback_text.strip():
            log_debug(f"Using fallback criteria OCR result: '{fallback_text}'")
            text = fallback_text.strip()
        else:
            text = "Unknown Criteria"
    
    return text

def check_goal_name(screenshot=None):
    """Detect the current goal name using simple Tesseract OCR.

    Captures the region (372, 113, 912, 152) and returns the recognized
    goal name as a string. Mirrors the lightweight OCR approach used in
    check_criteria (PSM 7, single line) with a single fallback to the
    shared extract_text helper.
    """
    GOAL_REGION = (372, 113, 912, 152)

    # Capture enhanced image of the goal name region for better OCR
    goal_img = enhanced_screenshot(GOAL_REGION, screenshot)

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
    import pytesseract
    text = pytesseract.image_to_string(goal_img, config='--oem 3 --psm 7').strip()

    if not text:
        # Fallback once to the shared OCR helper
        fallback_text = extract_text(goal_img)
        if fallback_text.strip():
            log_debug(f"Using fallback goal OCR result: '{fallback_text}'")
            text = fallback_text.strip()

    if DEBUG_MODE:
        log_debug(f"Goal name OCR result: '{text}'")

    return text



def check_skill_points(screenshot=None):
    skill_img = enhanced_screenshot(SKILL_PTS_REGION, screenshot)
    
    # Apply sharpening for better OCR accuracy
    sharpener = ImageEnhance.Sharpness(skill_img)
    skill_img_sharp = sharpener.enhance(2.5)  # Increase sharpness by 2.5x
    
    # Save debug images for skill points OCR troubleshooting (only in debug mode)
    if DEBUG_MODE:
        try:
            skill_img.save("debug_skill_points_original.png")
            skill_img_sharp.save("debug_skill_points_sharpened.png")
            log_debug(f"Saved original skill points image to debug_skill_points_original.png")
            log_debug(f"Saved sharpened skill points image to debug_skill_points_sharpened.png")
        except Exception:
            pass
    log_debug(f"Skill points region: {SKILL_PTS_REGION}")
    
    # Use sharpened image for OCR
    skill_text = extract_number(skill_img_sharp)
    digits = ''.join(filter(str.isdigit, skill_text))
    
    log_debug(f"Skill points OCR raw result: '{skill_text}'")
    log_debug(f"Extracted digits: '{digits}'")
    
    result = int(digits) if digits.isdigit() else 0
    log_debug(f"Final skill points value: {result}")
    
    # Cache the skill points for reuse in skill auto-purchase
    if result > 0:
        from core.skill_auto_purchase import cache_skill_points
        cache_skill_points(result)
    
    return result

def check_skill_points_cap(screenshot=None):
    """Check skill points and handle cap logic (same as PC version)"""
    import json
    import tkinter as tk
    from tkinter import messagebox
    
    # Load config
    try:
        with open("config.json", "r", encoding="utf-8") as file:
            config = json.load(file)
    except Exception as e:
        log_error(f"Error loading config: {e}")
        return True
    
    skill_point_cap = config.get("skill_point_cap", 9999)
    current_skill_points = check_skill_points(screenshot)
    
    log_info(f"Current skill points: {current_skill_points}, Cap: {skill_point_cap}")
    
    if current_skill_points > skill_point_cap:
        log_warning(f"Skill points ({current_skill_points}) exceed cap ({skill_point_cap})")
        
        # Decide flow based on config
        skill_purchase_mode = config.get("skill_purchase", "manual").lower()
        if skill_purchase_mode == "auto":
            log_info(f"Auto skill purchase enabled - starting automation")
            try:
                # 1) Enter skill screen
                entered = click_image_button("assets/buttons/skills_btn.png", "skills button", max_attempts=5)
                if not entered:
                    log_error(f"Could not find/open skills screen")
                    return True
                time.sleep(1.0)

                # 2) Scan skills and prepare purchase plan
                scan_result = scan_all_skills_with_scroll()
                if 'error' in scan_result:
                    log_error(f"Skill scanning failed: {scan_result['error']}")
                    # Attempt to go back anyway
                    click_image_button("assets/buttons/back_btn.png", "back button", max_attempts=5)
                    time.sleep(1.0)
                    return True
                all_skills = scan_result.get('all_skills', [])
                if not all_skills:
                    log_warning(f"No skills detected on skill screen")
                    click_image_button("assets/buttons/back_btn.png", "back button", max_attempts=5)
                    time.sleep(1.0)
                    return True

                # Read current available skill points from the skill screen
                available_points = extract_skill_points()
                log_info(f"Detected available skill points: {available_points}")

                # Build purchase plan from config priorities
                skill_file = config.get("skill_file", "skills.json")
                log_info(f"Loading skills from: {skill_file}")
                cfg = load_skill_config(skill_file)
                purchase_plan = create_purchase_plan(all_skills, cfg, end_career=False)
                if not purchase_plan:
                    log_info(f"No skills from priority list are currently available")
                    click_image_button("assets/buttons/back_btn.png", "back button", max_attempts=5)
                    time.sleep(1.0)
                    return True

                # Filter by budget if we have points
                final_plan = purchase_plan
                if isinstance(available_points, int) and available_points > 0:
                    affordable_skills, total_cost, remaining_points = filter_affordable_skills(purchase_plan, available_points)
                    final_plan = affordable_skills if affordable_skills else []
                    log_info(f"Affordable skills: {len(final_plan)}; Total cost: {total_cost}; Remaining: {remaining_points}")

                if not final_plan:
                    log_info(f"Nothing affordable to purchase at the moment")
                    click_image_button("assets/buttons/back_btn.png", "back button", max_attempts=5)
                    time.sleep(1.0)
                    return True

                # Execute automated purchases
                exec_result = execute_skill_purchases(final_plan)
                if not exec_result.get('success'):
                    log_warning(f"Automated purchase completed with issues: {exec_result.get('error', 'unknown error')}")

                # 3) Return to lobby
                back = click_image_button("assets/buttons/back_btn.png", "back button", max_attempts=5)
                if not back:
                    log_warning(f"Could not find back button after purchases; ensure you return to lobby manually")
                time.sleep(1.0)
            except Exception as e:
                log_error(f"Auto skill purchase failed: {e}")
            
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
            
            log_info(f"Player acknowledged skill points cap warning")
            
        except Exception as e:
            log_error(f"Failed to show GUI popup: {e}")
            log_info(f"Skill points cap reached - automation continuing")
        
        return True
    
    return True

def check_current_stats(screenshot=None):
    """
    Check current character stats using OCR on the stat regions.
    
    Args:
        screenshot: Optional PIL Image. If None, takes a new screenshot.
    
    Returns:
        dict: Dictionary of current stats with keys: spd, sta, pwr, guts, wit
    """
    from utils.constants_phone import SPD_REGION, STA_REGION, PWR_REGION, GUTS_REGION, WIT_REGION
    from utils.screenshot import take_screenshot
    import pytesseract
    from PIL import Image, ImageEnhance
    
    # Use provided screenshot or take new one if not provided
    if screenshot is None:
        screenshot = take_screenshot()
    
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
            # Crop to stat region from provided screenshot
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
                import re
                numbers = re.findall(r'\d+', stat_text)
                if numbers:
                    stats[stat_name] = int(numbers[0])
                    log_debug(f"{stat_name.upper()} stat: {stats[stat_name]}")
                else:
                    stats[stat_name] = 0
                    log_debug(f"Failed to extract {stat_name.upper()} stat from text: '{stat_text}'")
            else:
                stats[stat_name] = 0
                log_debug(f"No text found for {stat_name.upper()} stat")
                
        except Exception as e:
            log_debug(f"Error reading {stat_name.upper()} stat: {e}")
            stats[stat_name] = 0
    
    log_debug(f"Current stats: {stats}")
    return stats



def check_energy_bar(screenshot=None, debug_visualization=False):
    """Compute energy percentage using saturation-based detection.

    - Crop to the energy region
    - Detect filled (high saturation) vs empty (low saturation) portions
    - Use horizontal line analysis at the midpoint
    - Calculate percentage based on filled width
    """
    try:
        import cv2
        import numpy as np
        from utils.screenshot import take_screenshot

        if screenshot is None:
            screenshot = take_screenshot()

        # Crop region (x, y, w, h) - energy bar location
        x, y, width, height = 330, 203, 602, 72
        cropped = screenshot.crop((x, y, x + width, y + height))

        img = np.array(cropped, dtype=np.uint8)
        if img.shape[2] == 4:
            img = img[:, :, :3]

        h, w = img.shape[:2]
        
        if DEBUG_MODE:
            log_debug(f"Energy bar image shape: {img.shape}")

        # Find the horizontal midline of the bar
        mid_y = h // 2

        # Strategy: Use HSV saturation to detect filled vs empty
        # Filled portion: has high saturation (colorful - blue, yellow, green gradient)
        # Empty portion: has low saturation (gray)
        
        # Convert to HSV
        hsv = cv2.cvtColor(img, cv2.COLOR_RGB2HSV)
        
        # Extract saturation channel
        saturation = hsv[:, :, 1]
        
        # First, try to detect the actual pill interior width dynamically (handles event-based size changes)
        dyn_left, dyn_right = None, None
        try:
            gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
            edges = cv2.Canny(gray, 60, 160)
            edges = cv2.dilate(edges, np.ones((3,3), np.uint8), iterations=1)
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            best = None
            best_score = -1
            for cnt in contours:
                x0, y0, ww, hh = cv2.boundingRect(cnt)
                area = ww * hh
                if ww < 200 or hh < 20:
                    continue
                aspect = float(ww) / float(hh + 1e-3)
                score = area * aspect
                if score > best_score:
                    best_score = score
                    best = (x0, y0, ww, hh)
            if best is not None:
                x0, y0, ww, hh = best
                # Inset a bit to get inside the stroke
                inset = max(4, int(min(ww, hh) * 0.05))
                dyn_left = max(0, x0 + inset)
                dyn_right = min(w - 1, x0 + ww - inset)
        except Exception as _e:
            pass
        
        # Tunables - hardcoded for stability (ignore config)
        left_margin_cfg = 10
        right_margin_off_cfg = 16
        sat_threshold = 36
        min_gray_run_px = 12
        min_gray_run_pct = 0.06
        close_kernel = 7

        # Choose margins: prefer dynamic if available, else fallback to config
        if dyn_left is not None and dyn_right is not None and dyn_right - dyn_left > 100:
            left_margin = dyn_left
            right_margin = dyn_right
            source = "dynamic"
        else:
            left_margin = max(0, min(left_margin_cfg, w - 1))
            right_margin = max(left_margin + 1, min(w - right_margin_off_cfg, w - 1))
            source = "config"

        if DEBUG_MODE:
            log_debug(f"Energy params: src={source}, left={left_margin}, right={right_margin}, sat_th={sat_threshold}, min_run_px={min_gray_run_px}, min_run_pct={min_gray_run_pct}, close_kernel={close_kernel}")
        # Build gray mask by saturation threshold then horizontally close small gaps
        gray_mask = (saturation <= sat_threshold).astype(np.uint8) * 255
        if close_kernel > 1:
            try:
                k = cv2.getStructuringElement(cv2.MORPH_RECT, (close_kernel, 1))
                gray_mask = cv2.morphologyEx(gray_mask, cv2.MORPH_CLOSE, k, iterations=1)
            except Exception:
                pass

        # Compute constants
        bar_content_width = right_margin - left_margin + 1
        min_gray_run = max(min_gray_run_px, int(bar_content_width * min_gray_run_pct))
        mid_y = h // 2

        # Sample multiple horizontal lines around midline and find continuous gray run from the right
        offsets = [-10, -6, -3, 0, 3, 6, 10]
        candidate_boundaries = []
        for dy in offsets:
            y_idx = int(mid_y + dy)
            if y_idx <= 6 or y_idx >= h - 7:
                continue
            line = gray_mask[y_idx, :]
            run = 0
            in_gray = False
            boundary_index = None
            for x_pos in range(right_margin, left_margin - 1, -1):
                if line[x_pos] > 0:
                    # in gray region contiguous from the right edge
                    run += 1
                    in_gray = True
                else:
                    # hit non-gray; if we already have a long gray run, boundary is right after this non-gray
                    if in_gray and run >= min_gray_run:
                        boundary_index = x_pos + 1
                        break
                    # reset and continue searching
                    run = 0
                    in_gray = False
            # if entire span is gray, put boundary at left margin (0%)
            if boundary_index is None and in_gray and run >= min_gray_run:
                boundary_index = left_margin
            if boundary_index is not None:
                candidate_boundaries.append(boundary_index)

        if not candidate_boundaries:
            # Fallback: estimate using gray density to avoid reporting 100% incorrectly
            roi = gray_mask[max(0, mid_y-3):min(h, mid_y+4), left_margin:right_margin+1]
            gray_ratio = float(np.count_nonzero(roi)) / float(roi.size)
            if gray_ratio < 0.05:
                percentage = 100.0
            elif gray_ratio > 0.95:
                percentage = 0.0
            else:
                # Fallback to rightmost filled pixel (saturation-based)
                midline_sat = saturation[mid_y, :]
                filled_positions = np.where(midline_sat > sat_threshold)[0]
                if len(filled_positions) == 0:
                    percentage = 0.0
                else:
                    rightmost_filled = min(filled_positions[-1], right_margin)
                    filled_content_width = max(0, rightmost_filled - left_margin + 1)
                    percentage = float(filled_content_width / bar_content_width * 100.0)
            if DEBUG_MODE:
                log_debug(f"Energy bar: no gray run; gray_ratio={gray_ratio:.2f}; percent={percentage:.1f}%")
        else:
            boundary_index = int(np.median(candidate_boundaries))
            boundary_index = max(left_margin, min(boundary_index, right_margin))
            filled_content_width = max(0, boundary_index - left_margin)
            percentage = float(filled_content_width / bar_content_width * 100.0)
            percentage = min(100.0, max(0.0, percentage))
            if DEBUG_MODE:
                log_debug(f"Energy bar: boundaries={candidate_boundaries}, median={boundary_index}, left={left_margin}, right={right_margin}, min_run={min_gray_run}, percent={percentage:.1f}%")

        if DEBUG_MODE or debug_visualization:
            try:
                # Ensure debug directory exists
                debug_dir = os.path.join(os.getcwd(), "Energy test")
                os.makedirs(debug_dir, exist_ok=True)
                ts = time.strftime("%Y%m%d_%H%M%S")
                cropped_path = os.path.join(debug_dir, f"energy_{ts}_cropped.png")
                viz_path = os.path.join(debug_dir, f"energy_{ts}_viz.png")

                # Save original cropped image
                cv2.imwrite(cropped_path, cv2.cvtColor(img, cv2.COLOR_RGB2BGR))
                
                # Create visualization with midline and analysis
                debug_img = cv2.cvtColor(img.copy(), cv2.COLOR_RGB2BGR)
                
                # Draw midline and margins
                cv2.line(debug_img, (0, mid_y), (w - 1, mid_y), (0, 255, 0), 2)
                try:
                    # If variables exist draw margins/boundary
                    cv2.line(debug_img, (left_margin, 0), (left_margin, h - 1), (255, 0, 0), 1)
                    cv2.line(debug_img, (right_margin, 0), (right_margin, h - 1), (255, 0, 0), 1)
                    if 'boundary_index' in locals() and boundary_index is not None:
                        cv2.line(debug_img, (int(boundary_index), 0), (int(boundary_index), h - 1), (0, 255, 255), 2)
                except Exception:
                    pass
                
                # Draw saturation visualization overlay
                sat_vis = cv2.cvtColor(saturation, cv2.COLOR_GRAY2BGR)
                debug_img = cv2.addWeighted(debug_img, 0.7, sat_vis, 0.3, 0)
                
                # Add text
                cv2.putText(debug_img, f"Energy: {percentage:.1f}%", (10, 30), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
                cv2.putText(debug_img, f"Midline: y={mid_y}", (10, 60), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
                
                cv2.imwrite(viz_path, debug_img)
                log_debug(f"Saved energy debug: {os.path.basename(cropped_path)}, {os.path.basename(viz_path)}")
            except Exception as viz_e:
                log_debug(f"Energy debug visualization failed: {viz_e}")

        return percentage

    except Exception as e:
        log_debug(f"Energy bar check failed: {e}")
        if DEBUG_MODE:
            log_debug(f"Error details: {str(e)}")
        return 0.0
