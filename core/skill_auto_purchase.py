import time
import os
import json
from core.skill_recognizer import take_screenshot, perform_swipe, recognize_skill_up_locations
from core.skill_purchase_optimizer import fuzzy_match_skill_name
from utils.device import run_adb
from utils.log import log_debug, log_info, log_warning, log_error


# Global cache for skill points to avoid re-detection
_skill_points_cache = None
_cache_timestamp = 0
_cache_lifetime = 300  # Cache valid for 5 minutes


def cache_skill_points(points: int):
    """Cache skill points for reuse (called from race day detection)"""
    global _skill_points_cache, _cache_timestamp
    _skill_points_cache = points
    _cache_timestamp = time.time()
    log_debug(f"Cached skill points: {points}")

def get_cached_skill_points() -> int | None:
    """Get cached skill points if still valid, None if expired/missing"""
    global _skill_points_cache, _cache_timestamp
    if _skill_points_cache is None:
        return None
    if time.time() - _cache_timestamp > _cache_lifetime:
        log_debug(f"Skill points cache expired")
        _skill_points_cache = None
        return None
    log_debug(f"Using cached skill points: {_skill_points_cache}")
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
        log_info(f"Using cached skill points: {cached}")
        return cached

    try:
        if screenshot is None:
            from utils.screenshot import take_screenshot
            screenshot = take_screenshot()
        
        # Skill points region: 825, 605, 936, 656 (width: 111, height: 51)
        skill_points_region = (825, 605, 936, 656)
        
        # Crop the skill points region
        points_crop = screenshot.crop(skill_points_region)
        
        # Save original debug image
        points_crop.save("debug_skill_points.png")
        log_debug(f"Saved skill points debug image: debug_skill_points.png")
        
        # Optimized OCR - precise region makes simple approach work perfectly
        import pytesseract
        skill_points_raw = pytesseract.image_to_string(points_crop, lang='eng').strip()
        log_debug(f"OCR result: '{skill_points_raw}'")
        
        # Fallback with digits-only if simple OCR fails (rare with current precision)
        if not skill_points_raw:
            log_debug(f"Fallback: Using enhanced OCR with digits-only filter")
            enhanced_crop = enhance_image_for_ocr(points_crop)
            skill_points_raw = pytesseract.image_to_string(enhanced_crop, config='--psm 8 -c tessedit_char_whitelist=0123456789').strip()
            log_debug(f"Fallback result: '{skill_points_raw}'")
        
        # Clean and extract numbers
        skill_points = clean_skill_points(skill_points_raw)
        log_info(f"Available skill points: {skill_points}")
        
        # Cache the result for future use
        cache_skill_points(skill_points)
        return skill_points
        
    except Exception as e:
        log_error(f"Error extracting skill points: {e}")
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
        log_info(f"Error enhancing image: {e}")
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
        result = run_adb(click_command)
        if result is not None:
            log_debug(f"Clicked skill_up button at ({x}, {y}")
            return True
        else:
            log_error(f"Failed to click at ({x}, {y}")
            return False
    except Exception as e:
        log_error(f"Error clicking button: {e}")
        return False

def click_image_button(image_path, description="button", max_attempts=10, wait_between_attempts=0.5):
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
        
        if not os.path.exists(image_path):
            log_error(f"{description} template not found: {image_path}")
            return False
        
        # Load template once
        template = cv2.imread(image_path, cv2.IMREAD_COLOR)
        if template is None:
            log_error(f"Failed to load {description} template: {image_path}")
            return False
        
        log_debug(f"Looking for {description} (max {max_attempts} attempts)")
        
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
                        log_info(f"{description} clicked successfully (attempt {attempt + 1}")
                        return True
                    else:
                        log_error(f"Failed to click {description} (attempt {attempt + 1}")
                else:
                    log_debug(f"{description} not found (attempt {attempt + 1}/{max_attempts}, confidence: {max_val:.3f}")
                
                # Wait before next attempt (except on last attempt)
                if attempt < max_attempts - 1:
                    time.sleep(wait_between_attempts)
                    
            except Exception as e:
                log_warning(f"Error in attempt {attempt + 1}: {e}")
                if attempt < max_attempts - 1:
                    time.sleep(wait_between_attempts)
        
        log_error(f"{description} not found after {max_attempts} attempts")
        return False
            
    except Exception as e:
        log_error(f"Error finding {description}: {e}")
        return False

def fast_swipe_to_top():
    """
    Perform fast swipes to get to the top of the skill list.
    """
    log_info(f"Fast scrolling to top of skill list")
    
    for i in range(8):
        debug_print(f"[DEBUG] Fast swipe {i+1}/8")
        success = perform_swipe(504, 800, 504, 1400, duration=300)  # Swipe DOWN on screen to scroll UP in list
        if success:
            time.sleep(0.3)  # Short wait between fast swipes
        else:
            log_warning(f"Fast swipe {i+1} failed")
    
    log_debug(f"Waiting for UI to settle")
    time.sleep(1.5)  # Reduced wait time

def execute_skill_purchases(purchase_plan, max_scrolls=20):
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
    log_info(f"EXECUTING AUTOMATED SKILL PURCHASES")
    log_info(f"=" * 60)
    
    if not purchase_plan:
        log_error(f"No skills to purchase!")
        return {
            'success': False,
            'purchased_skills': [],
            'failed_skills': [],
            'scrolls_performed': 0,
            'error': 'No skills in purchase plan'
        }
    
    log_info(f"Skills to purchase: {len(purchase_plan)}")
    for i, skill in enumerate(purchase_plan, 1):
        log_info(f"   {i}. {skill['name']} - {skill['price']} points")
    log_info(f"")
    
    purchased_skills = []
    failed_skills = []
    remaining_skills = purchase_plan.copy()
    scrolls_performed = 0
    
    try:
        # Step 1: Fast swipe to top
        fast_swipe_to_top()
        
        # Step 2: Scroll down slowly to find and purchase skills
        log_info(f"Searching for skills to purchase")
        
        while remaining_skills and scrolls_performed < max_scrolls:
            scrolls_performed += 1
            log_info(f"\n[INFO] Scroll {scrolls_performed}/{max_scrolls}")
            log_debug(f"Looking for: {[s['name'] for s in remaining_skills]}")
            
            # Scan current screen for available skills
            result = recognize_skill_up_locations(
                confidence=0.9,
                debug_output=False,
                filter_dark_buttons=True,
                brightness_threshold=150,
                extract_skills=True
            )
            
            if 'error' in result:
                log_error(f"Error during skill detection: {result['error']}")
                break
            
            current_skills = result.get('skills', [])
            if not current_skills:
                log_debug(f"No skills found on this screen")
            else:
                log_debug(f"Found {len(current_skills)} available skills on screen")
                
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
                            log_info(f"Found target skill: {screen_skill['name']} (matches {target_skill['name']})")
                            break
                
                # Purchase found skills
                for match in skills_found_on_screen:
                    target_skill = match['target']
                    screen_skill = match['screen']
                    
                    # Get button coordinates
                    x, y, w, h = screen_skill['location']
                    button_center_x = x + w // 2
                    button_center_y = y + h // 2
                    
                    log_info(f"Purchasing: {screen_skill['name']}")
                    
                    # Click the skill_up button
                    if click_skill_up_button(button_center_x, button_center_y):
                        purchased_skills.append(target_skill)
                        remaining_skills.remove(target_skill)
                        log_info(f"Successfully purchased: {screen_skill['name']}")
                        
                        # Short wait after purchase
                        time.sleep(1)
                    else:
                        log_error(f"Failed to purchase: {screen_skill['name']}")
                
                # If we found and purchased skills, wait a bit longer
                if skills_found_on_screen:
                    time.sleep(1.5)
            
            # Continue scrolling if we haven't found all skills
            if remaining_skills and scrolls_performed < max_scrolls:
                log_debug(f"Scrolling down to find more skills")
                success = perform_swipe(504, 1492, 504, 926, duration=1000)  # Slow scroll like recognizer
                if not success:
                    log_error(f"Failed to scroll, stopping search")
                    break
                
                time.sleep(1.5)  # Wait for scroll animation
        
        # Step 3: Click confirm button
        if purchased_skills:
            log_info(f"\n[INFO] Purchased {len(purchased_skills)} skills, looking for confirm button")
            
            confirm_success = click_image_button("assets/buttons/confirm.png", "confirm button", max_attempts=10)
            if confirm_success:
                log_debug(f"Waiting for confirmation")
                time.sleep(1)  # Reduced wait time
                
                # Step 4: Click learn button
                log_debug(f"Looking for learn button")
                learn_success = click_image_button("assets/buttons/learn.png", "learn button", max_attempts=10)
                if learn_success:
                    log_debug(f"Waiting for learning to complete")
                    time.sleep(1)  # Reduced wait time
                    
                    # Step 5: Click close button (wait before it appears)
                    log_debug(f"Waiting for close button to appear")
                    time.sleep(0.5)  # Reduced wait time
                    close_success = click_image_button("assets/buttons/close.png", "close button", max_attempts=10)
                    if close_success:
                        log_info(f"Skill purchase sequence completed successfully")
                    else:
                        log_warning(f"Close button not found - manual intervention may be needed")
                else:
                    log_warning(f"Learn button not found or failed to click")
            else:
                log_warning(f"Confirm button not found or failed to click")
        
        # Add any remaining skills to failed list
        failed_skills.extend(remaining_skills)
        
        # Summary
        log_info(f"\n" + "=" * 60)
        log_info(f"PURCHASE EXECUTION COMPLETE")
        log_info(f"   Successfully purchased: {len(purchased_skills)} skills")
        log_info(f"   Failed to find/purchase: {len(failed_skills)} skills")
        log_info(f"   Scrolls performed: {scrolls_performed}")
        
        if purchased_skills:
            log_info(f"\n[INFO] Purchased skills:")
            for skill in purchased_skills:
                log_info(f"   • {skill['name']} - {skill['price']} points")
        
        if failed_skills:
            log_info(f"\n[WARNING] Failed to purchase:")
            for skill in failed_skills:
                log_info(f"   • {skill['name']} - {skill['price']} points")
        
        return {
            'success': len(purchased_skills) > 0,
            'purchased_skills': purchased_skills,
            'failed_skills': failed_skills,
            'scrolls_performed': scrolls_performed
        }
        
    except Exception as e:
        log_error(f"Error during skill purchase execution: {e}")
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
    log_info(f"TESTING AUTOMATED SKILL PURCHASE")
    log_info(f"=" * 60)
    log_warning(f"This will actually purchase skills!")
    log_info(f"   Make sure you're on the skill purchase screen.")
    log_info(f"")
    
    # Mock purchase plan for testing
    test_purchase_plan = [
        {"name": "Professor of Curvature", "price": "342"},
        {"name": "Pressure", "price": "160"}
    ]
    
    log_info(f"Test purchase plan:")
    for i, skill in enumerate(test_purchase_plan, 1):
        log_info(f"   {i}. {skill['name']} - {skill['price']} points")
    log_info(f"")
    
    confirm = input("Do you want to proceed with the test purchase? (y/n): ").lower().startswith('y')
    if not confirm:
        log_info(f"Test cancelled.")
        return
    
    # Execute the purchase
    result = execute_skill_purchases(test_purchase_plan)
    
    log_info(f"\n[INFO] Test Results:")
    log_info(f"   Success: {result['success']}")
    log_info(f"   Purchased: {len(result['purchased_skills'])}")
    log_info(f"   Failed: {len(result['failed_skills'])}")
    if 'error' in result:
        log_info(f"   Error: {result['error']}")

if __name__ == "__main__":
    test_skill_auto_purchase()
