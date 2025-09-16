import os
import json
import re
import time
import sys
import cv2
import numpy as np
from PIL import ImageStat

# Fix Windows console encoding for Unicode support
if os.name == 'nt':  # Windows
    try:
        # Set console to UTF-8 mode
        os.system('chcp 65001 > nul')
        # Also try to set stdout encoding
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass

from utils.recognizer import locate_all_on_screen
from utils.screenshot import take_screenshot, capture_region
from core.ocr import extract_event_name_text
from utils.log import log_debug, log_info, log_warning, log_error
from utils.template_matching import deduplicated_matches

# Load config and check debug mode
with open("config.json", "r", encoding="utf-8") as config_file:
    config = json.load(config_file)
    DEBUG_MODE = config.get("debug_mode", False)

 

def count_event_choices():
    """
    Count how many event choice icons are found on screen.
    Uses event_choice_1.png as template to find all U-shaped icons.
    Filters matches by brightness to avoid dim/false positives.
    Returns:
        tuple: (count, locations) - number of unique bright choices found and their locations
    """
    template_path = "assets/icons/event_choice_1.png"
    
    if not os.path.exists(template_path):
        log_debug(f" Template not found: {template_path}")
        return 0, []
    
    try:
        log_debug(f" Searching for event choices using: {template_path}")
        
        # Take screenshot and convert to OpenCV format
        screenshot = take_screenshot()
        img_cv = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
        
        # Load template
        template = cv2.imread(template_path)
        if template is None:
            log_debug(f" Could not load template: {template_path}")
            return 0, []
        
        # Search in the event choice region (x, y, width, height)
        x, y, w, h = 6, 450, 126, 1776
        roi = img_cv[y:y+h, x:x+w]
        
        # Template matching with same confidence as before
        result = cv2.matchTemplate(roi, template, cv2.TM_CCOEFF_NORMED)
        locations = np.where(result >= 0.45)
        
        # Convert to absolute coordinates
        raw_locations = []
        for pt in zip(*locations[::-1]):
            abs_x, abs_y = pt[0] + x, pt[1] + y
            tw, th = template.shape[1], template.shape[0]
            raw_locations.append((abs_x, abs_y, tw, th))
        
        log_debug(f" Raw locations found: {len(raw_locations)}")
        if not raw_locations:
            log_debug(f" No event choice locations found")
            return 0, []
        
        # Sort locations by y, then x (top to bottom, left to right)
        raw_locations = sorted(raw_locations, key=lambda loc: (loc[1], loc[0]))
        unique_locations = deduplicated_matches(raw_locations, threshold=150)
        
        # Compute brightness and filter
        grayscale = screenshot.convert("L")
        bright_threshold = 160.0
        bright_locations = []
        for (x, y, w, h) in unique_locations:
            try:
                region_img = grayscale.crop((x, y, x + w, y + h))
                avg_brightness = ImageStat.Stat(region_img).mean[0]
                log_debug(f" Choice at ({x},{y},{w},{h}) brightness: {avg_brightness:.1f}")
                if avg_brightness > bright_threshold:
                    bright_locations.append((x, y, w, h))
            except Exception:
                # If brightness calc fails, skip this location
                continue

        log_debug(f" Final unique bright locations: {len(bright_locations)} (threshold: {bright_threshold})")
        return len(bright_locations), bright_locations
    except Exception as e:
        log_info(f"❌ Error counting event choices: {str(e)}")
        return 0, []

def load_event_priorities():
    """Load event priority configuration from event_priority.json"""
    try:
        if os.path.exists("event_priority.json"):
            with open("event_priority.json", "r", encoding="utf-8") as f:
                priorities = json.load(f)
            return priorities
        else:
            log_info(f"Warning: event_priority.json not found")
            return {"Good_choices": [], "Bad_choices": []}
    except Exception as e:
        log_info(f"Error loading event priorities: {e}")
        return {"Good_choices": [], "Bad_choices": []}

def analyze_event_options(options, priorities):
    """Analyze event options and recommend the best choice based on priorities (optimized version)"""
    good_choices = priorities.get("Good_choices", [])
    bad_choices = priorities.get("Bad_choices", [])
    
    option_analysis = {}
    all_options_bad = True
    
    # Analyze each option
    for option_name, option_reward in options.items():
        reward_lower = option_reward.lower()
        
        # Check for good choices
        good_matches = []
        for good_choice in good_choices:
            if good_choice.lower() in reward_lower:
                good_matches.append(good_choice)
        
        # Check for bad choices
        bad_matches = []
        for bad_choice in bad_choices:
            if bad_choice.lower() in reward_lower:
                bad_matches.append(bad_choice)
        
        option_analysis[option_name] = {
            "reward": option_reward,
            "good_matches": good_matches,
            "bad_matches": bad_matches,
            "has_good": len(good_matches) > 0,
            "has_bad": len(bad_matches) > 0
        }
        
        # If any option has good choices, not all options are bad
        if len(good_matches) > 0:
            all_options_bad = False
    
    # Determine recommendation
    recommended_option = None
    recommendation_reason = ""
    
    if all_options_bad:
        # If all options have bad choices, pick based on good choice priority
        best_options = []
        best_priority = -1
        
        for option_name, analysis in option_analysis.items():
            for good_choice in analysis["good_matches"]:
                try:
                    priority = good_choices.index(good_choice)
                    if priority < best_priority or best_priority == -1:
                        best_priority = priority
                        best_options = [option_name]
                    elif priority == best_priority:
                        best_options.append(option_name)
                except ValueError:
                    continue
        
        if best_options:
            recommended_option = best_options[0]
            best_option_analysis = option_analysis[recommended_option]
            recommendation_reason = f"All options have bad choices. Recommended based on highest priority good choice: '{best_option_analysis['good_matches'][0]}'"
    else:
        # Normal case: avoid bad choices completely
        best_options = []
        best_priority = -1
        
        for option_name, analysis in option_analysis.items():
            # Only consider options that have good choices AND NO bad choices
            if analysis["has_good"] and not analysis["has_bad"]:
                for good_choice in analysis["good_matches"]:
                    try:
                        priority = good_choices.index(good_choice)
                        if priority < best_priority or best_priority == -1:
                            best_priority = priority
                            best_options = [option_name]
                        elif priority == best_priority:
                            best_options.append(option_name)
                    except ValueError:
                        continue
        
        if best_options:
            recommended_option = best_options[0]
            best_option_analysis = option_analysis[recommended_option]
            recommendation_reason = f"Recommended based on highest priority good choice: '{best_option_analysis['good_matches'][0]}'"
        else:
            # Fallback: pick option with least bad choices
            best_option = None
            min_bad_choices = 999
            
            for option_name, analysis in option_analysis.items():
                bad_count = len(analysis["bad_matches"])
                if bad_count < min_bad_choices:
                    min_bad_choices = bad_count
                    best_option = option_name
            
            if best_option:
                recommended_option = best_option
                recommendation_reason = f"No clean options available. Selected option with fewest bad choices: {min_bad_choices} bad choices"
    
    return {
        "recommended_option": recommended_option,
        "recommendation_reason": recommendation_reason,
        "option_analysis": option_analysis,
        "all_options_bad": all_options_bad
    }

def search_events_exact(event_name):
    """Search for exact event name match in all databases"""
    results = {}
    # Support Card
    if os.path.exists("assets/events/support_card.json"):
        with open("assets/events/support_card.json", "r", encoding="utf-8-sig") as f:
            for ev in json.load(f):
                if ev.get("EventName") == event_name:
                    entry = results.setdefault(event_name, {"source": "Support Card", "options": {}})
                    # Merge options across duplicate entries of the same event
                    entry["options"].update(ev.get("EventOptions", {}))
    # Uma Data
    if os.path.exists("assets/events/uma_data.json"):
        with open("assets/events/uma_data.json", "r", encoding="utf-8-sig") as f:
            for character in json.load(f):
                for ev in character.get("UmaEvents", []):
                    if ev.get("EventName") == event_name:
                        entry = results.setdefault(event_name, {"source": "Uma Data", "options": {}})
                        # Merge source labels
                        if entry["source"] == "Support Card":
                            entry["source"] = "Both"
                        elif entry["source"].startswith("Support Card +"):
                            entry["source"] = entry["source"].replace("Support Card +", "Both +")
                        entry["options"].update(ev.get("EventOptions", {}))
    # Ura Finale
    if os.path.exists("assets/events/ura_finale.json"):
        with open("assets/events/ura_finale.json", "r", encoding="utf-8-sig") as f:
            for ev in json.load(f):
                if ev.get("EventName") == event_name:
                    entry = results.setdefault(event_name, {"source": "Ura Finale", "options": {}})
                    if entry["source"] == "Support Card":
                        entry["source"] = "Support Card + Ura Finale"
                    elif entry["source"] == "Uma Data":
                        entry["source"] = "Uma Data + Ura Finale"
                    elif entry["source"] == "Both":
                        entry["source"] = "All Sources"
                    entry["options"].update(ev.get("EventOptions", {}))
    return results

def handle_event_choice():
    """
    Main function to handle event detection and choice selection.
    This function should be called when an event is detected.
    
    Returns:
        tuple: (choice_number, success, choice_locations) - choice number, success status, and found locations
    """
    # Define the region for event name detection
    from utils.constants_phone import EVENT_REGION
    event_region = EVENT_REGION
    
    log_info(f"Event detected, scan event")
    
    try:
        # Wait for event to stabilize (1.5 seconds)
        time.sleep(1.5)

        # Re-validate that this is a choices event before OCR (avoid scanning non-choice dialogs)
        recheck_count, recheck_locations = count_event_choices()
        log_debug(f" Recheck choices after delay: {recheck_count}")
        if recheck_count == 0:
            log_info(f"[INFO] Event choices not visible after delay, skipping analysis")
            return 1, False, []

        # Capture the event name
        event_image = capture_region(event_region)
        event_name = extract_event_name_text(event_image)
        event_name = event_name.strip()
        
        if not event_name:
            log_info(f"No text detected in event region")
            # Choices were visible and stabilized earlier; provide locations for fallback top-choice click
            return 1, False, recheck_locations
        
        log_info(f"Event found: {event_name}")

        # Prefer exact name lookup to ensure options align with the specific event instance
        def search_events_exact(name):
            results = {}
            # Support Card
            if os.path.exists("assets/events/support_card.json"):
                with open("assets/events/support_card.json", "r", encoding="utf-8-sig") as f:
                    for ev in json.load(f):
                        if ev.get("EventName") == name:
                            entry = results.setdefault(name, {"source": "Support Card", "options": {}})
                            # Merge options across duplicate entries of the same event
                            entry["options"].update(ev.get("EventOptions", {}))
            # Uma Data
            if os.path.exists("assets/events/uma_data.json"):
                with open("assets/events/uma_data.json", "r", encoding="utf-8-sig") as f:
                    for character in json.load(f):
                        for ev in character.get("UmaEvents", []):
                            if ev.get("EventName") == name:
                                entry = results.setdefault(name, {"source": "Uma Data", "options": {}})
                                # Merge source labels
                                if entry["source"] == "Support Card":
                                    entry["source"] = "Both"
                                elif entry["source"].startswith("Support Card +"):
                                    entry["source"] = entry["source"].replace("Support Card +", "Both +")
                                entry["options"].update(ev.get("EventOptions", {}))
            # Ura Finale
            if os.path.exists("assets/events/ura_finale.json"):
                with open("assets/events/ura_finale.json", "r", encoding="utf-8-sig") as f:
                    for ev in json.load(f):
                        if ev.get("EventName") == name:
                            entry = results.setdefault(name, {"source": "Ura Finale", "options": {}})
                            if entry["source"] == "Support Card":
                                entry["source"] = "Support Card + Ura Finale"
                            elif entry["source"]["source"] == "Uma Data":
                                entry["source"] = "Uma Data + Ura Finale"
                            elif entry["source"] == "Both":
                                entry["source"] = "All Sources"
                            entry["options"].update(ev.get("EventOptions", {}))
            return results

        found_events = search_events_exact(event_name)
        
        # Count event choices on screen
        choices_found, choice_locations = count_event_choices()
        
        # Load event priorities
        priorities = load_event_priorities()
        
        if found_events:
            # Event found in database
            event_name_key = list(found_events.keys())[0]
            event_data = found_events[event_name_key]
            options = event_data["options"]
            
            log_info(f"Source: {event_data['source']}")
            log_info(f"Options:")
            
            if options:
                # Analyze options with priorities
                analysis = analyze_event_options(options, priorities)
                
                for option_name, option_reward in options.items():
                    # Replace all line breaks with ', '
                    reward_single_line = option_reward.replace("\r\n", ", ").replace("\n", ", ").replace("\r", ", ")
                    
                    # Add analysis indicators
                    option_analysis = analysis["option_analysis"][option_name]
                    indicators = []
                    if option_analysis["has_good"]:
                        indicators.append("✅ Good")
                    if option_analysis["has_bad"]:
                        indicators.append("❌ Bad")
                    if option_name == analysis["recommended_option"]:
                        indicators.append("🎯 RECOMMENDED")
                    
                    indicator_text = f" [{', '.join(indicators)}]" if indicators else ""
                    log_info(f"  {option_name}: {reward_single_line}{indicator_text}")
                
                # Print recommendation
                log_info(f"Recommend: {analysis['recommended_option']}")
                
                # Determine which choice to select based on recommendation and choice count
                expected_options = len(options)
                recommended_option = analysis["recommended_option"]
                
                # If no recommendation, default to first choice
                if recommended_option is None:
                    log_info(f"No recommendation found, defaulting to first choice")
                    choice_number = 1
                else:
                    # Map recommended option to choice number
                    choice_number = 1  # Default to first choice
                    
                    if expected_options == 2:
                        if "top" in recommended_option.lower():
                            choice_number = 1
                        elif "bottom" in recommended_option.lower():
                            choice_number = 2
                    elif expected_options == 3:
                        if "top" in recommended_option.lower():
                            choice_number = 1
                        elif "middle" in recommended_option.lower():
                            choice_number = 2
                        elif "bottom" in recommended_option.lower():
                            choice_number = 3
                    elif expected_options >= 4:
                        # For 4+ choices, look for "Option 1", "Option 2", etc.
                        option_match = re.search(r'option\s*(\d+)', recommended_option.lower())
                        if option_match:
                            choice_number = int(option_match.group(1))
                
                # Verify choice number is valid
                if choice_number > choices_found:
                    log_info(f"Warning: Recommended choice {choice_number} exceeds available choices ({choices_found})")
                    choice_number = 1  # Fallback to first choice
                
                log_info(f"Choose choice: {choice_number}")
                return choice_number, True, choice_locations
            else:
                log_info(f"No valid options found in database")
                return 1, False, choice_locations
        else:
            # Unknown event
            log_info(f"Unknown event - not found in database")
            log_info(f"Choices found: {choices_found}")
            return 1, False, choice_locations  # Default to first choice for unknown events
    
    except Exception as e:
        # Handle Unicode characters in error messages gracefully
        try:
            error_msg = str(e)
            log_info(f"Error during event handling: {error_msg}")
        except UnicodeEncodeError:
            # Fallback: print error without problematic characters
            log_info(f"Error during event handling: {repr(e)}")
        
        # If choices are visible, return their locations to allow fallback top-choice click
        try:
            _, fallback_locations = count_event_choices()
        except Exception:
            fallback_locations = []
        return 1, False, fallback_locations  # Default to first choice on error

def click_event_choice(choice_number, choice_locations=None):
    """
    Click on the specified event choice using pre-found locations.
    
    Args:
        choice_number: The choice number to click (1, 2, 3, etc.)
        choice_locations: Pre-found locations from count_event_choices() (optional)
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        from utils.input import tap
        
        # Use pre-found locations if provided, otherwise search again
        if choice_locations is None:
            log_debug(f" No pre-found locations, searching for event choices...")
            event_choice_region = (6, 450, 126, 1776)
            choice_locations = locate_all_on_screen("assets/icons/event_choice_1.png", confidence=0.45, region=event_choice_region)
            
            if not choice_locations:
                log_info(f"No event choice icons found")
                return False
            
            # Filter out duplicates
            unique_locations = []
            for location in choice_locations:
                x, y, w, h = location
                center = (x + w//2, y + h//2)
                is_duplicate = False
                
                for existing in unique_locations:
                    ex, ey, ew, eh = existing
                    existing_center = (ex + ew//2, ey + eh//2)
                    distance = ((center[0] - existing_center[0]) ** 2 + (center[1] - existing_center[1]) ** 2) ** 0.5
                    if distance < 30:  # Within 30 pixels
                        is_duplicate = True
                        break
                
                if not is_duplicate:
                    unique_locations.append(location)
            
            # Sort locations by Y coordinate (top to bottom)
            unique_locations.sort(key=lambda loc: loc[1])
        else:
            log_debug(f" Using pre-found choice locations")
            unique_locations = choice_locations
        
        # Click the specified choice
        if 1 <= choice_number <= len(unique_locations):
            target_location = unique_locations[choice_number - 1]
            x, y, w, h = target_location
            center = (x + w//2, y + h//2)
            
            log_info(f"Clicking choice {choice_number} at position {center}")
            tap(center[0], center[1])
            return True
        else:
            log_info(f"Invalid choice number: {choice_number} (available: 1-{len(unique_locations)})")
            return False
    
    except Exception as e:
        log_info(f"Error clicking event choice: {e}")
        return False