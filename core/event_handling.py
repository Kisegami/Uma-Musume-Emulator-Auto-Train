import os
import json
import re
import time
from typing import Dict
from PIL import ImageStat

from core.config import Config
from core.templates_adb import EVENT_CHOICE_1_TEMPLATE
from utils.adb_input import tap
from utils.adb_recognizer import locate_all_on_screen, locate_on_screen
from utils.adb_screenshot import take_screenshot, capture_region
from core.ocr import extract_event_name_text

# Load config and check debug mode
config = Config.load()
DEBUG_MODE = config.get("debug_mode", False)

def _safe_load_json(path: str):
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)

_EVENT_JSON_FILES = [
    ("Support Card", "assets/events/support_card.json"),
    ("Uma Data", "assets/events/uma_data.json"),
    ("Ura Finale", "assets/events/ura_finale.json"),
]

def _merge_source_label(existing: str, new_src: str) -> str:
    """Merge human-readable source label without duplicates, e.g., 'Support Card + Uma Data'."""
    if not existing:
        return new_src
    if existing == new_src:
        return existing
    parts = {p.strip() for p in existing.replace("+", ",").split(",")} | {new_src}
    ordered = ["Support Card", "Uma Data", "Ura Finale"]
    final = [p for p in ordered if p in parts] + [p for p in sorted(parts) if p not in ordered]
    return "All Sources" if len(final) == 3 else " + ".join(final)

def _build_event_db() -> Dict[str, Dict]:
    """
    Returns:
      {
        EventName: {
          "source": "Support Card + Uma Data" | "All Sources" | ...,
          "options": { "Top": "...", "Bottom": "...", ... }
        },
        ...
      }
    """
    db: Dict[str, Dict] = {}
    for src_name, path in _EVENT_JSON_FILES:
        data = _safe_load_json(path)
        if data is None:
            continue

        if src_name == "Uma Data":
            # Structure: [ { "UmaEvents": [ {EventName, EventOptions}, ... ] }, ... ]
            for char in data:
                for ev in char.get("UmaEvents", []):
                    name = ev.get("EventName")
                    if not name:
                        continue
                    entry = db.setdefault(name, {"source": "", "options": {}})
                    entry["source"] = _merge_source_label(entry["source"], src_name)
                    entry["options"].update(ev.get("EventOptions", {}) or {})
        else:
            # support_card.json / ura_finale.json: list of events
            for ev in data:
                name = ev.get("EventName")
                if not name:
                    continue
                entry = db.setdefault(name, {"source": "", "options": {}})
                entry["source"] = _merge_source_label(entry["source"], src_name)
                entry["options"].update(ev.get("EventOptions", {}) or {})

    return db

# 2) Build once at import (hot path uses memory only)
EVENT_DB: Dict[str, Dict] = _build_event_db()

def search_events_exact(name: str) -> Dict[str, Dict]:
    """O(1) in-memory exact lookup; returns {} if not found."""
    if not name:
        return {}
    entry = EVENT_DB.get(name)
    return {name: entry} if entry else {}

def debug_print(message):
    """Print debug message only if DEBUG_MODE is enabled"""
    if DEBUG_MODE:
        print(message)

def count_event_choices(screenshot):
    """
    Count how many event choice icons are found on screen.
    Uses event_choice_1.png as template to find all U-shaped icons.
    Filters matches by brightness to avoid dim/false positives.
    Returns:
        tuple: (count, locations) - number of unique bright choices found and their locations
    """
    try:
        debug_print(f"[DEBUG] Searching for event choices using: EVENT_CHOICE_1_TEMPLATE")
        # Search for all instances of the template in the event choice region
        event_choice_region = (6, 450, 126, 1776)
        locations = locate_all_on_screen(screenshot, EVENT_CHOICE_1_TEMPLATE, confidence=0.45, region=event_choice_region)
        debug_print(f"[DEBUG] Raw locations found: {len(locations)}")
        if not locations:
            debug_print("[DEBUG] No event choice locations found")
            return 0, []
        # Sort locations by y, then x (top to bottom, left to right)
        locations = sorted(locations, key=lambda loc: (loc[1], loc[0]))
        unique_locations = []
        for i, location in enumerate(locations):
            x, y, w, h = location
            center = (x + w//2, y + h//2)
            if not unique_locations:
                unique_locations.append(location)
                continue
            # Only compare to the last accepted unique match
            last_x, last_y, last_w, last_h = unique_locations[-1]
            last_center = (last_x + last_w//2, last_y + last_h//2)
            distance = ((center[0] - last_center[0]) ** 2 + (center[1] - last_center[1]) ** 2) ** 0.5
            if distance >= 150:  # Increased from 30 to 150 to separate different choice rows
                unique_locations.append(location)
        # Compute brightness and filter
        screenshot = take_screenshot()
        grayscale = screenshot.convert("L")
        bright_threshold = 160.0
        bright_locations = []
        for (x, y, w, h) in unique_locations:
            try:
                region_img = grayscale.crop((x, y, x + w, y + h))
                avg_brightness = ImageStat.Stat(region_img).mean[0]
                debug_print(f"[DEBUG] Choice at ({x},{y},{w},{h}) brightness: {avg_brightness:.1f}")
                if avg_brightness > bright_threshold:
                    bright_locations.append((x, y, w, h))
            except Exception:
                # If brightness calc fails, skip this location
                continue

        debug_print(f"[DEBUG] Final unique bright locations: {len(bright_locations)} (threshold: {bright_threshold})")
        return len(bright_locations), bright_locations
    except Exception as e:
        print(f"❌ Error counting event choices: {str(e)}")
        return 0, []

def load_event_priorities():
    """Load event priority configuration from event_priority.json"""
    try:
        if os.path.exists("event_priority.json"):
            with open("event_priority.json", "r", encoding="utf-8") as f:
                priorities = json.load(f)
            return priorities
        else:
            print("Warning: event_priority.json not found")
            return {"Good_choices": [], "Bad_choices": []}
    except Exception as e:
        print(f"Error loading event priorities: {e}")
        return {"Good_choices": [], "Bad_choices": []}

def analyze_event_options(options, priorities):
    """
    Analyze event options and recommend the best choice based on priorities.
    
    Args:
        options: Dict of option_name -> option_reward
        priorities: Dict with "Good_choices" and "Bad_choices" lists
    
    Returns:
        Dict with recommendation info:
        {
            "recommended_option": str,
            "recommendation_reason": str,
            "option_analysis": dict,
            "all_options_bad": bool
        }
    """
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
    
    # Check if ALL options have bad choices (regardless of good choices)
    all_options_have_bad = all(analysis["has_bad"] for analysis in option_analysis.values())
    
    # Determine recommendation
    recommended_option = None
    recommendation_reason = ""
    
    if all_options_have_bad:
        # If all options have bad choices, ignore bad choices and pick based on good choice priority
        best_options = []  # Store all options with the same best priority
        best_priority = -1
        
        for option_name, analysis in option_analysis.items():
            # Find the highest priority good choice in this option
            for good_choice in analysis["good_matches"]:
                try:
                    priority = good_choices.index(good_choice)
                    if priority < best_priority or best_priority == -1:
                        # New best priority found, reset the list
                        best_priority = priority
                        best_options = [option_name]
                    elif priority == best_priority:
                        # Same priority, add to the list
                        if option_name not in best_options:
                            best_options.append(option_name)
                except ValueError:
                    continue
        
        if best_options:
            # If we have multiple options with the same priority, use tie-breaking
            if len(best_options) > 1:
                # Since all options have bad choices, ignore bad choices and prefer option with more good choices
                best_option = None
                max_good_choices = -1
                
                for option_name in best_options:
                    good_count = len(option_analysis[option_name]["good_matches"])
                    if good_count > max_good_choices:
                        max_good_choices = good_count
                        best_option = option_name
                
                # If still tied, choose the first option (top choice)
                if best_option is None:
                    best_option = best_options[0]
                
                recommended_option = best_option
                recommendation_reason = f"All options have bad choices. Multiple options have same priority good choice. Selected based on tie-breaking (more good choices, then top choice)."
            else:
                best_option = best_options[0]
                recommended_option = best_option
                recommendation_reason = f"All options have bad choices. Recommended based on highest priority good choice: '{option_analysis[best_option]['good_matches'][0]}'"
        else:
            # No good choices found, pick the option with the least bad choices
            best_option = None
            min_bad_choices = 999
            
            for option_name, analysis in option_analysis.items():
                bad_count = len(analysis["bad_matches"])
                if bad_count < min_bad_choices:
                    min_bad_choices = bad_count
                    best_option = option_name
            
            if best_option:
                recommended_option = best_option
                recommendation_reason = f"All options have bad choices. Selected option with least bad choices: {len(option_analysis[best_option]['bad_matches'])} bad choices"
            else:
                recommendation_reason = "All options have bad choices. No recommendation possible."
    else:
        # Normal case: some options don't have bad choices - avoid bad choices completely
        best_options = []
        best_priority = -1
        
        for option_name, analysis in option_analysis.items():
            # ONLY consider options that have good choices AND NO bad choices
            if analysis["has_good"] and not analysis["has_bad"]:
                # Find the highest priority good choice in this option
                for good_choice in analysis["good_matches"]:
                    try:
                        priority = good_choices.index(good_choice)
                        if priority < best_priority or best_priority == -1:
                            # New best priority found, reset the list
                            best_priority = priority
                            best_options = [option_name]
                        elif priority == best_priority:
                            # Same priority, add to the list
                            if option_name not in best_options:
                                best_options.append(option_name)
                    except ValueError:
                        continue
        
        if best_options:
            # If we have multiple options with the same priority, use tie-breaking
            if len(best_options) > 1:
                # Prefer option with more good choices, then fewer bad choices
                best_option = None
                max_good_choices = -1
                min_bad_choices = 999
                
                for option_name in best_options:
                    good_count = len(option_analysis[option_name]["good_matches"])
                    bad_count = len(option_analysis[option_name]["bad_matches"])
                    
                    if good_count > max_good_choices or (good_count == max_good_choices and bad_count < min_bad_choices):
                        max_good_choices = good_count
                        min_bad_choices = bad_count
                        best_option = option_name
                
                recommended_option = best_option
                recommendation_reason = f"Multiple options have same priority good choice. Selected based on tie-breaking (more good choices, then fewer bad choices)."
            else:
                best_option = best_options[0]
                recommended_option = best_option
                recommendation_reason = f"Recommended based on highest priority good choice: '{option_analysis[best_option]['good_matches'][0]}'"
        else:
            # No clean options (good without bad) found, try options with good choices even if they have bad choices
            debug_print("[DEBUG] No clean options found, considering options with good choices despite bad choices...")
            fallback_options = []
            best_priority = -1
            
            for option_name, analysis in option_analysis.items():
                if analysis["has_good"]:  # Has good choices (ignoring bad choices for now)
                    # Find the highest priority good choice in this option
                    for good_choice in analysis["good_matches"]:
                        try:
                            priority = good_choices.index(good_choice)
                            if priority < best_priority or best_priority == -1:
                                # New best priority found, reset the list
                                best_priority = priority
                                fallback_options = [option_name]
                            elif priority == best_priority:
                                # Same priority, add to the list
                                if option_name not in fallback_options:
                                    fallback_options.append(option_name)
                        except ValueError:
                            continue
            
            if fallback_options:
                # Choose from fallback options, prefer fewer bad choices
                best_option = None
                min_bad_choices = 999
                
                for option_name in fallback_options:
                    bad_count = len(option_analysis[option_name]["bad_matches"])
                    if bad_count < min_bad_choices:
                        min_bad_choices = bad_count
                        best_option = option_name
                
                recommended_option = best_option
                recommendation_reason = f"No clean options available. Selected option with good choices but fewest bad choices: {min_bad_choices} bad choices"
            else:
                # Absolutely no good choices found, pick the option with the least bad choices
                best_option = None
                min_bad_choices = 999
                
                for option_name, analysis in option_analysis.items():
                    bad_count = len(analysis["bad_matches"])
                    if bad_count < min_bad_choices:
                        min_bad_choices = bad_count
                        best_option = option_name
                
                if best_option:
                    recommended_option = best_option
                    recommendation_reason = f"No good choices found. Selected option with least bad choices: {len(option_analysis[best_option]['bad_matches'])} bad choices"
                else:
                    recommendation_reason = "No good choices found. No recommendation possible."
    
    return {
        "recommended_option": recommended_option,
        "recommendation_reason": recommendation_reason,
        "option_analysis": option_analysis,
        "all_options_bad": all_options_bad
    }

def generate_event_variations(event_name):
    """
    Generate variations of an event name for better matching.
    
    Args:
        event_name: The base event name
    
    Returns:
        List of event name variations
    """
    variations = [event_name]
    
    # Add common variations
    if " " in event_name:
        # Split by spaces and create combinations
        parts = event_name.split()
        variations.extend(parts)
        
        # Add combinations of parts
        for i in range(len(parts)):
            for j in range(i + 1, len(parts) + 1):
                combination = " ".join(parts[i:j])
                if combination not in variations:
                    variations.append(combination)
    
    # Add lowercase versions
    variations.append(event_name.lower())
    
    # Add versions without special characters
    clean_name = event_name.replace("(", "").replace(")", "").replace("[", "").replace("]", "")
    if clean_name not in variations:
        variations.append(clean_name)
    
    return variations

# Precompiled once
_RE_KEEP_CHARS = re.compile(r"[^a-z0-9☆\s]")
_RE_REMOVE_SPACES_PUNCT = re.compile(r"[^a-z0-9☆]")

# Option name filter keywords (lowercased)
_VALID_OPTION_KEYWORDS = (
    "top option",
    "bottom option",
    "middle option",
    "option1", "option2", "option3", "option4", "option5",
    "option 1", "option 2", "option 3", "option 4", "option 5",
)

def _normalize_for_match(name: str) -> str:
    n = (name or "").lower()
    # Remove the chain symbols you mentioned
    for token in ("(❯❯❯)", "(❯❯)", "(❯)"):
        n = n.replace(token, "")
    return n.strip()

def _strip_punct_spaces(name: str) -> str:
    # Keep letters, numbers, star, and spaces; drop the rest
    return _RE_KEEP_CHARS.sub("", name)

def _nospace(name: str) -> str:
    # Remove all spaces and punctuation entirely
    return _RE_REMOVE_SPACES_PUNCT.sub("", name)

def _is_match(db_name_raw: str, search_raw: str) -> bool:
    dbn = _normalize_for_match(db_name_raw)
    srch = _normalize_for_match(search_raw)
    if not dbn or not srch:
        return False

    # Guard: ignore trivial variations
    srch_tokens = [t for t in _strip_punct_spaces(srch).split() if t]
    if (len(srch) < 3) or (len(srch_tokens) == 1 and len(srch_tokens[0]) < 3) or (srch.strip() == "☆"):
        return False

    # Exact
    if dbn == srch:
        return True

    # Substring match ignoring punctuation/spaces
    dbn_np = _strip_punct_spaces(dbn).replace("  ", " ").strip()
    srch_np = _strip_punct_spaces(srch).replace("  ", " ").strip()
    if srch_np and (srch_np in dbn_np or dbn_np in srch_np):
        return True

    # Substring match ignoring all spaces/punct
    dbn_ns = _nospace(dbn)
    srch_ns = _nospace(srch)
    if srch_ns and (srch_ns in dbn_ns or dbn_ns in srch_ns):
        return True

    # Token containment (all search tokens in db tokens)
    db_tokens = set([t for t in dbn_np.split() if t])
    srch_tokens_set = set([t for t in srch_np.split() if t])
    if srch_tokens_set and srch_tokens_set.issubset(db_tokens):
        return True

    return False

def _merge_source_label_fallback(existing: str, new_src: str) -> str:
    # Use your global _merge_source_label if defined; otherwise a simple dedup combiner:
    if ' _merge_source_label' in globals() and callable(globals()['_merge_source_label']):  # noqa: E712
        return globals()['_merge_source_label'](existing, new_src)  # type: ignore
    if not existing:
        return new_src
    if existing == new_src:
        return existing
    parts = {p.strip() for p in existing.replace("+", ",").split(",")} | {new_src}
    ordered = ["Support Card", "Uma Data", "Ura Finale"]
    final = [p for p in ordered if p in parts] + [p for p in sorted(parts) if p not in ordered]
    return "All Sources" if len(final) == 3 else " + ".join(final)

def search_events(event_variations):
    """
    Fuzzy search over preloaded EVENT_DB with debug logging.
    Returns { EventName: { "source": str, "options": {...}} }
    """
    found_events = {}
    debug_print("[DEBUG] Starting search_events...")
    if not event_variations:
        debug_print("[DEBUG] No variations provided; returning empty result.")
        return found_events

    debug_print(f"[DEBUG] Variations to search: {event_variations}")

    # Pre-normalize variations once
    variations_norm = [_normalize_for_match(v) for v in event_variations if v]
    debug_print(f"[DEBUG] Normalized variations: {variations_norm}")

    # Iterate in-memory DB
    total_db_events = len(EVENT_DB)
    debug_print(f"[DEBUG] Searching across {total_db_events} preloaded events in memory...")

    match_count = 0
    for db_event_name, db_entry in EVENT_DB.items():
        for v in variations_norm:
            if _is_match(db_event_name, v):
                debug_print(f"[DEBUG] Matched '{v}' → '{db_event_name}'")
                match_count += 1
                # Create or update entry
                event_name_key = db_event_name
                dst = found_events.setdefault(event_name_key, {"source": "", "options": {}})
                dst["source"] = _merge_source_label_fallback(dst["source"], db_entry.get("source", ""))
                # Filter and add valid options
                src_opts = db_entry.get("options", {}) or {}
                for option_name, option_reward in src_opts.items():
                    if not option_name:
                        continue
                    ln = option_name.lower()
                    if any(k in ln for k in _VALID_OPTION_KEYWORDS):
                        dst["options"][option_name] = option_reward
                break  # no need to test other variations once matched

    debug_print(f"[DEBUG] Total matched events: {match_count}")

    if not found_events:
        print("[INFO] No events matched from variations.")
    else:
        print(f"[INFO] Found {len(found_events)} matching event(s).")
        for k, v in found_events.items():
            print(f"  - {k} ({v['source']}), {len(v['options'])} options")

    return found_events

def handle_event_choice(screenshot):
    """
    Main function to handle event detection and choice selection.
    This function should be called when an event is detected.
    
    Returns:
        tuple: (choice_number, success, choice_locations) - choice number, success status, and found locations
    """
    # Define the region for event name detection
    from utils.constants_phone import EVENT_REGION
    event_region = EVENT_REGION
    
    print("Event detected, scan event")
    
    try:
        # Re-validate that this is a choices event before OCR (avoid scanning non-choice dialogs)
        recheck_count, recheck_locations = count_event_choices(screenshot)
        debug_print(f"[DEBUG] Recheck choices after delay: {recheck_count}")
        if recheck_count == 0:
            print("[INFO] Event choices not visible after delay, skipping analysis")
            return 1, False, []

        # Capture the event name
        event_image = capture_region(event_region)
        event_name = extract_event_name_text(event_image)
        event_name = event_name.strip()
        
        if not event_name:
            print("No text detected in event region")
            # Choices were visible and stabilized earlier; provide locations for fallback top-choice click
            return 1, False, recheck_locations
        
        print(f"Event found: {event_name}")

        found_events = search_events_exact(event_name)
        if not found_events:
            # Fallback variations-based search
            event_variations = generate_event_variations(event_name)
            found_events = search_events(event_variations)
        
        # Count event choices on screen
        choices_found, choice_locations = count_event_choices(screenshot)
        
        # Load event priorities
        priorities = load_event_priorities()
        
        if found_events:
            # Event found in database
            event_name_key = list(found_events.keys())[0]
            event_data = found_events[event_name_key]
            options = event_data["options"]
            
            print(f"Source: {event_data['source']}")
            print("Options:")
            
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
                    print(f"  {option_name}: {reward_single_line}{indicator_text}")
                
                # Print recommendation
                print(f"Recommend: {analysis['recommended_option']}")
                
                # Determine which choice to select based on recommendation and choice count
                expected_options = len(options)
                recommended_option = analysis["recommended_option"]
                
                # If no recommendation, default to first choice
                if recommended_option is None:
                    print("No recommendation found, defaulting to first choice")
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
                    print(f"Warning: Recommended choice {choice_number} exceeds available choices ({choices_found})")
                    choice_number = 1  # Fallback to first choice
                
                print(f"Choose choice: {choice_number}")
                return choice_number, True, choice_locations
            else:
                print("No valid options found in database")
                return 1, False, choice_locations
        else:
            # Unknown event
            print("Unknown event - not found in database")
            print(f"Choices found: {choices_found}")
            return 1, False, choice_locations  # Default to first choice for unknown events
    
    except Exception as e:
        print(f"Error during event handling: {e}")
        # If choices are visible, return their locations to allow fallback top-choice click
        try:
            _, fallback_locations = count_event_choices(screenshot)
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
        from utils.adb_input import tap
        
        # Use pre-found locations if provided, otherwise search again
        if choice_locations is None:
            debug_print("[DEBUG] No pre-found locations, searching for event choices...")
            event_choice_region = (6, 450, 126, 1776)
            screenshot = take_screenshot()
            choice_locations = locate_all_on_screen(screenshot, EVENT_CHOICE_1_TEMPLATE, confidence=0.45, region=event_choice_region)
            
            if not choice_locations:
                print("No event choice icons found")
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
            debug_print("[DEBUG] Using pre-found choice locations")
            unique_locations = choice_locations
        
        # Click the specified choice
        if 1 <= choice_number <= len(unique_locations):
            target_location = unique_locations[choice_number - 1]
            x, y, w, h = target_location
            center = (x + w//2, y + h//2)
            
            print(f"Clicking choice {choice_number} at position {center}")
            tap(center[0], center[1])
            return True
        else:
            print(f"Invalid choice number: {choice_number} (available: 1-{len(unique_locations)})")
            return False
    
    except Exception as e:
        print(f"Error clicking event choice: {e}")
        return False

def click(template, confidence=0.8, minSearch=1, text="", region=None):
    """Click on image with retry logic"""
    debug_print(f"[DEBUG] Looking for: {template}")
    for attempt in range(int(minSearch)):
        screenshot = take_screenshot()
        btn = locate_on_screen(screenshot, template, confidence=confidence, region=region)
        if btn:
            if text:
                print(text)
            debug_print(f"[DEBUG] Clicking {template} at position {btn}")
            tap(btn[0], btn[1])
            return True
        if attempt < int(minSearch) - 1:  # Don't sleep on last attempt
            debug_print(f"[DEBUG] Attempt {attempt + 1}: {template} not found")
            time.sleep(0.05)  # Reduced from 0.1 to 0.05
    debug_print(f"[DEBUG] Failed to find {template} after {minSearch} attempts")
    return False