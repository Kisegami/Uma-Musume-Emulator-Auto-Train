import time
import json
import random
import numpy as np
import pytesseract
from PIL import ImageStat

from utils.recognizer import locate_on_screen, match_template, locate_all_on_screen, max_match_confidence
from utils.input import tap, triple_click, long_press, tap_on_image, swipe
from utils.screenshot import take_screenshot
from utils.template_matching import wait_for_image, deduplicated_matches
from utils.log import debug_print
from core.state import check_skill_points_cap, check_current_year
from core.ocr import extract_text

# Load config for RETRY_RACE
try:
    with open("config.json", "r", encoding="utf-8") as config_file:
        config = json.load(config_file)
        RETRY_RACE = config.get("retry_race", True)
except Exception:
    RETRY_RACE = True

# Region offsets from fan center (same as test code)
GRADE_OFFSET = (-37, -105, 90, 45)  # x, y, width, height
OCR_OFFSET = (47, -117, 345, 63)    # x, y, width, height

def is_racing_available(year):
    """Check if racing is available based on the current year/month"""
    # No races in Pre-Debut
    if is_pre_debut_year(year):
        return False
    # No races in Finale Season (final training period before URA)
    if "Finale Season" in year:
        return False
    year_parts = year.split(" ")
    # No races in July and August (summer break)
    if len(year_parts) > 3 and year_parts[3] in ["Jul", "Aug"]:
        return False
    return True

def is_pre_debut_year(year):
    return ("Pre-Debut" in year or "PreDebut" in year or 
            "PreeDebut" in year or "Pre" in year)

def get_grade_priority(grade):
    """Get priority score for a grade (lower number = higher priority)"""
    grade_priority = {
        "G1": 1,
        "G2": 2,
        "G3": 3,
        "OP": 4,
        "PRE-OP": 5
    }
    return grade_priority.get(grade.upper(), 999)  # Unknown grades get lowest priority

def find_target_race_in_screenshot(screenshot, race_description):
    """Find target race in a given screenshot and return fan center coordinates"""
    matches = locate_all_on_screen("assets/races/fan.png", confidence=0.8, region=(321, 1018, 114, 510))
    
    debug_print(f"[DEBUG] Found {len(matches) if matches else 0} fan matches")
    
    if not matches:
        return None, None
    
    unique_fans = deduplicated_matches(matches, threshold=30)
    debug_print(f"[DEBUG] After deduplication: {len(unique_fans)} unique fans")
    
    for i, (x, y, w, h) in enumerate(unique_fans):
        center_x, center_y = x + w//2, y + h//2
        
        # OCR region
        ox, oy, ow, oh = center_x + OCR_OFFSET[0], center_y + OCR_OFFSET[1], OCR_OFFSET[2], OCR_OFFSET[3]
        text = extract_text(screenshot.crop((ox, oy, ox + ow, oy + oh)))
        
        debug_print(f"[DEBUG] Fan {i+1} at ({center_x}, {center_y}) - OCR text: '{text}'")
        
        # Check if the race description appears in the OCR text
        if race_description and text and race_description.lower() in text.lower():
            debug_print(f"[DEBUG] Found race with description '{race_description}' at fan center ({center_x}, {center_y})")
            return center_x, center_y
    
    return None, None

def execute_race_after_selection():
    """Execute race after race selection - handles race button tapping and race execution"""
    debug_print("[DEBUG] Executing race after selection...")
    
    # Wait for race button to appear after selecting race
    debug_print("[DEBUG] Waiting for race button to appear after race selection...")
    race_btn = wait_for_image("assets/buttons/race_btn.png", timeout=10)
    if not race_btn:
        debug_print("[DEBUG] Race button not found after 10 seconds")
        return False
    
    # Click race button twice to start the race
    for j in range(2):
        if tap_on_image("assets/buttons/race_btn.png", confidence=0.8, min_search=1):
            debug_print(f"[DEBUG] Race button clicked {j+1}/2")
            time.sleep(0.5)
        else:
            debug_print(f"[DEBUG] Failed to click race button {j+1}/2")
    
    # Race starts automatically after clicking race button twice
    # Use the existing race_prep function to handle strategy and race execution
    debug_print("[DEBUG] Race started automatically, calling race_prep...")
    race_prep()
    time.sleep(1)
    # Handle post-race actions
    after_race()
    return True

def search_race_with_swiping(race_description, year, max_swipes=3):
    """Helper function to search for a race with swiping - eliminates duplicate code"""
    debug_print(f"[DEBUG] Looking for: {race_description}")
    
    # Take screenshot and search for the race
    screenshot = take_screenshot()
    target_x, target_y = find_target_race_in_screenshot(screenshot, race_description)
    
    if target_x and target_y:
        debug_print(f"[DEBUG] Race found! Tapping at ({target_x}, {target_y})")
        tap(target_x, target_y)
        time.sleep(0.5)
        return True
    
    # If not found initially, perform swipes
    debug_print("[DEBUG] Race not found on initial screen, performing swipes...")
    
    for swipe_num in range(1, max_swipes + 1):
        debug_print(f"[DEBUG] Swipe {swipe_num}:")
        swipe(381, 1415, 381, 1223, duration_ms=240)
        time.sleep(1)  # Wait for swipe animation
        
        # Take new screenshot after swipe
        screenshot = take_screenshot()
        
        # Search for the race after each swipe
        target_x, target_y = find_target_race_in_screenshot(screenshot, race_description)
        
        if target_x and target_y:
            debug_print(f"[DEBUG] Race found after swipe {swipe_num}! Tapping at ({target_x}, {target_y})")
            tap(target_x, target_y)
            time.sleep(0.5)
            return True
    
    debug_print("[DEBUG] Race not found after all swipes")
    return False

def race_day():
    """Handle race day"""
    # Check skill points cap before race day (if enabled)
    import json
    
    # Load config to check if skill point check is enabled
    with open("config.json", "r", encoding="utf-8") as file:
        config = json.load(file)
    
    enable_skill_check = config.get("enable_skill_point_check", True)
    
    if enable_skill_check:
        print("[INFO] Race Day - Checking skill points cap...")
        check_skill_points_cap()
    
    debug_print("[DEBUG] Clicking race day button...")
    if tap_on_image("assets/buttons/race_day_btn.png", min_search=10):
        debug_print("[DEBUG] Race day button clicked, clicking OK button...")
        time.sleep(1.3)
        tap_on_image("assets/buttons/ok_btn.png", confidence=0.5, min_search=2)
        
        # Wait for race selection screen to appear by waiting for race button
        debug_print("[DEBUG] Waiting for race selection screen to appear...")
        race_btn_found = wait_for_image("assets/buttons/race_btn.png", timeout=10)
        if not race_btn_found:
            debug_print("[DEBUG] Race button not found after 10 seconds, failed to enter race selection screen")
            return False
        
        debug_print("[DEBUG] Race selection screen appeared, proceeding with race selection...")
        
        # Try to find and click race button with better error handling
        race_clicked = False
        for attempt in range(3):  # Try up to 3 times
            if tap_on_image("assets/buttons/race_btn.png", confidence=0.7, min_search=1):
                debug_print(f"[DEBUG] Race button clicked successfully, attempt {attempt + 1}")
                time.sleep(0.5)  # Wait between clicks
                
                # Click race button twice like in race_select
                for j in range(2):
                    if tap_on_image("assets/buttons/race_btn.png", confidence=0.7, min_search=1):
                        debug_print(f"[DEBUG] Race button clicked {j+1} time(s)")
                        time.sleep(0.5)
                    else:
                        debug_print(f"[DEBUG] Failed to click race button {j+1} time(s)")
                
                race_clicked = True
                time.sleep(0.8)  # Wait for UI to respond
                break
            else:
                debug_print(f"[DEBUG] Race button not found, attempt {attempt + 1}")
                time.sleep(0.5)
        
        if not race_clicked:
            debug_print("[DEBUG] Failed to click race button after all attempts")
            return False
            
        debug_print("[DEBUG] Starting race preparation...")
        race_prep()
        time.sleep(1)
        
        # Loop to check for either next button or clock icon with unlimited retries
        debug_print("[DEBUG] Checking for next button or clock icon with unlimited retries...")
        retry_count = 0
        max_retries_per_race = 50  # Safety limit to prevent infinite loops
        
        while True:
            retry_count += 1
            debug_print(f"[DEBUG] Check attempt {retry_count}")
            
            # Check for clock icon (race failure)
            clock = locate_on_screen("assets/icons/clock.png", confidence=0.8)
            if clock:
                debug_print(f"[DEBUG] Clock icon found - race failed (attempt {retry_count}), handling retry...")
                if retry_count > max_retries_per_race:
                    debug_print(f"[DEBUG] Max retries per race ({max_retries_per_race}) reached, proceeding anyway...")
                    after_race()
                    return True
                
                # Handle race retry
                handle_race_retry_if_failed()
                # Continue the loop to check again after retry
                continue
            
            # Check for next button
            next_btn = locate_on_screen("assets/buttons/next_btn.png", confidence=0.8)
            if next_btn:
                debug_print(f"[DEBUG] Next button found after {retry_count} attempts - proceeding with after_race...")
                after_race()
                return True
            
            # If neither found, try tapping middle of screen and wait
            debug_print(f"[DEBUG] Neither clock nor next button found (attempt {retry_count}), tapping middle of screen...")
            tap(540, 960)  # Click middle of screen (1080x1920 resolution)
            time.sleep(1)
            
            # Safety check to prevent infinite loops
            if retry_count > max_retries_per_race:
                debug_print(f"[DEBUG] Safety limit reached ({max_retries_per_race} attempts), proceeding with after_race...")
                after_race()
                return True
    return False

def check_strategy_before_race(region=(660, 974, 378, 120)) -> bool:
    """Check and ensure strategy matches config before race."""
    debug_print("[DEBUG] Checking strategy before race...")
    
    try:
        screenshot = take_screenshot()
        
        templates = {
            "front": "assets/icons/front.png",
            "late": "assets/icons/late.png", 
            "pace": "assets/icons/pace.png",
            "end": "assets/icons/end.png",
        }
        
        # Find brightest strategy using existing project functions
        best_match = None
        best_brightness = 0
        
        for name, path in templates.items():
            try:
                # Use existing match_template function
                matches = match_template(screenshot, path, confidence=0.5, region=region)
                if matches:
                    # Get confidence for best match
                    confidence = max_match_confidence(screenshot, path, region)
                    if confidence:
                        # Check brightness of the matched region
                        x, y, w, h = matches[0]
                        roi = screenshot.convert("L").crop((x, y, x + w, y + h))
                        bright = float(ImageStat.Stat(roi).mean[0])
                        
                        if bright >= 160 and bright > best_brightness:
                            best_match = (name, matches[0], confidence, bright)
                            best_brightness = bright
            except Exception:
                continue
        
        if not best_match:
            debug_print("[DEBUG] No strategy found with brightness >= 160")
            return False
        
        strategy_name, bbox, conf, bright = best_match
        current_strategy = strategy_name.upper()
        
        # Load expected strategy from config
        try:
            with open("config.json", "r", encoding="utf-8") as f:
                config = json.load(f)
            expected_strategy = config.get("strategy", "").upper()
        except Exception:
            debug_print("[DEBUG] Cannot read config.json")
            return False
        
        matches = current_strategy == expected_strategy
        debug_print(f"[DEBUG] Current: {current_strategy}, Expected: {expected_strategy}, Match: {matches}")
        
        if matches:
            debug_print("[DEBUG] Strategy matches config, proceeding with race")
            return True
        
        # Strategy doesn't match, try to change it
        debug_print(f"[DEBUG] Strategy mismatch, changing to {expected_strategy}")
        
        if change_strategy_before_race(expected_strategy):
            # Recheck after change
            new_strategy, new_matches = check_strategy_before_race(region)
            if new_matches:
                debug_print("[DEBUG] Strategy successfully changed")
                return True
            else:
                debug_print("[DEBUG] Strategy change failed")
                return False
        else:
            debug_print("[DEBUG] Failed to change strategy")
            return False
            
    except Exception as e:
        debug_print(f"[DEBUG] Error checking strategy: {e}")
        return False

def change_strategy_before_race(expected_strategy: str) -> bool:
    """Change strategy to the expected one before race."""
    debug_print(f"[DEBUG] Changing strategy to: {expected_strategy}")
    
    # Strategy coordinates mapping
    strategy_coords = {
        "FRONT": (882, 1159),
        "PACE": (645, 1159),
        "LATE": (414, 1159),
        "END": (186, 1162),
    }
    
    if expected_strategy not in strategy_coords:
        debug_print(f"[DEBUG] Unknown strategy: {expected_strategy}")
        return False
    
    try:
        # Step 1: Find and tap strategy_change.png
        debug_print("[DEBUG] Looking for strategy change button...")
        change_btn = wait_for_image("assets/buttons/strategy_change.png", timeout=10, confidence=0.8)
        if not change_btn:
            debug_print("[DEBUG] Strategy change button not found")
            return False
        
        debug_print(f"[DEBUG] Found strategy change button at {change_btn}")
        tap(change_btn[0], change_btn[1])
        debug_print("[DEBUG] Tapped strategy change button")
        
        # Step 2: Wait for confirm.png to appear
        debug_print("[DEBUG] Waiting for confirm button to appear...")
        confirm_btn = wait_for_image("assets/buttons/confirm.png", timeout=10, confidence=0.8)
        if not confirm_btn:
            debug_print("[DEBUG] Confirm button not found after strategy change")
            return False
        
        debug_print(f"[DEBUG] Confirm button appeared at {confirm_btn}")
        
        # Step 3: Tap on the specified coordinate for the right strategy
        target_x, target_y = strategy_coords[expected_strategy]
        debug_print(f"[DEBUG] Tapping strategy position: ({target_x}, {target_y}) for {expected_strategy}")
        tap(target_x, target_y)
        debug_print(f"[DEBUG] Tapped strategy position for {expected_strategy}")
        
        # Step 4: Tap confirm.png from found location
        debug_print("[DEBUG] Confirming strategy change...")
        tap(confirm_btn[0], confirm_btn[1])
        debug_print("[DEBUG] Tapped confirm button")
        
        # Wait a moment for the change to take effect
        time.sleep(2)
        
        debug_print(f"[DEBUG] Strategy change completed for {expected_strategy}")
        return True
        
    except Exception as e:
        debug_print(f"[DEBUG] Error during strategy change: {e}")
        return False

def race_prep():
    """Prepare for race"""
    debug_print("[DEBUG] Preparing for race...")
    
    view_result_btn = wait_for_image("assets/buttons/view_results.png", timeout=20)
        
    # Check and ensure strategy matches config before race
    if not check_strategy_before_race():
        debug_print("[DEBUG] Failed to ensure correct strategy, proceeding anyway...")
    if view_result_btn:
        debug_print(f"[DEBUG] Found view results button at {view_result_btn}")
        tap(view_result_btn[0], view_result_btn[1])
        time.sleep(0.5)
        for i in range(1):
            debug_print(f"[DEBUG] Clicking view results {i + 1}/3")
            triple_click(view_result_btn[0], view_result_btn[1], interval=0.01)
            time.sleep(0.5)
        time.sleep(1.0)
    else:
        debug_print("[DEBUG] View results button not found, proceeding without strategy check")

def handle_race_retry_if_failed():
    """Detect race failure on race day and retry based on config.

    Recognizes failure by detecting `assets/icons/clock.png` on screen.
    If `retry_race` is true in config, taps `assets/buttons/try_again.png`, waits 5s,
    and calls `race_prep()` again. Returns True if a retry was performed, False otherwise.
    """
    try:
        # Check for failure indicator (clock icon)
        clock = locate_on_screen("assets/icons/clock.png", confidence=0.8)
        if not clock:
            return False

        print("[INFO] Race failed detected (clock icon).")

        if not RETRY_RACE:
            print("[INFO] retry_race is disabled. Stopping automation.")
            raise SystemExit(0)

        # Try to click Try Again button
        try_again = locate_on_screen("assets/buttons/try_again.png", confidence=0.8)
        if try_again:
            time.sleep(0.5)
            print("[INFO] Clicking Try Again button.")
            tap(try_again[0], try_again[1])
        else:
            print("[INFO] Try Again button not found. Attempting helper click...")
            # Fallback: attempt generic click using click helper
            tap_on_image("assets/buttons/try_again.png", confidence=0.8, min_search=10)

        # Wait before re-prepping the race
        print("[INFO] Waiting 5 seconds before retrying the race...")
        time.sleep(5)
        print("[INFO] Re-preparing race...")
        race_prep()
        return True
    except SystemExit:
        raise
    except Exception as e:
        print(f"[ERROR] handle_race_retry_if_failed error: {e}")
        return False

def after_race():
    """Handle post-race actions"""
    debug_print("[DEBUG] Handling post-race actions...")
    
    # Try to click first next button with fallback mechanism
    if not tap_on_image("assets/buttons/next_btn.png", confidence=0.7, min_search=10):
        debug_print("[DEBUG] First next button not found after 10 attempts, clicking middle of screen as fallback...")
        tap(540, 960)  # Click middle of screen (1080x1920 resolution)
        time.sleep(1)
        debug_print("[DEBUG] Retrying next button search after screen tap...")
        tap_on_image("assets/buttons/next_btn.png", confidence=0.7, min_search=10)
    
    time.sleep(4)
    
    # Try to click second next button with fallback mechanism
    if not tap_on_image("assets/buttons/next2_btn.png", confidence=0.7, min_search=10):
        debug_print("[DEBUG] Second next button not found after 10 attempts, clicking middle of screen as fallback...")
        tap(540, 960)  # Click middle of screen (1080x1920 resolution)
        time.sleep(1)
        debug_print("[DEBUG] Retrying next2 button search after screen tap...")
        tap_on_image("assets/buttons/next2_btn.png", confidence=0.7, min_search=10)
    
    debug_print("[DEBUG] Post-race actions complete")

def enter_race_selection_screen():
    """Helper function to enter race selection screen - eliminates duplicate code"""
    debug_print("[DEBUG] Entering race selection screen...")
    
    # Tap races button
    if not tap_on_image("assets/buttons/races_btn.png", min_search=10):
        debug_print("[DEBUG] Failed to find races button")
        return False
    
    time.sleep(1.2)
    
    # Try to tap OK button if it appears (optional)
    ok_clicked = tap_on_image("assets/buttons/ok_btn.png", confidence=0.5, min_search=1)
    if ok_clicked:
        debug_print("[DEBUG] OK button found and clicked")
        time.sleep(1.5)  # Wait for race list to load
    else:
        debug_print("[DEBUG] OK button not found, proceeding without it")
        time.sleep(1.0)  # Shorter wait since no OK button
    
    return True

def check_and_select_maiden_race():
    """Helper function to check for and select maiden races - eliminates duplicate code"""
    debug_print("[DEBUG] Checking for maiden races...")
    maiden_races = locate_all_on_screen("assets/races/maiden.png", confidence=0.8)
    
    if maiden_races:
        debug_print(f"[DEBUG] Found {len(maiden_races)} maiden race(s)!")
        
        # Sort by Y coordinate (highest Y = top of screen)
        maiden_races.sort(key=lambda x: x[1])  # Sort by Y coordinate
        
        # Select the topmost maiden race (highest Y coordinate)
        top_maiden = maiden_races[0]
        maiden_x, maiden_y, maiden_w, maiden_h = top_maiden
        maiden_center_x = maiden_x + maiden_w // 2
        maiden_center_y = maiden_y + maiden_h // 2
        
        debug_print(f"[DEBUG] Selecting top maiden race at ({maiden_center_x}, {maiden_center_y})")
        debug_print("[DEBUG] Tapping on maiden race...")
        
        tap(maiden_center_x, maiden_center_y)
        time.sleep(0.5)
        
        debug_print("[DEBUG] Maiden race selected successfully!")
        return True
    
    debug_print("[DEBUG] No maiden races found")
    return False

def find_and_do_race():
    """Find and execute race using intelligent race selection - replaces old do_race()"""
    debug_print("[DEBUG] Starting intelligent race selection...")
    
    try:
        # 1. Setup common environment
        year = check_current_year()
        if not year:
            debug_print("[DEBUG] Could not detect current year")
            return False
        
        # 2. Load configuration and race data
        try:
            with open("config.json", "r", encoding="utf-8") as f:
                config = json.load(f)
        except Exception as e:
            debug_print(f"[DEBUG] Error loading config: {e}")
            return False
        
        try:
            with open("assets/races/clean_race_data.json", "r", encoding="utf-8") as f:
                race_data = json.load(f)
        except Exception as e:
            debug_print(f"[DEBUG] Error loading race data: {e}")
            return False
        
        if not race_data:
            debug_print("[DEBUG] Failed to load race data")
            return False
        
        # 3. Choose best race based on database and config criteria
        # Check if goal contains G1 and override allowed grades if so
        from core.state import check_goal_name
        goal_name = check_goal_name()
        
        # Override allowed grades if goal contains G1
        if goal_name and "G1" in goal_name:
            debug_print(f"[DEBUG] Goal contains G1: '{goal_name}' - Overriding to only allow G1 races")
            allowed_grades = ["G1"]
        else:
            allowed_grades = config.get("allowed_grades", ["G1", "G2", "G3", "OP", "PRE-OP"])
        
        allowed_tracks = config.get("allowed_tracks", ["Turf", "Dirt"])
        allowed_distances = config.get("allowed_distances", ["Sprint", "Mile", "Medium", "Long"])
        
        # Find best race using the existing logic
        best_race = None
        best_grade = None
        best_priority = 999
        best_fans = 0
        
        if year in race_data:
            for race_name, race_info in race_data[year].items():
                race_grade = race_info.get("grade", "UNKNOWN")
                race_surface = race_info.get("surface", "UNKNOWN")
                race_category = race_info.get("distance_type", "UNKNOWN")
                
                # Check if this grade is allowed
                if race_grade not in allowed_grades:
                    continue
                
                # Check if this track/surface is allowed
                if allowed_tracks and race_surface not in allowed_tracks:
                    continue
                
                # Check if this distance/category is allowed
                if allowed_distances and race_category not in allowed_distances:
                    continue
                
                # Get priority score for this grade
                priority = get_grade_priority(race_grade)
                fans = race_info.get("fans", 0)
                
                # Update best race if this one is better
                if priority < best_priority or (priority == best_priority and fans > best_fans):
                    best_race = race_name
                    best_grade = race_grade
                    best_priority = priority
                    best_fans = fans
        
        if not best_race:
            debug_print("[DEBUG] No suitable race found")
            return False
        
        debug_print(f"[DEBUG] Best race selected: {best_race} ({best_grade})")
        
        # 4. Enter race selection screen
        if not enter_race_selection_screen():
            return False
        
        # 5. Check for maiden races first (priority over database selection)
        debug_print("[DEBUG] Checking for maiden races...")
        if check_and_select_maiden_race():
            debug_print("[DEBUG] Maiden race selected successfully!")
            # Execute the race after selection
            return execute_race_after_selection()
        
        debug_print("[DEBUG] No maiden races found, proceeding with database selection...")
        
        # 6. Find and choose the selected race using OCR
        debug_print("[DEBUG] Searching for selected race in Race Select Screen...")
        debug_print(f"[DEBUG] Looking for: {best_race}")
        
        # Get race description for OCR matching
        race_info = race_data[year][best_race]
        race_description = race_info.get("description", "")
        debug_print(f"[DEBUG] Race description: {race_description}")
        
        # Search for race with swiping using the same logic as test file
        if search_race_with_swiping(race_description, year):
            debug_print("[DEBUG] Race selection completed successfully!")
            # Execute the race after selection
            return execute_race_after_selection()
        
        return False
        
    except Exception as e:
        debug_print(f"[DEBUG] Error in find_and_do_race: {e}")
        return False

def do_custom_race():
    """Handle custom races from custom_races.json - bypasses all criteria checks"""
    debug_print("[DEBUG] Checking for custom race...")
    
    try:
        # 1. Get current year
        year = check_current_year()
        if not year:
            return False
        
        # 2. Load custom races data
        try:
            with open("custom_races.json", "r", encoding="utf-8") as f:
                custom_races = json.load(f)
        except Exception as e:
            debug_print(f"[DEBUG] Failed to load custom_races.json: {e}")
            return False
        
        # 3. Check if there's a custom race for the current year
        if year not in custom_races:
            return False
        
        custom_race = custom_races[year]
        if not custom_race or custom_race.strip() == "":
            return False
        
        debug_print(f"[DEBUG] Custom race found: {custom_race}")
        
        # 4. Enter race selection screen
        if not enter_race_selection_screen():
            debug_print("[DEBUG] Failed to enter race selection screen")
            return False
        
        # 5. Check for maiden races first (priority over custom race)
        debug_print("[DEBUG] Checking for maiden races...")
        if check_and_select_maiden_race():
            debug_print("[DEBUG] Maiden race selected successfully!")
            # Execute the race after selection
            return execute_race_after_selection()
        
        debug_print("[DEBUG] No maiden races found, proceeding with custom race...")
        
        # 6. Search for the custom race using OCR
        debug_print("[DEBUG] Searching for custom race in Race Select Screen...")
        
        # Load race data to get the description for OCR matching
        try:
            with open("assets/races/clean_race_data.json", "r", encoding="utf-8") as f:
                race_data = json.load(f)
        except Exception as e:
            debug_print(f"[DEBUG] Error loading race data: {e}")
            race_data = {}
        
        if year in race_data and custom_race in race_data[year]:
            race_info = race_data[year][custom_race]
            race_description = race_info.get("description", "")
            debug_print(f"[DEBUG] Race description: {race_description}")
        else:
            debug_print(f"[DEBUG] Warning: Race '{custom_race}' not found in race database for {year}")
            debug_print("[DEBUG] Will search by race name directly")
            race_description = custom_race
        
        # Search for race with swiping
        if search_race_with_swiping(race_description, year):
            debug_print("[DEBUG] Custom race selection completed successfully!")
            # Execute the race after selection
            return execute_race_after_selection()
        
        return False
        
    except Exception as e:
        debug_print(f"[DEBUG] Error in do_custom_race: {e}")
        return False
