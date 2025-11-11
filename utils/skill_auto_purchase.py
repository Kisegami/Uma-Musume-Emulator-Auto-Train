import time
import os
import json
from core.templates_adb import CLOSE_BUTTON_TEMPLATE, CONFIRM_BUTTON_TEMPLATE, LEARN_BUTTON_TEMPLATE
from utils.skill_recognizer import take_screenshot, perform_swipe, recognize_skill_up_locations
from utils.skill_purchase_optimizer import fuzzy_match_skill_name
from utils.adb_screenshot import run_adb_command

# Load config for debug mode
try:
    with open("config.json", "r") as f:
        config = json.load(f)
    DEBUG_MODE = config.get("debug_mode", False)
except:
    DEBUG_MODE = False

# Global cache for skill points to avoid re-detection
_skill_points_cache = None
_cache_timestamp = 0
_cache_lifetime = 300  # Cache valid for 5 minutes

def debug_print(message):
    """Print debug message only if DEBUG_MODE is enabled"""
    if DEBUG_MODE:
        print(message)

def cache_skill_points(points: int):
    """Cache skill points for reuse (called from race day detection)"""
    global _skill_points_cache, _cache_timestamp
    _skill_points_cache = points
    _cache_timestamp = time.time()
    debug_print(f"[DEBUG] Cached skill points: {points}")

def get_cached_skill_points() -> int | None:
    """Get cached skill points if still valid, None if expired/missing"""
    global _skill_points_cache, _cache_timestamp
    if _skill_points_cache is None:
        return None
    if time.time() - _cache_timestamp > _cache_lifetime:
        debug_print("[DEBUG] Skill points cache expired")
        _skill_points_cache = None
        return None
    debug_print(f"[DEBUG] Using cached skill points: {_skill_points_cache}")
    return _skill_points_cache

def extract_skill_points(screenshot=None):
    """
    Extract available skill points from the screen using OCR with enhanced preprocessing.
    First checks cache, then falls back to OCR detection.
    
    Args:
        screenshot: PIL Image (optional, will take new screenshot if not provided)
    
    Returns:
        int: Available skill points, or 0 if extraction fails
    """
    # Check cache first
    cached = get_cached_skill_points()
    if cached is not None:
        print(f"[INFO] Using cached skill points: {cached}")
        return cached

    try:
        if screenshot is None:
            from utils.adb_screenshot import take_screenshot
            screenshot = take_screenshot()
        
        # Skill points region: 825, 605, 936, 656 (width: 111, height: 51)
        skill_points_region = (825, 605, 936, 656)
        
        # Crop the skill points region
        points_crop = screenshot.crop(skill_points_region)
        
        # Save original debug image
        points_crop.save("debug_skill_points.png")
        debug_print("[DEBUG] Saved skill points debug image: debug_skill_points.png")
        
        # Optimized OCR - precise region makes simple approach work perfectly
        import pytesseract
        skill_points_raw = pytesseract.image_to_string(points_crop, lang='eng').strip()
        debug_print(f"[DEBUG] OCR result: '{skill_points_raw}'")
        
        # Fallback with digits-only if simple OCR fails (rare with current precision)
        if not skill_points_raw:
            debug_print("[DEBUG] Fallback: Using enhanced OCR with digits-only filter")
            enhanced_crop = enhance_image_for_ocr(points_crop)
            skill_points_raw = pytesseract.image_to_string(enhanced_crop, config='--psm 8 -c tessedit_char_whitelist=0123456789').strip()
            debug_print(f"[DEBUG] Fallback result: '{skill_points_raw}'")
        
        # Clean and extract numbers
        skill_points = clean_skill_points(skill_points_raw)
        print(f"[INFO] Available skill points: {skill_points}")
        
        # Cache the result for future use
        cache_skill_points(skill_points)
        return skill_points
        
    except Exception as e:
        print(f"[ERROR] Error extracting skill points: {e}")
        return 0

def clean_skill_points(text):
    """
    Clean and extract skill points from OCR text.
    
    Args:
        text: Raw OCR text
    
    Returns:
        int: Extracted skill points
    """
    if not text:
        return 0
    
    import re
    # Normalize common OCR confusions before extracting digits
    # Treat backslash as '1' (e.g., 77\ -> 771)
    text = text.replace('\\', '1')
    # Remove extra whitespace and newlines
    text = re.sub(r'\s+', ' ', text).strip()
    
    # Extract all numbers
    numbers = re.findall(r'\d+', text)
    
    if numbers:
        # Return the largest number found (skill points are usually the biggest number)
        skill_points = max(int(num) for num in numbers)
        return skill_points
    
    return 0

def enhance_image_for_ocr(image):
    """
    Simple image enhancement for OCR fallback (rarely needed with precise region).
    
    Args:
        image: PIL Image
    
    Returns:
        PIL Image: Enhanced image
    """
    try:
        from PIL import ImageEnhance
        # Convert to grayscale and resize for better OCR
        if image.mode != 'L':
            image = image.convert('L')
        
        width, height = image.size
        image = image.resize((width * 3, height * 3), Image.LANCZOS)
        
        return image
        
    except Exception as e:
        print(f"Error enhancing image: {e}")
        return image

def click_skill_up_button(x, y):
    """
    Click on a skill_up button at the specified coordinates.
    
    Args:
        x, y: Coordinates of the skill_up button
    
    Returns:
        bool: True if click was successful, False otherwise
    """
    try:
        click_command = ['shell', 'input', 'tap', str(x), str(y)]
        result = run_adb_command(click_command)
        if result is not None:
            debug_print(f"[DEBUG] Clicked skill_up button at ({x}, {y})")
            return True
        else:
            print(f"[ERROR] Failed to click at ({x}, {y})")
            return False
    except Exception as e:
        print(f"[ERROR] Error clicking button: {e}")
        return False

def click_image_button(template, description="button", max_attempts=10, wait_between_attempts=0.5):
    """
    Find and click a button by image template matching with retry attempts.
    
    Args:
        image_path: Path to the button image template
        description: Description for logging
        max_attempts: Maximum number of attempts to find the button
        wait_between_attempts: Seconds to wait between attempts
    
    Returns:
        bool: True if button was found and clicked, False otherwise
    """
    try:
        import cv2
        import numpy as np

        debug_print(f"[DEBUG] Looking for {description} (max {max_attempts} attempts)")
        
        for attempt in range(max_attempts):
            try:
                # Take screenshot
                screenshot = take_screenshot()
                screenshot_cv = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
                
                # Perform template matching
                result = cv2.matchTemplate(screenshot_cv, template, cv2.TM_CCOEFF_NORMED)
                
                # Find the best match
                min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
                
                if max_val >= 0.8:  # High confidence threshold
                    # Calculate center of the button
                    template_height, template_width = template.shape[:2]
                    center_x = max_loc[0] + template_width // 2
                    center_y = max_loc[1] + template_height // 2
                    
                    # Click the button
                    success = click_skill_up_button(center_x, center_y)
                    if success:
                        print(f"[INFO] {description} clicked successfully (attempt {attempt + 1})")
                        return True
                    else:
                        print(f"[ERROR] Failed to click {description} (attempt {attempt + 1})")
                else:
                    debug_print(f"[DEBUG] {description} not found (attempt {attempt + 1}/{max_attempts}, confidence: {max_val:.3f})")
                
                # Wait before next attempt (except on last attempt)
                if attempt < max_attempts - 1:
                    time.sleep(wait_between_attempts)
                    
            except Exception as e:
                print(f"[WARNING] Error in attempt {attempt + 1}: {e}")
                if attempt < max_attempts - 1:
                    time.sleep(wait_between_attempts)
        
        print(f"[ERROR] {description} not found after {max_attempts} attempts")
        return False
            
    except Exception as e:
        print(f"[ERROR] Error finding {description}: {e}")
        return False

def fast_swipe_to_top():
    """
    Perform fast swipes to get to the top of the skill list.
    """
    print("[INFO] Fast scrolling to top of skill list")
    
    for i in range(8):
        debug_print(f"[DEBUG] Fast swipe {i+1}/8")
        success = perform_swipe(504, 800, 504, 1400, duration=300)  # Swipe DOWN on screen to scroll UP in list
        if success:
            time.sleep(0.3)  # Short wait between fast swipes
        else:
            print(f"[WARNING] Fast swipe {i+1} failed")
    
    debug_print("[DEBUG] Waiting for UI to settle")
    time.sleep(1.5)  # Reduced wait time

def execute_skill_purchases(purchase_plan, bought_skills, max_scrolls=20):
    """
    Execute the automated skill purchase plan.
    
    Args:
        purchase_plan: List of skills to purchase (from create_purchase_plan)
        max_scrolls: Maximum number of scrolls to prevent infinite loops
    
    Returns:
        dict: {
            'success': bool,
            'purchased_skills': [list of successfully purchased skills],
            'failed_skills': [list of skills that couldn't be found/purchased],
            'scrolls_performed': int
        }
    """
    print("[INFO] EXECUTING AUTOMATED SKILL PURCHASES")
    print("=" * 60)
    
    if not purchase_plan:
        print("[ERROR] No skills to purchase!")
        return {
            'success': False,
            'purchased_skills': [],
            'failed_skills': [],
            'scrolls_performed': 0,
            'error': 'No skills in purchase plan'
        }
    
    print(f"[INFO] Skills to purchase: {len(purchase_plan)}")
    for i, skill in enumerate(purchase_plan, 1):
        print(f"   {i}. {skill['name']} - {skill['price']} points")
    print()
    
    purchased_skills = []
    failed_skills = []
    remaining_skills = purchase_plan.copy()
    scrolls_performed = 0
    
    try:
        # Step 1: Fast swipe to top
        fast_swipe_to_top()
        
        # Step 2: Scroll down slowly to find and purchase skills
        print("[INFO] Searching for skills to purchase")
        
        while remaining_skills and scrolls_performed < max_scrolls:
            scrolls_performed += 1
            print(f"\n[INFO] Scroll {scrolls_performed}/{max_scrolls}")
            debug_print(f"[DEBUG] Looking for: {[s['name'] for s in remaining_skills]}")
            
            # Scan current screen for available skills
            result = recognize_skill_up_locations(
                confidence=0.9,
                debug_output=False,
                filter_dark_buttons=True,
                brightness_threshold=150,
                extract_skills=True
            )
            
            if 'error' in result:
                print(f"[ERROR] Error during skill detection: {result['error']}")
                break
            
            current_skills = result.get('skills', [])
            if not current_skills:
                debug_print("[DEBUG] No skills found on this screen")
            else:
                debug_print(f"[DEBUG] Found {len(current_skills)} available skills on screen")
                
                # Check if any of our target skills are on this screen
                skills_found_on_screen = []
                
                for target_skill in remaining_skills:
                    for screen_skill in current_skills:
                        # Use fuzzy matching to find target skills
                        if fuzzy_match_skill_name(screen_skill['name'], target_skill['name']):
                            skills_found_on_screen.append({
                                'target': target_skill,
                                'screen': screen_skill
                            })
                            print(f"[INFO] Found target skill: {screen_skill['name']} (matches {target_skill['name']})")
                            break
                
                # Purchase found skills
                for match in skills_found_on_screen:
                    target_skill = match['target']
                    screen_skill = match['screen']
                    
                    # Get button coordinates
                    x, y, w, h = screen_skill['location']
                    button_center_x = x + w // 2
                    button_center_y = y + h // 2
                    
                    print(f"[INFO] Purchasing: {screen_skill['name']}")
                    
                    # Click the skill_up button
                    if click_skill_up_button(button_center_x, button_center_y):
                        purchased_skills.append(target_skill)
                        remaining_skills.remove(target_skill)
                        print(f"[INFO] Successfully purchased: {screen_skill['name']}")
                        
                        # Short wait after purchase
                        time.sleep(1)
                    else:
                        print(f"[ERROR] Failed to purchase: {screen_skill['name']}")
                
                # If we found and purchased skills, wait a bit longer
                if skills_found_on_screen:
                    time.sleep(1.5)
            
            # Continue scrolling if we haven't found all skills
            if remaining_skills and scrolls_performed < max_scrolls:
                debug_print("[DEBUG] Scrolling down to find more skills")
                success = perform_swipe(504, 1492, 504, 926, duration=1000)  # Slow scroll like recognizer
                if not success:
                    print("[ERROR] Failed to scroll, stopping search")
                    break
                
                time.sleep(1.5)  # Wait for scroll animation
        
        # Step 3: Click confirm button
        if purchased_skills:
            print(f"\n[INFO] Purchased {len(purchased_skills)} skills, looking for confirm button")
            
            confirm_success = click_image_button(CONFIRM_BUTTON_TEMPLATE, "confirm button", max_attempts=10)
            if confirm_success:
                debug_print("[DEBUG] Waiting for confirmation")
                time.sleep(1)  # Reduced wait time
                
                # Step 4: Click learn button
                debug_print("[DEBUG] Looking for learn button")
                learn_success = click_image_button(LEARN_BUTTON_TEMPLATE, "learn button", max_attempts=10)
                if learn_success:
                    debug_print("[DEBUG] Waiting for learning to complete")
                    time.sleep(1)  # Reduced wait time
                    
                    # Step 5: Click close button (wait before it appears)
                    debug_print("[DEBUG] Waiting for close button to appear")
                    time.sleep(0.5)  # Reduced wait time
                    close_success = click_image_button(CLOSE_BUTTON_TEMPLATE, "close button", max_attempts=10)
                    if close_success:
                        print("[INFO] Skill purchase sequence completed successfully")
                    else:
                        print("[WARNING] Close button not found - manual intervention may be needed")
                else:
                    print("[WARNING] Learn button not found or failed to click")
            else:
                print("[WARNING] Confirm button not found or failed to click")
        
        # Add any remaining skills to failed list
        failed_skills.extend(remaining_skills)
        
        # Summary
        print(f"\n" + "=" * 60)
        print(f"[INFO] PURCHASE EXECUTION COMPLETE")
        print(f"   Successfully purchased: {len(purchased_skills)} skills")
        print(f"   Failed to find/purchase: {len(failed_skills)} skills")
        print(f"   Scrolls performed: {scrolls_performed}")
        
        if purchased_skills:
            print(f"\n[INFO] Purchased skills:")
            for skill in purchased_skills:
                bought_skills[skill['name']] = True
                print(f"   • {skill['name']} - {skill['price']} points")
        
        if failed_skills:
            print(f"\n[WARNING] Failed to purchase:")
            for skill in failed_skills:
                print(f"   • {skill['name']} - {skill['price']} points")
        
        return {
            'success': len(purchased_skills) > 0,
            'purchased_skills': purchased_skills,
            'failed_skills': failed_skills,
            'scrolls_performed': scrolls_performed
        }
        
    except Exception as e:
        print(f"[ERROR] Error during skill purchase execution: {e}")
        import traceback
        traceback.print_exc()
        
        return {
            'success': False,
            'purchased_skills': purchased_skills,
            'failed_skills': failed_skills + remaining_skills,
            'scrolls_performed': scrolls_performed,
            'error': str(e)
        }

def test_skill_auto_purchase():
    """
    Test function for the automated skill purchase system.
    """
    print("[INFO] TESTING AUTOMATED SKILL PURCHASE")
    print("=" * 60)
    print("[WARNING] This will actually purchase skills!")
    print("   Make sure you're on the skill purchase screen.")
    print()

    bought_skills = {}
    
    # Mock purchase plan for testing
    test_purchase_plan = [
        {"name": "Professor of Curvature", "price": "342"},
        {"name": "Pressure", "price": "160"}
    ]
    
    print("[INFO] Test purchase plan:")
    for i, skill in enumerate(test_purchase_plan, 1):
        print(f"   {i}. {skill['name']} - {skill['price']} points")
    print()
    
    confirm = input("Do you want to proceed with the test purchase? (y/n): ").lower().startswith('y')
    if not confirm:
        print("[INFO] Test cancelled.")
        return
    
    # Execute the purchase
    result = execute_skill_purchases(test_purchase_plan, bought_skills)
    
    print(f"\n[INFO] Test Results:")
    print(f"   Success: {result['success']}")
    print(f"   Purchased: {len(result['purchased_skills'])}")
    print(f"   Failed: {len(result['failed_skills'])}")
    if 'error' in result:
        print(f"   Error: {result['error']}")

if __name__ == "__main__":
    test_skill_auto_purchase()
