import time
from PIL import ImageStat
from core.templates_adb import BACK_BUTTON_TEMPLATE, CLOCK_TEMPLATE, CONFIRM_BUTTON_TEMPLATE, G1_RACE_TEMPLATE, MATCH_TRACK_TEMPLATE, NEXT_2_BUTTON_TEMPLATE, NEXT_BUTTON_TEMPLATE, OK_BUTTON_TEMPLATE, RACE_BUTTON_TEMPLATE, RACE_DAY_BUTTON_TEMPLATE, RACES_BUTTON_TEMPLATE, STRATEGY_BUTTON_TEMPLATE, TRY_AGAIN_BUTTON_TEMPLATE, VIEW_RESULTS_BUTTON_TEMPLATE
import cv2

from core.config import Config
from core.event_handling import click, debug_print
from core.state_adb import check_skill_points_cap, check_skills_are_available, is_pre_debut_year
from utils.adb_recognizer import locate_on_screen, match_template, max_match_confidence, wait_for_image
from utils.adb_input import tap, triple_click
from utils.adb_screenshot import take_screenshot
from utils.constants_phone import RACE_CARD_REGION

# Load config and check debug mode
config = Config.load()
DEBUG_MODE = Config.get("debug_mode", False)
RETRY_RACE = Config.get("retry_race", True)

def do_race(year, prioritize_g1=False):
    """Perform race action"""
    debug_print(f"[DEBUG] Performing race action (G1 priority: {prioritize_g1})...")
    click(RACES_BUTTON_TEMPLATE, minSearch=10)
    time.sleep(1.2)
    click(OK_BUTTON_TEMPLATE, confidence=0.5, minSearch=1)

    found = race_select(year, prioritize_g1=prioritize_g1)
    if found:
        debug_print("[DEBUG] Race found and selected, proceeding to race preparation")
        return True
    else:
        debug_print("[DEBUG] No race found, going back")
        click(BACK_BUTTON_TEMPLATE, minSearch=0.7)
        return False

def race_day(screenshot, bought_skills):
    """Handle race day"""
    # Check skill points cap before race day (if enabled)
    enable_skill_check = config.get("enable_skill_point_check", True)
    
    if enable_skill_check and check_skills_are_available(bought_skills):
        print("[INFO] Race Day - Checking skill points cap...")
        check_skill_points_cap(screenshot, bought_skills)
    
    debug_print("[DEBUG] Clicking race day button...")
    if click(RACE_DAY_BUTTON_TEMPLATE, minSearch=10):
        debug_print("[DEBUG] Race day button clicked, clicking OK button...")
        time.sleep(1.3)
        click(OK_BUTTON_TEMPLATE, confidence=0.5, minSearch=2)
        time.sleep(1.0)  # Increased wait time
        
        # Try to find and click race button with better error handling
        race_clicked = False
        for attempt in range(3):  # Try up to 3 times
            if click(RACE_BUTTON_TEMPLATE, confidence=0.7, minSearch=1):
                debug_print(f"[DEBUG] Race button clicked successfully, attempt {attempt + 1}")
                time.sleep(0.5)  # Wait between clicks
                
                # Click race button twice like in race_select
                for j in range(2):
                    if click(RACE_BUTTON_TEMPLATE, confidence=0.7, minSearch=1):
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
            debug_print("[ERROR] Failed to click race button after multiple attempts")
            return False
            
        debug_print("[DEBUG] Starting race preparation...")
        return True
    return False

def race_select(year, prioritize_g1=False):
    """Select race"""
    debug_print(f"[DEBUG] Selecting race (G1 priority: {prioritize_g1})...")

    def find_and_select_race():
        """Helper function to find and select a race (G1 or normal)"""
        # Wait for race list to load before detection
        debug_print("[DEBUG] Waiting for race list to load...")
        time.sleep(1.5)
        
        # Check initial screen first
        if prioritize_g1:
            debug_print("[DEBUG] Looking for G1 race.")
            screenshot = take_screenshot()
            race_cards = match_template(screenshot, G1_RACE_TEMPLATE, confidence=0.9)
            debug_print(f"[DEBUG] Initial G1 detection result: {race_cards}")
            
            if race_cards:
                debug_print(f"[DEBUG] Found {len(race_cards)} G1 race card(s), searching for match_track within regions...")
                for x, y, w, h in race_cards:
                    # Search for match_track.png within the race card region
                    region = (x, y, RACE_CARD_REGION[2], RACE_CARD_REGION[3])
                    debug_print(f"[DEBUG] Searching region: {region}")
                    match_aptitude = locate_match_track_with_brightness(confidence=0.6, region=region, brightness_threshold=180.0)
                    if match_aptitude:
                        debug_print(f"[DEBUG] ✅ Match track found at {match_aptitude} in region {region}")
                    else:
                        debug_print(f"[DEBUG] ❌ No match track found in region {region}")
                    if match_aptitude:
                        debug_print(f"[DEBUG] G1 race found at {match_aptitude}")
                        tap(match_aptitude[0], match_aptitude[1])
                        time.sleep(0.2)
                        
                        # Click race button twice like PC version
                        for j in range(2):
                            race_button_screenshot = take_screenshot()
                            race_btn = locate_on_screen(race_button_screenshot, RACE_BUTTON_TEMPLATE, confidence=0.6)
                            if race_btn:
                                debug_print(f"[DEBUG] Found race button at {race_btn}")
                                tap(race_btn[0], race_btn[1])
                                time.sleep(0.5)
                            else:
                                debug_print("[DEBUG] Race button not found")
                        return True
            else:
                debug_print("[DEBUG] No G1 race cards found on initial screen, will try swiping...")
        else:
            debug_print("[DEBUG] Looking for race.")
            screenshot = take_screenshot()
            match_aptitude = locate_match_track_with_brightness(confidence=0.6, brightness_threshold=180.0)
            if match_aptitude:
                debug_print(f"[DEBUG] Race found at {match_aptitude}")
                tap(match_aptitude[0], match_aptitude[1])
                time.sleep(0.2)
                
                # Click race button twice like PC version
                for j in range(2):
                    race_button_screenshot = take_screenshot()
                    race_btn = locate_on_screen(race_button_screenshot, RACE_BUTTON_TEMPLATE, confidence=0.8)
                    if race_btn:
                        debug_print(f"[DEBUG] Found race button at {race_btn}")
                        tap(race_btn[0], race_btn[1])
                        time.sleep(0.5)
                    else:
                        debug_print("[DEBUG] Race button not found")
                return True

        if prioritize_g1 and not is_g1_racing_available(year):
            return False
        
        # If not found on initial screen, try scrolling up to 4 times
        for scroll in range(4):
            # Use direct swipe instead of scroll_down
            from utils.adb_input import swipe
            debug_print(f"[DEBUG] Swiping from (378,1425) to (378,1106) (attempt {scroll+1}/4)")
            swipe(378, 1425, 378, 1106, duration_ms=500)
            time.sleep(0.2)
            screenshot = take_screenshot()
            
            # Check for race again after each swipe
            if prioritize_g1:
                race_cards = match_template(screenshot, G1_RACE_TEMPLATE, confidence=0.9)
                
                if race_cards:
                    debug_print(f"[DEBUG] Found {len(race_cards)} G1 race card(s) after swipe {scroll+1}")
                    for i, (x, y, w, h) in enumerate(race_cards):
                        debug_print(f"[DEBUG] G1 Race Card {i+1}: bbox=({x}, {y}, {w}, {h})")
                        # Search for match_track.png within the race card region
                        region = (x, y, RACE_CARD_REGION[2], RACE_CARD_REGION[3])
                        debug_print(f"[DEBUG] Extended region: {region}")
                        match_aptitude = locate_match_track_with_brightness(confidence=0.6, region=region, brightness_threshold=180.0)
                        if match_aptitude:
                            debug_print(f"[DEBUG] ✅ Match track found at {match_aptitude} in region {region}")
                        else:
                            debug_print(f"[DEBUG] ❌ No match track found in region {region}")
                        if match_aptitude:
                            debug_print(f"[DEBUG] G1 race found at {match_aptitude} after swipe {scroll+1}")
                            tap(match_aptitude[0], match_aptitude[1])
                            time.sleep(0.2)
                            
                            # Click race button twice like PC version
                            for j in range(2):
                                race_btn = locate_on_screen(screenshot, RACE_BUTTON_TEMPLATE, confidence=0.8)
                                if race_btn:
                                    debug_print(f"[DEBUG] Found race button at {race_btn}")
                                    tap(race_btn[0], race_btn[1])
                                    time.sleep(0.5)
                                else:
                                    debug_print("[DEBUG] Race button not found")
                            return True
                else:
                    debug_print(f"[DEBUG] No G1 race cards found after swipe {scroll+1}")
            else:
                debug_print(f"[DEBUG] Looking for any race (non-G1) after swipe {scroll+1}")
                match_aptitude = locate_match_track_with_brightness(confidence=0.6, brightness_threshold=180.0)
                if match_aptitude:
                    debug_print(f"[DEBUG] Race found at {match_aptitude} after swipe {scroll+1}")
                    tap(match_aptitude[0], match_aptitude[1])
                    time.sleep(0.2)
                    
                    # Click race button twice like PC version
                    for j in range(2):
                        race_btn = locate_on_screen(screenshot, RACE_BUTTON_TEMPLATE, confidence=0.8)
                        if race_btn:
                            debug_print(f"[DEBUG] Found race button at {race_btn}")
                            tap(race_btn[0], race_btn[1])
                            time.sleep(0.5)
                        else:
                            debug_print("[DEBUG] Race button not found")
                    return True
                else:
                    debug_print(f"[DEBUG] No races found after swipe {scroll+1}")
        
        return False
    
    # Use the unified race finding logic
    found = find_and_select_race()
    if not found:
        debug_print("[DEBUG] No suitable race found")
    return found

def check_strategy_before_race(region=(660, 974, 378, 120)) -> bool:
    """Check and ensure strategy matches config before race."""
    debug_print("[DEBUG] Checking strategy before race...")
    
    try:
        screenshot = take_screenshot()
        
        templates = {
            "front": cv2.imread("assets/icons/front.png", cv2.IMREAD_COLOR),
            "late": cv2.imread("assets/icons/late.png", cv2.IMREAD_COLOR),
            "pace": cv2.imread("assets/icons/pace.png", cv2.IMREAD_COLOR),
            "end": cv2.imread("assets/icons/end.png", cv2.IMREAD_COLOR),
        }
        
        # Find brightest strategy using existing project functions
        best_match = None
        best_brightness = 0
        
        for name, template in templates.items():
            try:
                # Use existing match_template function
                matches = match_template(screenshot, template, confidence=0.5, region=region)
                if matches:
                    # Get confidence for best match
                    confidence = max_match_confidence(screenshot, template, region)
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
        expected_strategy = config.get("strategy", "").upper()
        
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
        change_btn = wait_for_image(STRATEGY_BUTTON_TEMPLATE, timeout=10, confidence=0.8)
        if not change_btn:
            debug_print("[DEBUG] Strategy change button not found")
            return False
        
        debug_print(f"[DEBUG] Found strategy change button at {change_btn}")
        tap(change_btn[0], change_btn[1])
        debug_print("[DEBUG] Tapped strategy change button")
        
        # Step 2: Wait for confirm.png to appear
        debug_print("[DEBUG] Waiting for confirm button to appear...")
        confirm_btn = wait_for_image(CONFIRM_BUTTON_TEMPLATE, timeout=10, confidence=0.8)
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

def after_race():
    """Handle post-race actions"""
    debug_print("[DEBUG] Handling post-race actions...")
    
    # # Try to click first next button with fallback mechanism
    # if not click(NEXT_BUTTON_TEMPLATE, confidence=0.7, minSearch=10):
    #     debug_print("[DEBUG] First next button not found after 10 attempts, clicking middle of screen as fallback...")
    #     tap(540, 960)  # Click middle of screen (1080x1920 resolution)
    #     time.sleep(1)
    #     debug_print("[DEBUG] Retrying next button search after screen tap...")
    #     click(NEXT_BUTTON_TEMPLATE, confidence=0.7, minSearch=10)
    
    # time.sleep(4)
    
    # # Try to click second next button with fallback mechanism
    # if not click(NEXT_2_BUTTON_TEMPLATE, confidence=0.7, minSearch=10):
    #     debug_print("[DEBUG] Second next button not found after 10 attempts, clicking middle of screen as fallback...")
    #     tap(540, 960)  # Click middle of screen (1080x1920 resolution)
    #     time.sleep(1)
    #     debug_print("[DEBUG] Retrying next2 button search after screen tap...")
    #     click(NEXT_2_BUTTON_TEMPLATE, confidence=0.7, minSearch=10)
    
    # debug_print("[DEBUG] Post-race actions complete")


# Event handling functions moved to core/event_handling.py
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
    
def is_g1_racing_available(year):
    g1_race_days = {g1_race_day: True for g1_race_day in config.get("g1_race_days", [])}
    return year in g1_race_days or not g1_race_days

def locate_match_track_with_brightness(confidence=0.6, region=None, brightness_threshold=180.0):
    """
    Find center of `assets/ui/match_track.png` that also passes brightness threshold.
    Returns (x, y) center or None.
    """
    try:
        screenshot = take_screenshot()
        matches = match_template(screenshot, MATCH_TRACK_TEMPLATE, confidence=confidence, region=region)
        if not matches:
            debug_print(f"[DEBUG] no matches in match track for region: {region}")
            return None

        grayscale = screenshot.convert("L")
        for (x, y, w, h) in matches:
            try:
                roi = grayscale.crop((x, y, x + w, y + h))
                avg_brightness = ImageStat.Stat(roi).mean[0]
                debug_print(f"[DEBUG] match_track bbox=({x},{y},{w},{h}) brightness={avg_brightness:.1f} (thr {brightness_threshold})")
                if avg_brightness > brightness_threshold:
                    center = (x + w//2, y + h//2)
                    return center
            except Exception as e:
                debug_print(f"[DEBUG] match_track locate error: {e}")
                continue
        return None
    except Exception as e:
        debug_print(f"[DEBUG] match_track locate error: {e}")
        return None