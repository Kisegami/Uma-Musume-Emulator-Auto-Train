"""
Test event recognition for support_card.json compatibility.

This test verifies that:
1. The support_card.json file can be loaded correctly
2. Event recognition functions work with the new data
3. Exact and fuzzy matching work properly
4. Event options are correctly parsed

Run this test:
    python -m unity_test.test_event_recognition

Or with a screenshot (if event screen is visible):
    python -m unity_test.test_event_recognition --screenshot

Or run the full event recognition flow (requires event screen visible):
    python -m unity_test.test_event_recognition --full
    python -m unity_test.test_event_recognition -f
"""

import os
import sys
import json
from typing import Dict, List, Optional

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.log import log_info, log_warning, log_error, log_debug
from utils.screenshot import capture_region
from utils.constants_unity import EVENT_REGION
from core_unity.event_handling import (
    _load_event_databases,
    search_events_exact,
    search_events_fuzzy,
    analyze_event_options,
    load_event_priorities,
    count_event_choices,
)
from core_unity.ocr import extract_event_name_text


def test_load_support_card_json() -> bool:
    """Test that support_card.json can be loaded and has valid structure."""
    log_info("\n=== TEST 1: Loading support_card.json ===")
    
    file_path = "assets/events/support_card.json"
    if not os.path.exists(file_path):
        log_error(f"❌ File not found: {file_path}")
        return False
    
    try:
        with open(file_path, "r", encoding="utf-8-sig") as f:
            data = json.load(f)
        
        if not isinstance(data, list):
            log_error(f"❌ Expected list, got {type(data)}")
            return False
        
        log_info(f"✅ File loaded successfully: {len(data)} events found")
        
        # Validate structure
        valid_count = 0
        invalid_count = 0
        event_names = set()
        card_slugs = set()
        
        for i, event in enumerate(data):
            if not isinstance(event, dict):
                log_warning(f"⚠️  Event {i} is not a dict: {type(event)}")
                invalid_count += 1
                continue
            
            event_name = event.get("EventName", "")
            event_options = event.get("EventOptions", {})
            card_slug = event.get("CardSlug", "")
            
            if not event_name:
                log_warning(f"⚠️  Event {i} missing EventName")
                invalid_count += 1
                continue
            
            if not isinstance(event_options, dict):
                log_warning(f"⚠️  Event {i} EventOptions is not a dict")
                invalid_count += 1
                continue
            
            event_names.add(event_name)
            if card_slug:
                card_slugs.add(card_slug)
            valid_count += 1
        
        log_info(f"✅ Valid events: {valid_count}")
        log_info(f"⚠️  Invalid events: {invalid_count}")
        log_info(f"📊 Unique event names: {len(event_names)}")
        log_info(f"📊 Unique card slugs: {len(card_slugs)}")
        
        # Show sample event names
        sample_names = list(event_names)[:10]
        log_info(f"📝 Sample event names (first 10):")
        for name in sample_names:
            log_info(f"   - {name}")
        
        return valid_count > 0
        
    except json.JSONDecodeError as e:
        log_error(f"❌ JSON decode error: {e}")
        return False
    except Exception as e:
        log_error(f"❌ Error loading file: {e}")
        return False


def test_event_database_cache() -> bool:
    """Test that the event database cache loads support_card.json correctly."""
    log_info("\n=== TEST 2: Event Database Cache ===")
    
    try:
        cache = _load_event_databases()
        
        if cache["support_card"] is None:
            log_error("❌ support_card cache is None")
            return False
        
        if not isinstance(cache["support_card"], list):
            log_error(f"❌ support_card cache is not a list: {type(cache['support_card'])}")
            return False
        
        log_info(f"✅ support_card cache loaded: {len(cache['support_card'])} events")
        
        # Test cache persistence (should not reload)
        cache2 = _load_event_databases()
        if cache["support_card"] is not cache2["support_card"]:
            log_warning("⚠️  Cache was reloaded (should be same object)")
        else:
            log_info("✅ Cache persistence working correctly")
        
        return True
        
    except Exception as e:
        log_error(f"❌ Error testing cache: {e}")
        return False


def test_exact_matching() -> bool:
    """Test exact event name matching."""
    log_info("\n=== TEST 3: Exact Event Matching ===")
    
    # Get some sample event names from the database
    cache = _load_event_databases()
    if not cache["support_card"]:
        log_error("❌ No support_card events loaded")
        return False
    
    # Collect unique event names
    test_names = []
    seen = set()
    for event in cache["support_card"][:20]:  # Test first 20 events
        name = event.get("EventName", "")
        if name and name not in seen:
            test_names.append(name)
            seen.add(name)
    
    if not test_names:
        log_error("❌ No event names found to test")
        return False
    
    log_info(f"Testing {len(test_names)} event names...")
    
    success_count = 0
    for event_name in test_names:
        results = search_events_exact(event_name)
        
        if event_name in results:
            result = results[event_name]
            source = result.get("source", "")
            options = result.get("options", {})
            
            if source == "Support Card" and options:
                log_debug(f"✅ '{event_name}' -> {len(options)} options")
                success_count += 1
            else:
                log_warning(f"⚠️  '{event_name}' -> source={source}, options={len(options)}")
        else:
            log_warning(f"⚠️  '{event_name}' -> NOT FOUND")
    
    log_info(f"✅ Exact matches: {success_count}/{len(test_names)}")
    return success_count > 0


def test_fuzzy_matching() -> bool:
    """Test fuzzy event name matching."""
    log_info("\n=== TEST 4: Fuzzy Event Matching ===")
    
    cache = _load_event_databases()
    if not cache["support_card"]:
        log_error("❌ No support_card events loaded")
        return False
    
    # Test cases: partial names that should match
    test_cases = [
        ("Mummy Hunt", "Mummy Hunt! Drop the Jokes!"),  # Should match
        ("Tamamo", "Tamamo's School Tour"),  # Should match
        ("Battle", "A Battle I Can't Lose!"),  # Should match
        ("Bookworm", "The Bookworm and the Secret Meeting"),  # Should match
    ]
    
    # Get actual event names from database
    actual_names = []
    for event in cache["support_card"][:50]:
        name = event.get("EventName", "")
        if name:
            actual_names.append(name)
    
    # Create test cases from actual data
    if actual_names:
        # Test with first word of event names
        for name in actual_names[:10]:
            first_word = name.split()[0] if name.split() else name
            # Remove special characters
            first_word = first_word.replace("(", "").replace(")", "").replace("❯", "").strip()
            if first_word and len(first_word) >= 3:
                test_cases.append((first_word, name))
    
    log_info(f"Testing {len(test_cases)} fuzzy match cases...")
    
    success_count = 0
    for partial_name, expected_full_name in test_cases:
        results = search_events_fuzzy(partial_name)
        
        if results:
            # Check if expected name is in results
            found = False
            for result_name in results.keys():
                if expected_full_name in result_name or result_name in expected_full_name:
                    found = True
                    log_debug(f"✅ '{partial_name}' -> matched '{result_name}'")
                    success_count += 1
                    break
            
            if not found:
                # Show what was actually found
                found_names = list(results.keys())[:3]
                log_debug(f"⚠️  '{partial_name}' -> found {found_names} (expected: {expected_full_name})")
        else:
            log_debug(f"⚠️  '{partial_name}' -> NO MATCHES")
    
    log_info(f"✅ Fuzzy matches: {success_count}/{len(test_cases)}")
    return success_count > 0


def test_event_options_parsing() -> bool:
    """Test that event options are correctly parsed."""
    log_info("\n=== TEST 5: Event Options Parsing ===")
    
    cache = _load_event_databases()
    if not cache["support_card"]:
        log_error("❌ No support_card events loaded")
        return False
    
    # Find events with multiple options
    events_with_options = []
    for event in cache["support_card"]:
        options = event.get("EventOptions", {})
        if len(options) > 0:
            events_with_options.append((event.get("EventName", ""), options))
            if len(events_with_options) >= 10:
                break
    
    if not events_with_options:
        log_error("❌ No events with options found")
        return False
    
    log_info(f"Testing {len(events_with_options)} events with options...")
    
    success_count = 0
    for event_name, options in events_with_options:
        if not options:
            continue
        
        # Test analyze_event_options
        priorities = load_event_priorities()
        analysis = analyze_event_options(options, priorities)
        
        if analysis and "option_analysis" in analysis:
            log_debug(f"✅ '{event_name}' -> {len(options)} options analyzed")
            success_count += 1
            
            # Show option details
            for opt_name, opt_reward in options.items():
                opt_analysis = analysis["option_analysis"].get(opt_name, {})
                has_good = opt_analysis.get("has_good", False)
                has_bad = opt_analysis.get("has_bad", False)
                indicators = []
                if has_good:
                    indicators.append("✅")
                if has_bad:
                    indicators.append("❌")
                indicator = " ".join(indicators) if indicators else ""
                log_debug(f"   {opt_name}: {indicator}")
        else:
            log_warning(f"⚠️  '{event_name}' -> analysis failed")
    
    log_info(f"✅ Options parsed: {success_count}/{len(events_with_options)}")
    return success_count > 0


def test_ocr_extraction(screenshot_available: bool = False) -> bool:
    """Test OCR extraction from screenshot (if available)."""
    log_info("\n=== TEST 6: OCR Event Name Extraction ===")
    
    if not screenshot_available:
        log_info("⏭️  Skipping OCR test (no screenshot provided)")
        log_info("   To test OCR, run with --screenshot flag when event screen is visible")
        return True
    
    try:
        from utils.screenshot import take_screenshot
        
        log_info("Taking screenshot...")
        screenshot = take_screenshot()
        
        log_info("Extracting event name from EVENT_REGION...")
        event_image = capture_region(EVENT_REGION)
        event_name = extract_event_name_text(event_image)
        
        if event_name:
            log_info(f"✅ OCR extracted: '{event_name}'")
            
            # Try to match it
            exact_results = search_events_exact(event_name)
            if not exact_results:
                fuzzy_results = search_events_fuzzy(event_name)
                if fuzzy_results:
                    log_info(f"✅ Fuzzy match found: {list(fuzzy_results.keys())[0]}")
                    return True
                else:
                    log_warning(f"⚠️  No matches found for: '{event_name}'")
                    return False
            else:
                log_info(f"✅ Exact match found: {list(exact_results.keys())[0]}")
                return True
        else:
            log_warning("⚠️  No event name extracted from OCR")
            log_info("   This is normal if no event screen is currently visible")
            return True  # Not a failure, just no event visible
        
    except Exception as e:
        log_error(f"❌ OCR test error: {e}")
        return False


def test_event_structure_compatibility() -> bool:
    """Test that the event structure is compatible with the bot's expectations."""
    log_info("\n=== TEST 7: Event Structure Compatibility ===")
    
    cache = _load_event_databases()
    if not cache["support_card"]:
        log_error("❌ No support_card events loaded")
        return False
    
    required_fields = ["EventName", "EventOptions"]
    optional_fields = ["CardSlug"]
    
    issues = []
    checked = 0
    
    for i, event in enumerate(cache["support_card"][:100]):  # Check first 100
        checked += 1
        
        # Check required fields
        for field in required_fields:
            if field not in event:
                issues.append(f"Event {i}: missing required field '{field}'")
            elif not event[field]:
                issues.append(f"Event {i}: empty required field '{field}'")
        
        # Check EventOptions structure
        options = event.get("EventOptions", {})
        if not isinstance(options, dict):
            issues.append(f"Event {i}: EventOptions is not a dict")
        elif options:
            # Check that option values are strings
            for opt_name, opt_value in options.items():
                if not isinstance(opt_value, str):
                    issues.append(f"Event {i}: option '{opt_name}' value is not a string")
    
    if issues:
        log_error(f"❌ Found {len(issues)} compatibility issues:")
        for issue in issues[:10]:  # Show first 10
            log_error(f"   - {issue}")
        if len(issues) > 10:
            log_error(f"   ... and {len(issues) - 10} more")
        return False
    else:
        log_info(f"✅ All {checked} events have compatible structure")
        return True


def test_full_event_recognition_flow() -> bool:
    """
    Test the full event recognition flow from screenshot to recommendation.
    This simulates what the bot does when handling an event.
    """
    log_info("\n=== TEST: Full Event Recognition Flow ===")
    log_info("This test will:")
    log_info("  1. Take a screenshot")
    log_info("  2. Extract event name using OCR")
    log_info("  3. Search for event in database")
    log_info("  4. Count event choices on screen")
    log_info("  5. Analyze options and show recommendation")
    
    try:
        from utils.screenshot import take_screenshot
        import time
        
        log_info("\n📸 Taking screenshot...")
        screenshot = take_screenshot()
        log_info("✅ Screenshot captured")
        
        # Wait a bit for screen to stabilize
        log_info("⏳ Waiting for screen to stabilize...")
        time.sleep(0.5)
        
        # Check if event choices are visible
        log_info("\n🔍 Checking for event choices on screen...")
        choices_count, choice_locations = count_event_choices()
        log_info(f"   Found {choices_count} event choice(s)")
        
        if choices_count == 0:
            log_warning("⚠️  No event choices detected on screen")
            log_info("   Make sure an event screen with choices is visible")
            log_info("   Saving screenshot for debugging...")
            debug_path = "unity_test/debug_event_screenshot.png"
            screenshot.save(debug_path)
            log_info(f"   Screenshot saved to: {debug_path}")
            return False
        
        # Extract event name from EVENT_REGION
        log_info("\n📝 Extracting event name from OCR...")
        event_image = capture_region(EVENT_REGION)
        event_name = extract_event_name_text(event_image)
        event_name = event_name.strip()
        
        if not event_name:
            log_error("❌ Failed to extract event name from OCR")
            log_info("   Saving debug images...")
            debug_event_path = "unity_test/debug_event_region.png"
            event_image.save(debug_event_path)
            log_info(f"   Event region saved to: {debug_event_path}")
            debug_screenshot_path = "unity_test/debug_event_screenshot.png"
            screenshot.save(debug_screenshot_path)
            log_info(f"   Full screenshot saved to: {debug_screenshot_path}")
            return False
        
        log_info(f"✅ Event name extracted: '{event_name}'")
        
        # Search for event in database
        log_info("\n🔎 Searching for event in database...")
        found_events = search_events_exact(event_name)
        match_type = "exact"
        
        if not found_events:
            log_info("   Exact match not found, trying fuzzy search...")
            found_events = search_events_fuzzy(event_name)
            match_type = "fuzzy"
        
        if not found_events:
            log_warning(f"⚠️  Event '{event_name}' not found in database")
            log_info(f"   Choices found on screen: {choices_count}")
            log_info("   The bot would default to first choice")
            return False
        
        # Get event data
        event_name_key = list(found_events.keys())[0]
        event_data = found_events[event_name_key]
        options = event_data["options"]
        source = event_data["source"]
        
        log_info(f"✅ Event found in database ({match_type} match)")
        log_info(f"   Database name: '{event_name_key}'")
        log_info(f"   Source: {source}")
        log_info(f"   Options available: {len(options)}")
        
        # Load priorities and analyze options
        log_info("\n📊 Analyzing event options...")
        priorities = load_event_priorities()
        analysis = analyze_event_options(options, priorities)
        
        # Display all options with analysis
        log_info("\n" + "=" * 60)
        log_info("EVENT CHOICES:")
        log_info("=" * 60)
        
        for i, (option_name, option_reward) in enumerate(options.items(), 1):
            # Format reward text
            reward_single_line = option_reward.replace("\r\n", ", ").replace("\n", ", ").replace("\r", ", ")
            
            # Get analysis for this option
            option_analysis = analysis["option_analysis"].get(option_name, {})
            has_good = option_analysis.get("has_good", False)
            has_bad = option_analysis.get("has_bad", False)
            good_matches = option_analysis.get("good_matches", [])
            bad_matches = option_analysis.get("bad_matches", [])
            
            # Build indicator text
            indicators = []
            if has_good:
                indicators.append("✅ Good")
            if has_bad:
                indicators.append("❌ Bad")
            if option_name == analysis["recommended_option"]:
                indicators.append("🎯 RECOMMENDED")
            
            indicator_text = f" [{', '.join(indicators)}]" if indicators else ""
            
            log_info(f"\nChoice {i}: {option_name}{indicator_text}")
            log_info(f"  Reward: {reward_single_line}")
            
            if good_matches:
                log_info(f"  ✅ Good matches: {', '.join(good_matches)}")
            if bad_matches:
                log_info(f"  ❌ Bad matches: {', '.join(bad_matches)}")
        
        # Show recommendation
        log_info("\n" + "=" * 60)
        log_info("RECOMMENDATION:")
        log_info("=" * 60)
        
        recommended_option = analysis["recommended_option"]
        recommendation_reason = analysis.get("recommendation_reason", "")
        
        if recommended_option:
            # Map to choice number
            choice_number = 1
            if len(options) == 2:
                if "top" in recommended_option.lower():
                    choice_number = 1
                elif "bottom" in recommended_option.lower():
                    choice_number = 2
            elif len(options) == 3:
                if "top" in recommended_option.lower():
                    choice_number = 1
                elif "middle" in recommended_option.lower():
                    choice_number = 2
                elif "bottom" in recommended_option.lower():
                    choice_number = 3
            
            # Verify choice number is valid
            if choice_number > choices_count:
                log_warning(f"⚠️  Recommended choice {choice_number} exceeds available choices ({choices_count})")
                choice_number = 1
            
            log_info(f"🎯 Recommended Option: {recommended_option}")
            log_info(f"   Choice Number: {choice_number}")
            log_info(f"   Reason: {recommendation_reason}")
        else:
            log_warning("⚠️  No recommendation found")
            log_info("   The bot would default to first choice")
            choice_number = 1
        
        log_info(f"\n📋 Summary:")
        log_info(f"   Event: {event_name_key}")
        log_info(f"   Choices on screen: {choices_count}")
        log_info(f"   Options in database: {len(options)}")
        log_info(f"   Recommended choice: {choice_number}")
        log_info(f"   Match type: {match_type}")
        
        log_info("\n✅ Full event recognition flow completed successfully!")
        return True
        
    except Exception as e:
        log_error(f"❌ Error in full event recognition flow: {e}")
        import traceback
        log_debug(traceback.format_exc())
        return False


def main():
    """Run all event recognition tests."""
    log_info("=" * 60)
    log_info("Event Recognition Test Suite")
    log_info("=" * 60)
    
    # Check for screenshot flag
    use_screenshot = "--screenshot" in sys.argv or "-s" in sys.argv
    full_flow = "--full" in sys.argv or "-f" in sys.argv
    
    if full_flow:
        # Run only the full flow test
        log_info("Running FULL EVENT RECOGNITION FLOW test")
        log_info("Make sure an event screen with choices is visible!")
        log_info("")
        result = test_full_event_recognition_flow()
        return 0 if result else 1
    
    if use_screenshot:
        log_info("Screenshot mode: Will test OCR if event screen is visible")
    else:
        log_info("No screenshot mode: OCR test will be skipped")
        log_info("(Use --screenshot flag to enable OCR testing)")
        log_info("(Use --full flag to run full event recognition flow)")
    
    results = []
    
    # Run all tests
    results.append(("Load JSON", test_load_support_card_json()))
    results.append(("Database Cache", test_event_database_cache()))
    results.append(("Exact Matching", test_exact_matching()))
    results.append(("Fuzzy Matching", test_fuzzy_matching()))
    results.append(("Options Parsing", test_event_options_parsing()))
    results.append(("Structure Compatibility", test_event_structure_compatibility()))
    results.append(("OCR Extraction", test_ocr_extraction(use_screenshot)))
    
    # Summary
    log_info("\n" + "=" * 60)
    log_info("Test Summary")
    log_info("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        log_info(f"{status}: {test_name}")
    
    log_info("=" * 60)
    log_info(f"Results: {passed}/{total} tests passed")
    
    if passed == total:
        log_info("✅ All tests passed! The bot is compatible with support_card.json")
        return 0
    else:
        log_warning(f"⚠️  {total - passed} test(s) failed. Please review the issues above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())

