from core.templates_adb import SKILL_UP_BUTTON_TEMPLATE
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import os
import time
import re
import json
from utils.adb_screenshot import take_screenshot, run_adb_command

# Load config for debug mode
try:
    with open("config.json", "r") as f:
        config = json.load(f)
    DEBUG_MODE = config.get("debug_mode", False)
except:
    DEBUG_MODE = False

def debug_print(message):
    """Print debug message only if DEBUG_MODE is enabled"""
    if DEBUG_MODE:
        print(message)

try:
    import pytesseract
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False
    debug_print("[DEBUG] Warning: pytesseract not available. OCR features will be disabled.")



def remove_overlapping_rectangles(rectangles, overlap_threshold=0.5):
    """
    Remove overlapping rectangles based on overlap threshold.
    
    Args:
        rectangles: List of (x, y, width, height) tuples
        overlap_threshold: Minimum overlap ratio to consider rectangles as duplicates
    
    Returns:
        List of non-overlapping rectangles
    """
    if not rectangles:
        return []
    
    # Convert to (x1, y1, x2, y2) format for easier calculation
    boxes = []
    for x, y, w, h in rectangles:
        boxes.append([x, y, x + w, y + h])
    
    # Sort by area (largest first)
    boxes = sorted(boxes, key=lambda box: (box[2] - box[0]) * (box[3] - box[1]), reverse=True)
    
    keep = []
    
    for box in boxes:
        should_keep = True
        
        for kept_box in keep:
            # Calculate intersection
            x1 = max(box[0], kept_box[0])
            y1 = max(box[1], kept_box[1])
            x2 = min(box[2], kept_box[2])
            y2 = min(box[3], kept_box[3])
            
            if x1 < x2 and y1 < y2:
                # Calculate overlap area
                intersection_area = (x2 - x1) * (y2 - y1)
                box_area = (box[2] - box[0]) * (box[3] - box[1])
                
                # Calculate overlap ratio
                overlap_ratio = intersection_area / box_area
                
                if overlap_ratio >= overlap_threshold:
                    should_keep = False
                    break
        
        if should_keep:
            keep.append(box)
    
    # Convert back to (x, y, width, height) format
    result = []
    for x1, y1, x2, y2 in keep:
        result.append((x1, y1, x2 - x1, y2 - y1))
    
    return result


def perform_swipe(start_x, start_y, end_x, end_y, duration=1000):
    """
    Perform smooth swipe gesture using ADB.
    
    Args:
        start_x, start_y: Starting coordinates
        end_x, end_y: Ending coordinates  
        duration: Swipe duration in milliseconds (optimized for smooth scrolling)
    
    Returns:
        bool: True if swipe was successful, False otherwise
    """
    try:
        swipe_command = ['shell', 'input', 'swipe', str(start_x), str(start_y), str(end_x), str(end_y), str(duration)]
        result = run_adb_command(swipe_command)
        if result is not None:
            debug_print(f"[DEBUG] Swiped from ({start_x}, {start_y}) to ({end_x}, {end_y})")
            return True
        else:
            debug_print(f"[DEBUG] Failed to perform swipe")
            return False
    except Exception as e:
        debug_print(f"[DEBUG] Error performing swipe: {e}")
        return False

def extract_skill_info(screenshot, button_x, button_y, anchor_x=946, anchor_y=809):
    """
    Extract skill name and price from screenshot using button position as anchor.
    
    Args:
        screenshot: PIL Image of the screen
        button_x, button_y: Detected skill_up button position
        anchor_x, anchor_y: Reference anchor position (946, 809)
    
    Returns:
        dict: {'name': str, 'price': str, 'name_region': tuple, 'price_region': tuple}
    """
    try:
        if not OCR_AVAILABLE:
            return {
                'name': 'OCR not available',
                'price': 'OCR not available',
                'name_region': None,
                'price_region': None
            }
        
        # Calculate offset from anchor position
        offset_x = button_x - anchor_x
        offset_y = button_y - anchor_y
        
        # Define regions relative to anchor
        # Skill name region: 204, 719, 732, 788 (width: 528, height: 69)
        name_x1 = 204 + offset_x
        name_y1 = 719 + offset_y
        name_x2 = 732 + offset_x
        name_y2 = 788 + offset_y
        name_region = (name_x1, name_y1, name_x2, name_y2)
        
        # Skill price region: 834, 803, 927, 854 (width: 93, height: 51)
        price_x1 = 834 + offset_x
        price_y1 = 803 + offset_y
        price_x2 = 927 + offset_x
        price_y2 = 854 + offset_y
        price_region = (price_x1, price_y1, price_x2, price_y2)
        
        # Extract skill name with simple OCR
        skill_name = "Name Error"
        try:
            name_crop = screenshot.crop(name_region)
            skill_name_raw = pytesseract.image_to_string(name_crop, lang='eng').strip()
            skill_name = clean_skill_name(skill_name_raw)
        except Exception as e:
            debug_print(f"[DEBUG] Name OCR error: {e}")
        
        # Extract skill price with simple OCR
        skill_price = "Price Error"
        try:
            price_crop = screenshot.crop(price_region)
            
            # Try multiple OCR approaches
            skill_price_raw = ""
            
            # Approach 1: Simple OCR
            skill_price_raw = pytesseract.image_to_string(price_crop, lang='eng').strip()
            
            # Approach 2: If empty, try with digits-only config
            if not skill_price_raw:
                skill_price_raw = pytesseract.image_to_string(price_crop, config='--psm 8 -c tessedit_char_whitelist=0123456789').strip()
            
            # Approach 3: If still empty, try different PSM
            if not skill_price_raw:
                skill_price_raw = pytesseract.image_to_string(price_crop, config='--psm 7').strip()
            
            debug_print(f"[DEBUG] Raw price OCR: '{skill_price_raw}'")
            skill_price = clean_skill_price(skill_price_raw)
            debug_print(f"[DEBUG] Cleaned price: '{skill_price}'")
            
            # Save debug image if price OCR still fails
            if not skill_price_raw or skill_price == "0":
                debug_filename = f"debug_price_{skill_name.replace(' ', '_')}.png"
                price_crop.save(debug_filename)
                debug_print(f"[DEBUG] Saved debug image: {debug_filename}")
                
        except Exception as e:
            debug_print(f"[DEBUG] Price OCR error: {e}")
        
        result = {
            'name': skill_name,
            'price': skill_price,
            'name_region': name_region,
            'price_region': price_region
        }
        return result
        
    except Exception as e:
        debug_print(f"[DEBUG] Error extracting skill info: {e}")
        debug_print(f"[DEBUG] Error type: {type(e)}")
        import traceback
        traceback.print_exc()
        return {
            'name': 'Error',
            'price': 'Error',
            'name_region': None,
            'price_region': None
        }



def clean_skill_name(text):
    """
    Clean and format skill name text from OCR.
    
    Args:
        text: Raw OCR text
    
    Returns:
        Cleaned skill name string
    """
    if not text:
        return "Unknown Skill"
    
    # Remove extra whitespace and newlines
    text = re.sub(r'\s+', ' ', text).strip()
    
    # Remove common OCR artifacts
    text = re.sub(r'[^\w\s\-\(\)\'\"&]', '', text)
    
    # Fix common OCR errors at the beginning
    # Remove leading numbers that shouldn't be there
    text = re.sub(r'^[0-9]+', '', text).strip()
    
    # Fix specific known OCR misreads
    if text.lower().startswith('1can see right through you'):
        text = 'I Can See Right Through You'
    elif text.lower().startswith('1') and 'can see' in text.lower():
        text = 'I Can See Right Through You'
    elif 'can see right through you' in text.lower() and text.lower() != 'i can see right through you':
        text = 'I Can See Right Through You'
    
    # Fix Umastan -> Uma Stan
    if text.lower() in ['umastan', 'uma stan', 'umestan']:
        text = 'Uma Stan'
    
    # Keep original capitalization (don't force title case)
    # This preserves natural capitalization like "Professor of Curvature"
    
    return text if text else "Unknown Skill"

def clean_skill_price(text):
    """
    Clean and format skill price text from OCR.
    
    Args:
        text: Raw OCR text
    
    Returns:
        Cleaned price string
    """
    if not text:
        return "0"
    
    # Remove extra whitespace and newlines
    text = re.sub(r'\s+', ' ', text).strip()
    
    # Extract numbers (price is likely numeric) 
    numbers = re.findall(r'\d+', text)
    if numbers:
        return numbers[0]  # Return first number found
    
    # If no numbers found, return the raw text (might still be useful)
    return text if text else "0"

def is_button_available(screenshot, x, y, width, height, brightness_threshold=150):
    """
    Check if a skill button is available (bright) or unavailable (dark).
    
    Args:
        screenshot: PIL Image of the screen
        x, y, width, height: Button location and size
        brightness_threshold: Minimum average brightness for available buttons
    
    Returns:
        tuple: (is_available: bool, avg_brightness: float)
    """
    try:
        # Extract the button region
        button_region = screenshot.crop((x, y, x + width, y + height))
        
        # Convert to grayscale for brightness analysis
        gray_button = button_region.convert('L')
        
        # Calculate average brightness
        import numpy as np
        brightness_array = np.array(gray_button)
        avg_brightness = np.mean(brightness_array)
        
        # Check if button is bright enough (available)
        is_available = avg_brightness >= brightness_threshold
        
        return is_available, avg_brightness
        
    except Exception as e:
        debug_print(f"[DEBUG] Error checking button availability: {e}")
        return True, 0  # Default to available if check fails

def recognize_skill_up_locations(confidence=0.9, debug_output=True, overlap_threshold=0.5, 
                               filter_dark_buttons=True, brightness_threshold=150,
                               extract_skills=True):
    """
    Recognize and count skill_up.png locations on screen using ADB capture.
    
    Args:
        confidence: Minimum confidence threshold for template matching (0.0 to 1.0)
        debug_output: Whether to generate debug image with bounding boxes
        overlap_threshold: Minimum overlap ratio to consider rectangles as duplicates
        filter_dark_buttons: Whether to filter out dark/unavailable skill buttons
        brightness_threshold: Minimum average brightness for available buttons (0-255)
        extract_skills: Whether to extract skill names and prices using OCR
    
    Returns:
        dict: {
            'count': int,
            'locations': [(x, y, width, height), ...],
            'skills': [{'name': str, 'price': str, 'location': tuple, 'regions': dict}, ...],
            'debug_image_path': str or None
        }
    """
    try:
        # Take screenshot
        screenshot = take_screenshot()
        
        # Convert screenshot to OpenCV format
        screenshot_cv = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
        
        # Get template dimensions
        template_height, template_width = SKILL_UP_BUTTON_TEMPLATE.shape[:2]
        
        # Perform template matching
        result = cv2.matchTemplate(screenshot_cv, SKILL_UP_BUTTON_TEMPLATE, cv2.TM_CCOEFF_NORMED)
        
        # Find locations where the matching exceeds the threshold
        locations = np.where(result >= confidence)
        
        # Convert to list of rectangles
        matches = []
        for pt in zip(*locations[::-1]):  # Switch columns and rows
            matches.append((pt[0], pt[1], template_width, template_height))
        
        # Remove overlapping rectangles
        unique_matches = remove_overlapping_rectangles(matches, overlap_threshold)
        
        # Filter out dark/unavailable buttons if requested
        available_matches = []
        brightness_info = []
        
        if filter_dark_buttons:
            debug_print(f"[DEBUG] Filtering dark buttons (brightness threshold: {brightness_threshold})...")
            for x, y, w, h in unique_matches:
                is_available, avg_brightness = is_button_available(
                    screenshot, x, y, w, h, brightness_threshold
                )
                brightness_info.append({
                    'location': (x, y, w, h),
                    'brightness': avg_brightness,
                    'available': is_available
                })
                
                if is_available:
                    available_matches.append((x, y, w, h))
                    
            debug_print(f"[DEBUG] Found {len(matches)} raw matches, {len(unique_matches)} after de-duplication, {len(available_matches)} available (bright) buttons")
        else:
            available_matches = unique_matches
            debug_print(f"[DEBUG] Found {len(matches)} raw matches, {len(unique_matches)} after de-duplication")
        
        # Extract skill information if requested
        skills_info = []
        if extract_skills and available_matches:
            debug_print(f"[DEBUG] Extracting skill information using OCR...")
            for i, (x, y, w, h) in enumerate(available_matches):
                try:
                    skill_info = extract_skill_info(screenshot, x, y)
                    skill_data = {
                        'name': skill_info['name'],
                        'price': skill_info['price'],
                        'location': (x, y, w, h),
                        'regions': {
                            'name_region': skill_info['name_region'],
                            'price_region': skill_info['price_region']
                        }
                    }
                    skills_info.append(skill_data)
                    debug_print(f"[DEBUG] {i+1}. {skill_info['name']} - {skill_info['price']}")
                except Exception as e:
                    debug_print(f"[DEBUG] {i+1}. Error extracting skill: {e}")
                    # Add a fallback skill entry
                    skill_data = {
                        'name': f'Skill {i+1} (Error)',
                        'price': 'Error',
                        'location': (x, y, w, h),
                        'regions': {
                            'name_region': None,
                            'price_region': None
                        }
                    }
                    skills_info.append(skill_data)
        
        debug_image_path = None
        
        # Generate debug image if requested
        if debug_output and (available_matches or unique_matches):
            debug_image_path = generate_debug_image(
                screenshot, 
                available_matches if filter_dark_buttons else unique_matches, 
                confidence,
                brightness_info if filter_dark_buttons else None,
                filter_dark_buttons
            )
        
        result = {
            'count': len(available_matches),
            'locations': available_matches,
            'skills': skills_info,
            'debug_image_path': debug_image_path,
            'raw_matches': len(matches),
            'deduplicated_matches': len(unique_matches),
            'confidence_used': confidence,
            'overlap_threshold_used': overlap_threshold,
            'brightness_threshold_used': brightness_threshold if filter_dark_buttons else None,
            'filter_dark_buttons_used': filter_dark_buttons,
            'extract_skills_used': extract_skills
        }
        
        if filter_dark_buttons:
            result['brightness_info'] = brightness_info
            result['dark_buttons_filtered'] = len(unique_matches) - len(available_matches)
        
        return result
        
    except Exception as e:
        debug_print(f"[DEBUG] Error in skill recognition: {e}")
        return {
            'count': 0,
            'locations': [],
            'skills': [],
            'debug_image_path': None,
            'error': str(e)
        }

def generate_debug_image(screenshot, locations, confidence, brightness_info=None, filter_dark_buttons=False):
    """
    Generate debug image with bounding boxes drawn on detected skill_up locations.
    
    Args:
        screenshot: PIL Image of the screen
        locations: List of (x, y, width, height) tuples
        confidence: Confidence threshold used for detection
        brightness_info: List of brightness information for each detection
        filter_dark_buttons: Whether dark button filtering was applied
    
    Returns:
        str: Path to the saved debug image
    """
    try:
        # Create a copy of the screenshot for drawing
        debug_image = screenshot.copy()
        draw = ImageDraw.Draw(debug_image)
        
        # Try to load a font, fall back to default if not available
        try:
            font = ImageFont.truetype("arial.ttf", 16)
        except:
            try:
                font = ImageFont.load_default()
            except:
                font = None
        
        # Draw bounding boxes and labels
        for i, (x, y, width, height) in enumerate(locations):
            # Determine box color based on availability
            box_color = "green"  # Default for available buttons
            label = f"{i+1}"
            
            # Add brightness info if available
            if brightness_info:
                # Find brightness info for this location
                brightness_data = None
                for info in brightness_info:
                    if info['location'] == (x, y, width, height):
                        brightness_data = info
                        break
                
                if brightness_data:
                    if brightness_data['available']:
                        box_color = "green"
                        label = f"{i+1} (✓{brightness_data['brightness']:.0f})"
                    else:
                        box_color = "red"
                        label = f"{i+1} (✗{brightness_data['brightness']:.0f})"
            
            # Draw rectangle with colored border
            draw.rectangle([x, y, x + width, y + height], outline=box_color, width=3)
            
            # Draw label
            if font:
                # Calculate text size for background
                bbox = draw.textbbox((0, 0), label, font=font)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]
                
                # Draw background for text
                draw.rectangle([x, y - text_height - 2, x + text_width + 4, y], 
                             fill=box_color, outline=box_color)
                
                # Draw text
                draw.text((x + 2, y - text_height - 1), label, fill="white", font=font)
            else:
                # Fallback without font
                draw.text((x + 2, y - 15), label, fill=box_color)
        
        # Add summary information
        summary_lines = [
            f"Skill Up Detection Results:",
            f"Available Buttons: {len(locations)}",
            f"Confidence: {confidence}"
        ]
        
        if filter_dark_buttons and brightness_info:
            total_detected = len(brightness_info)
            dark_buttons = len([info for info in brightness_info if not info['available']])
            summary_lines.extend([
                f"Total Detected: {total_detected}",
                f"Dark/Unavailable: {dark_buttons}",
                f"Legend: ✓=Available, ✗=Dark"
            ])
        
        summary_text = "\n".join(summary_lines)
        
        if font:
            draw.text((10, 10), summary_text, fill="blue", font=font)
        else:
            draw.text((10, 10), summary_text, fill="blue")
        
        # Save debug image with timestamp
        timestamp = int(time.time())
        debug_filename = f"debug_skill_up_{timestamp}.png"
        debug_path = os.path.join("debug_images", debug_filename)
        
        # Create debug directory if it doesn't exist
        os.makedirs("debug_images", exist_ok=True)
        
        # Save the image
        debug_image.save(debug_path)
        debug_print(f"[DEBUG] Debug image saved: {debug_path}")
        
        return debug_path
        
    except Exception as e:
        debug_print(f"[DEBUG] Error generating debug image: {e}")
        return None

def test_skill_recognition():
    """
    Test function for skill recognition - can be used for manual testing.
    """
    debug_print("[DEBUG] Testing skill recognition with brightness filtering...")
    debug_print("[DEBUG] " + "=" * 60)
    
    # Test with optimized settings for Auto Skill Purchase
    debug_print(f"[DEBUG] Testing with confidence: 0.9 (optimized for Auto Skill Purchase)")
    result = recognize_skill_up_locations(
        confidence=0.9, 
        debug_output=True,
        filter_dark_buttons=True,
        brightness_threshold=150
    )
        
    if 'error' in result:
        debug_print(f"[DEBUG] Error: {result['error']}")
        return
        
    debug_print(f"[DEBUG] Available skill_up icons: {result['count']}")
    debug_print(f"[DEBUG] Raw matches: {result.get('raw_matches', 'N/A')}")
    debug_print(f"[DEBUG] After de-duplication: {result.get('deduplicated_matches', 'N/A')}")
    
    if result.get('dark_buttons_filtered', 0) > 0:
        debug_print(f"[DEBUG] Dark buttons filtered out: {result['dark_buttons_filtered']}")
    
    # Show skill information if available
    if result.get('skills'):
        debug_print(f"[DEBUG] Detected Skills and Prices:")
        debug_print("[DEBUG] " + "=" * 60)
        for i, skill in enumerate(result['skills']):
            x, y, w, h = skill['location']
            debug_print(f"[DEBUG] {i+1}. Skill: {skill['name']}")
            debug_print(f"[DEBUG]      Price: {skill['price']}")
            debug_print(f"[DEBUG]      Button Location: ({x}, {y}) size: {w}x{h}")
            if skill['regions']['name_region']:
                nr = skill['regions']['name_region']
                debug_print(f"[DEBUG]      Name Region: ({nr[0]}, {nr[1]}) to ({nr[2]}, {nr[3]})")
            if skill['regions']['price_region']:
                pr = skill['regions']['price_region']
                debug_print(f"[DEBUG]      Price Region: ({pr[0]}, {pr[1]}) to ({pr[2]}, {pr[3]})")
            debug_print("[DEBUG] ")
    elif result['locations']:
        debug_print("[DEBUG] Available button locations (skill info extraction disabled):")
        for i, (x, y, w, h) in enumerate(result['locations']):
            debug_print(f"[DEBUG] {i+1}: ({x}, {y}) size: {w}x{h}")
    
    # Show brightness info if available
    if 'brightness_info' in result:
        debug_print("[DEBUG] Brightness analysis:")
        for info in result['brightness_info']:
            x, y, w, h = info['location']
            status = "✓ Available" if info['available'] else "✗ Dark"
            debug_print(f"[DEBUG] ({x}, {y}): {info['brightness']:.1f} - {status}")
    
    if result['debug_image_path']:
        debug_print(f"[DEBUG] Debug image: {result['debug_image_path']}")
    
    # Test comparison between filtered and unfiltered
    debug_print(f"[DEBUG] " + "=" * 60)
    debug_print("[DEBUG] Comparing filtered vs unfiltered detection:")
    
    debug_print("[DEBUG] 1. Without brightness filtering:")
    result_unfiltered = recognize_skill_up_locations(
        confidence=0.9, 
        debug_output=False,
        filter_dark_buttons=False
    )
    debug_print(f"[DEBUG]    Found: {result_unfiltered['count']} buttons")
    
    debug_print("[DEBUG] 2. With brightness filtering (Auto Skill Purchase optimized):")
    result_filtered = recognize_skill_up_locations(
        confidence=0.9, 
        debug_output=True,
        filter_dark_buttons=True,
        brightness_threshold=150
    )
    debug_print(f"[DEBUG]    Found: {result_filtered['count']} available buttons")
    if 'dark_buttons_filtered' in result_filtered:
        debug_print(f"[DEBUG]    Filtered out: {result_filtered['dark_buttons_filtered']} dark buttons")
    
    debug_print("[DEBUG] " + "=" * 60)
    debug_print("[DEBUG] Test completed!")

def scan_all_skills_with_scroll(swipe_start_x=504, swipe_start_y=1492, swipe_end_x=504, swipe_end_y=926,
                               confidence=0.9, brightness_threshold=150, max_scrolls=20):
    """
    Scan all available skills by scrolling through the list until duplicates are found.
    Uses optimized slow swipe for smooth scrolling without acceleration.
    
    Args:
        swipe_start_x, swipe_start_y: Starting coordinates for swipe
        swipe_end_x, swipe_end_y: Ending coordinates for swipe
        confidence: Template matching confidence (default: 0.9)
        brightness_threshold: Brightness threshold for available buttons (default: 150)
        max_scrolls: Maximum number of scrolls to prevent infinite loops (default: 20)
    
    Returns:
        dict: {
            'all_skills': [list of all unique skills found],
            'total_unique_skills': int,
            'scrolls_performed': int,
            'duplicate_found': str or None
        }
    """
    debug_print("[DEBUG] Scanning all available skills with scrolling")
    debug_print("[DEBUG] " + "=" * 60)
    
    all_skills = []
    seen_skill_names = set()
    scrolls_performed = 0
    duplicate_found = None
    
    try:
        while scrolls_performed < max_scrolls:
            debug_print(f"[DEBUG] Scroll {scrolls_performed + 1}/{max_scrolls}")
            
            # Take screenshot and detect skills
            result = recognize_skill_up_locations(
                confidence=confidence,
                debug_output=False,
                filter_dark_buttons=True,
                brightness_threshold=brightness_threshold,
                extract_skills=True
            )
            
            if 'error' in result:
                debug_print(f"[DEBUG] Error during skill detection: {result['error']}")
                break
            
            current_skills = result.get('skills', [])
            new_skills_found = 0
            
            if not current_skills:
                debug_print("[DEBUG] No skills found on this screen")
                # Don't break here - continue scrolling to find skills
                # Only break if we've tried several empty screens in a row
                if scrolls_performed >= 3 and len(all_skills) == 0:
                    debug_print("[DEBUG] No skills found after 3 scrolls - may not be on skill screen")
                    break
            else:
                # Check for duplicates and add new skills
                for skill in current_skills:
                    skill_name = skill['name']
                    
                    if skill_name in seen_skill_names:
                        debug_print(f"[DEBUG] Duplicate found: '{skill_name}' - end of list reached")
                        duplicate_found = skill_name
                        debug_print("[DEBUG] Stopping scan - we've looped back to already seen skills")
                        break
                    else:
                        seen_skill_names.add(skill_name)
                        all_skills.append(skill)
                        new_skills_found += 1
                        debug_print(f"[DEBUG] {len(all_skills)}. {skill_name} - {skill['price']}")
                
                # Stop if duplicate found
                if duplicate_found:
                    break
            
            debug_print(f"[DEBUG] Found {new_skills_found} new skills (Total: {len(all_skills)})")
            
            # Perform swipe to scroll down
            scrolls_performed += 1
            if scrolls_performed < max_scrolls:
                debug_print("[DEBUG] Scrolling")
                success = perform_swipe(swipe_start_x, swipe_start_y, swipe_end_x, swipe_end_y)
                
                if not success:
                    debug_print("[DEBUG] Failed to perform swipe, stopping scan")
                    break
                
                # Wait for scroll animation to complete
                time.sleep(1.5)
        
        # Summary
        debug_print(f"[DEBUG] " + "=" * 60)
        debug_print(f"[DEBUG] Skill Scan Complete")
        debug_print(f"[DEBUG]    Total unique skills found: {len(all_skills)}")
        debug_print(f"[DEBUG]    Scrolls performed: {scrolls_performed}")
        if duplicate_found:
            debug_print(f"[DEBUG] Stopped due to duplicate: {duplicate_found}")
        elif scrolls_performed >= max_scrolls:
            debug_print(f"[DEBUG] Stopped due to max scroll limit reached")
        else:
            debug_print(f"[DEBUG] Scan completed - reached end of list")
        
        return {
            'all_skills': all_skills,
            'total_unique_skills': len(all_skills),
            'scrolls_performed': scrolls_performed,
            'duplicate_found': duplicate_found
        }
        
    except Exception as e:
        debug_print(f"[DEBUG] Error during skill scanning: {e}")
        return {
            'all_skills': all_skills,
            'total_unique_skills': len(all_skills),
            'scrolls_performed': scrolls_performed,
            'duplicate_found': None,
            'error': str(e)
        }

def test_skill_listing():
    """
    Test function specifically for listing all skills with their prices.
    """
    debug_print("[DEBUG] Testing skill listing with OCR extraction...")
    debug_print("[DEBUG] " + "=" * 70)
    debug_print("[DEBUG] This will detect all available skill_up buttons and extract their names and prices.")
    debug_print("[DEBUG] ")
    
    # Run with skill info extraction enabled
    result = recognize_skill_up_locations(
        confidence=0.9,
        debug_output=True,
        filter_dark_buttons=True,
        brightness_threshold=150,
        extract_skills=True
    )
    
    if 'error' in result:
        debug_print(f"[DEBUG] Error: {result['error']}")
        return
    
    debug_print(f"[DEBUG] Detection Results:")
    debug_print(f"[DEBUG]    Available skill buttons found: {result['count']}")
    debug_print(f"[DEBUG]    Total detected before filtering: {result.get('deduplicated_matches', 'N/A')}")
    
    if result.get('dark_buttons_filtered', 0) > 0:
        debug_print(f"[DEBUG]    Dark buttons filtered out: {result['dark_buttons_filtered']}")
    
    if result.get('skills'):
        debug_print(f"[DEBUG] SKILL INVENTORY:")
        debug_print("[DEBUG] " + "=" * 70)
        
        for i, skill in enumerate(result['skills'], 1):
            x, y, w, h = skill['location']
            debug_print(f"[DEBUG] {i:2d}. {skill['name']:<30} | Price: {skill['price']:<10} | Button: ({x}, {y})")
        
        debug_print("[DEBUG] " + "=" * 70)
        debug_print(f"[DEBUG] Total skills available for purchase: {len(result['skills'])}")
        
        # Extract unique prices for summary
        prices = [skill['price'] for skill in result['skills'] if skill['price'] != 'Unknown Price']
        if prices:
            try:
                numeric_prices = [int(p) for p in prices if p.isdigit()]
                if numeric_prices:
                    debug_print(f"[DEBUG] Price range: {min(numeric_prices)} - {max(numeric_prices)}")
            except:
                pass
    else:
        debug_print(f"[DEBUG] No skills detected or OCR extraction failed")
        if not OCR_AVAILABLE:
            debug_print("[DEBUG]    Note: pytesseract not available for OCR")
        
    if result['debug_image_path']:
        debug_print(f"[DEBUG] Debug image saved: {result['debug_image_path']}")
        debug_print("[DEBUG]    Green boxes = Available buttons, Red boxes = Dark buttons")
    
    debug_print(f"[DEBUG] " + "=" * 70)
    debug_print("[DEBUG] Skill listing test completed!")

if __name__ == "__main__":
    # Run test when script is executed directly
    test_skill_listing()