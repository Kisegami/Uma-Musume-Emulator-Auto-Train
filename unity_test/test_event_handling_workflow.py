"""
Time-consuming test for event_handling.py workflow.

This test will:
- Take multiple screenshots on the event choices screen
- Test the complete workflow of handle_event_choice()
- Save screenshots with overlays showing detected regions and choices
- Provide detailed statistics and analysis

Run from project root:
    python -m unity_test.test_event_handling_workflow

Or with custom number of iterations:
    python -m unity_test.test_event_handling_workflow --iterations 20
"""

import os
import sys
import time
from typing import List, Tuple, Dict, Optional
from PIL import Image, ImageDraw, ImageFont

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.log import log_info, log_warning, log_error, log_debug
from utils.screenshot import take_screenshot, capture_region
from utils.constants_unity import EVENT_REGION
from core_unity.event_handling import (
    count_event_choices,
    handle_event_choice,
    search_events_exact,
    search_events_fuzzy,
    analyze_event_options,
    load_event_priorities,
    find_text_on_screen,
)
from core_unity.ocr import extract_event_name_text


# Configuration
DEFAULT_ITERATIONS = 1  # Single test run
SCREENSHOT_DELAY = 0.3  # Delay between screenshots
OUTPUT_DIR = "unity_test/event_handling_test_output"


def save_event_overlay(
    screenshot: Image.Image,
    event_name: str,
    choice_locations: List[Tuple[int, int, int, int]],
    choice_count: int,
    recommended_choice: Optional[int],
    event_found: bool,
    analysis_result: Optional[Dict] = None,
    iteration: int = 0,
    out_path: Optional[str] = None,
):
    """
    Save screenshot with overlays showing:
    - Event region
    - Detected choice locations
    - Event name text
    - Analysis results
    """
    try:
        img = screenshot.convert("RGB").copy()
        draw = ImageDraw.Draw(img)
        
        # Try to use a larger font if available
        try:
            font_large = ImageFont.truetype("arial.ttf", 24)
            font_medium = ImageFont.truetype("arial.ttf", 18)
            font_small = ImageFont.truetype("arial.ttf", 14)
        except:
            try:
                font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)
                font_medium = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 18)
                font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)
            except:
                font_large = ImageFont.load_default()
                font_medium = ImageFont.load_default()
                font_small = ImageFont.load_default()
        
        # Draw event region
        left, top, right, bottom = EVENT_REGION
        draw.rectangle([left, top, right, bottom], outline="cyan", width=3)
        draw.text((left + 3, top + 3), "EVENT_REGION", fill="cyan", font=font_small)
        
        # Draw event name text if available
        if event_name:
            # Draw a background box for text
            text_bbox = draw.textbbox((left, top - 30), event_name, font=font_medium)
            text_bg = [text_bbox[0] - 5, text_bbox[1] - 5, text_bbox[2] + 5, text_bbox[3] + 5]
            draw.rectangle(text_bg, fill="black", outline="cyan", width=2)
            draw.text((left, top - 30), event_name, fill="cyan", font=font_medium)
        
        # Draw choice region (event choice area)
        choice_region = (6, 450, 132, 2226)  # (x, y, width, height) from count_event_choices
        choice_x, choice_y, choice_w, choice_h = choice_region
        draw.rectangle(
            [choice_x, choice_y, choice_x + choice_w, choice_y + choice_h],
            outline="yellow",
            width=2
        )
        draw.text((choice_x + 3, choice_y + 3), "CHOICE_REGION", fill="yellow", font=font_small)
        
        # Draw each detected choice
        for idx, (x, y, w, h) in enumerate(choice_locations, start=1):
            # Color based on whether this is the recommended choice
            if recommended_choice and idx == recommended_choice:
                color = "lime"
                label = f"CHOICE#{idx} (RECOMMENDED)"
            else:
                color = "yellow"
                label = f"CHOICE#{idx}"
            
            center_x = x + w // 2
            center_y = y + h // 2
            
            # Draw bounding box
            draw.rectangle([x, y, x + w, y + h], outline=color, width=3)
            
            # Draw center point
            draw.ellipse([center_x - 5, center_y - 5, center_x + 5, center_y + 5], 
                        fill=color, outline=color)
            
            # Draw label
            draw.text((x + 2, y + 2), label, fill=color, font=font_small)
            draw.text((x + 2, y + 20), f"({center_x},{center_y})", fill=color, font=font_small)
        
        # Draw analysis summary
        summary_y = 50
        summary_lines = [
            f"Iteration: {iteration}",
            f"Event Name: {event_name if event_name else 'NOT DETECTED'}",
            f"Choices Found: {choice_count}",
            f"Event in DB: {'YES' if event_found else 'NO'}",
        ]
        
        if recommended_choice:
            summary_lines.append(f"Recommended Choice: {recommended_choice}")
        
        if analysis_result:
            summary_lines.append(f"Recommendation: {analysis_result.get('recommendation_reason', 'N/A')}")
            if analysis_result.get('all_options_bad'):
                summary_lines.append("⚠️ All options have bad choices")
        
        # Draw summary background
        max_width = max(draw.textbbox((0, 0), line, font=font_small)[2] for line in summary_lines)
        summary_height = len(summary_lines) * 20 + 10
        draw.rectangle(
            [10, summary_y, max_width + 20, summary_y + summary_height],
            fill="black",
            outline="white",
            width=2
        )
        
        # Draw summary text
        for i, line in enumerate(summary_lines):
            draw.text((15, summary_y + 5 + i * 20), line, fill="white", font=font_small)
        
        # Save the image
        if out_path is None:
            os.makedirs(OUTPUT_DIR, exist_ok=True)
            out_path = os.path.join(OUTPUT_DIR, f"event_overlay_{iteration:03d}.png")
        
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        img.save(out_path)
        log_info(f"Saved event overlay to: {out_path}")
        
    except Exception as e:
        log_error(f"Failed to save event overlay: {e}")


def test_event_handling_workflow(iterations: int = DEFAULT_ITERATIONS):
    """
    Test the complete event handling workflow multiple times.
    
    Args:
        iterations: Number of screenshots to take and analyze
    """
    log_info("=" * 70)
    log_info("Event Handling Workflow Test (Single Run)")
    log_info("=" * 70)
    log_info(f"Make sure the event choices screen is visible.")
    log_info(f"Running single test with detailed timing breakdown...\n")
    
    # Statistics
    stats = {
        "total_iterations": 0,
        "successful_detections": 0,
        "failed_detections": 0,
        "events_found_in_db": 0,
        "events_not_found": 0,
        "choice_counts": [],
        "recommended_choices": [],
        "processing_times": [],
        "event_names": [],
    }
    
    # Results for each iteration
    iteration_results = []
    
    for i in range(iterations):
        log_info(f"\n{'='*70}")
        log_info(f"Iteration {i+1}/{iterations}")
        log_info(f"{'='*70}")
        
        iteration_start = time.perf_counter()
        step_times = {}  # Track time for each step
        
        try:
            # Take screenshot
            step_start = time.perf_counter()
            time.sleep(SCREENSHOT_DELAY)
            screenshot = take_screenshot()
            step_times["screenshot"] = (time.perf_counter() - step_start) * 1000
            log_info(f"✓ Screenshot captured ({step_times['screenshot']:.2f}ms)")
            
            # Step 1: Count event choices
            log_info("\n[Step 1] Counting event choices...")
            step_start = time.perf_counter()
            choice_count, choice_locations = count_event_choices()
            step_times["count_choices"] = (time.perf_counter() - step_start) * 1000
            log_info(f"✓ Found {choice_count} event choice(s) ({step_times['count_choices']:.2f}ms)")
            if choice_locations:
                for idx, (x, y, w, h) in enumerate(choice_locations, start=1):
                    center_x = x + w // 2
                    center_y = y + h // 2
                    log_info(f"  Choice {idx}: Center ({center_x}, {center_y}), Box ({x}, {y}, {w}, {h})")
            
            if choice_count == 0:
                log_warning("⚠️  No event choices detected - skipping this iteration")
                stats["failed_detections"] += 1
                iteration_results.append({
                    "iteration": i + 1,
                    "success": False,
                    "reason": "No choices detected",
                    "choice_count": 0,
                    "step_times": step_times,
                })
                continue
            
            # Step 2: Extract event name
            log_info("\n[Step 2] Extracting event name from OCR...")
            step_start = time.perf_counter()
            event_image = capture_region(EVENT_REGION)
            capture_time = (time.perf_counter() - step_start) * 1000
            
            step_start = time.perf_counter()
            event_name = extract_event_name_text(event_image)
            ocr_time = (time.perf_counter() - step_start) * 1000
            event_name = event_name.strip()
            step_times["extract_event_name"] = capture_time + ocr_time
            step_times["capture_region"] = capture_time
            step_times["ocr_extraction"] = ocr_time
            
            if event_name:
                log_info(f"✓ Event name detected: '{event_name}' ({step_times['extract_event_name']:.2f}ms)")
                log_info(f"  - Capture region: {capture_time:.2f}ms")
                log_info(f"  - OCR extraction: {ocr_time:.2f}ms")
                stats["successful_detections"] += 1
                stats["event_names"].append(event_name)
            else:
                log_warning(f"⚠️  Event name not detected via OCR ({step_times['extract_event_name']:.2f}ms)")
                event_name = None
                stats["failed_detections"] += 1
            
            # Step 3: Search for event in database
            log_info("\n[Step 3] Searching for event in database...")
            found_events = {}
            if event_name:
                step_start = time.perf_counter()
                found_events = search_events_exact(event_name)
                exact_search_time = (time.perf_counter() - step_start) * 1000
                step_times["exact_search"] = exact_search_time
                
                if not found_events:
                    log_info(f"  Trying fuzzy search... ({exact_search_time:.2f}ms for exact)")
                    step_start = time.perf_counter()
                    found_events = search_events_fuzzy(event_name)
                    fuzzy_search_time = (time.perf_counter() - step_start) * 1000
                    step_times["fuzzy_search"] = fuzzy_search_time
                    step_times["database_search"] = exact_search_time + fuzzy_search_time
                    log_info(f"  Fuzzy search completed ({fuzzy_search_time:.2f}ms)")
                else:
                    step_times["database_search"] = exact_search_time
                    log_info(f"  Exact search completed ({exact_search_time:.2f}ms)")
            else:
                step_times["database_search"] = 0
                step_times["exact_search"] = 0
                step_times["fuzzy_search"] = 0
            
            if found_events:
                log_info(f"✓ Event found in database (Total: {step_times['database_search']:.2f}ms)")
                event_name_key = list(found_events.keys())[0]
                event_data = found_events[event_name_key]
                log_info(f"  Source: {event_data['source']}")
                log_info(f"  Options: {len(event_data.get('options', {}))}")
                stats["events_found_in_db"] += 1
            else:
                log_warning(f"⚠️  Event not found in database ({step_times['database_search']:.2f}ms)")
                stats["events_not_found"] += 1
            
            # Step 4: Load priorities and analyze options
            log_info("\n[Step 4] Analyzing event options...")
            step_start = time.perf_counter()
            priorities = load_event_priorities()
            load_priorities_time = (time.perf_counter() - step_start) * 1000
            step_times["load_priorities"] = load_priorities_time
            
            analysis_result = None
            recommended_choice = None
            
            if found_events:
                event_name_key = list(found_events.keys())[0]
                event_data = found_events[event_name_key]
                options = event_data.get("options", {})
                
                if options:
                    step_start = time.perf_counter()
                    analysis_result = analyze_event_options(options, priorities)
                    analysis_time = (time.perf_counter() - step_start) * 1000
                    step_times["analyze_options"] = analysis_time
                    step_times["step4_total"] = load_priorities_time + analysis_time
                    
                    recommended_option = analysis_result.get("recommended_option")
                    
                    log_info(f"✓ Analysis complete ({step_times['step4_total']:.2f}ms)")
                    log_info(f"  - Load priorities: {load_priorities_time:.2f}ms")
                    log_info(f"  - Analyze options: {analysis_time:.2f}ms")
                    log_info(f"  Recommended option: {recommended_option}")
                    log_info(f"  Reason: {analysis_result.get('recommendation_reason', 'N/A')}")
                    
                    # Map option to choice number
                    step_start = time.perf_counter()
                    if recommended_option:
                        expected_options = len(options)
                        if expected_options == 2:
                            if "top" in recommended_option.lower():
                                recommended_choice = 1
                            elif "bottom" in recommended_option.lower():
                                recommended_choice = 2
                        elif expected_options == 3:
                            if "top" in recommended_option.lower():
                                recommended_choice = 1
                            elif "middle" in recommended_option.lower():
                                recommended_choice = 2
                            elif "bottom" in recommended_option.lower():
                                recommended_choice = 3
                        else:
                            import re
                            option_match = re.search(r'option\s*(\d+)', recommended_option.lower())
                            if option_match:
                                recommended_choice = int(option_match.group(1))
                        
                        # Validate choice number
                        if recommended_choice and recommended_choice > choice_count:
                            log_warning(f"⚠️  Recommended choice {recommended_choice} exceeds available choices ({choice_count})")
                            recommended_choice = 1
                    step_times["map_choice"] = (time.perf_counter() - step_start) * 1000
                    
                    # Log option details
                    for option_name, option_reward in options.items():
                        option_analysis = analysis_result["option_analysis"].get(option_name, {})
                        indicators = []
                        if option_analysis.get("has_good"):
                            indicators.append("✅ Good")
                        if option_analysis.get("has_bad"):
                            indicators.append("❌ Bad")
                        if option_name == recommended_option:
                            indicators.append("🎯 RECOMMENDED")
                        
                        indicator_text = f" [{', '.join(indicators)}]" if indicators else ""
                        reward_single_line = option_reward.replace("\r\n", ", ").replace("\n", ", ").replace("\r", ", ")
                        log_info(f"  {option_name}: {reward_single_line}{indicator_text}")
                else:
                    step_times["analyze_options"] = 0
                    step_times["step4_total"] = load_priorities_time
            else:
                step_times["analyze_options"] = 0
                step_times["step4_total"] = load_priorities_time
            
            # Step 5: Test full handle_event_choice workflow
            log_info("\n[Step 5] Testing full handle_event_choice() workflow...")
            step_start = time.perf_counter()
            try:
                choice_num, success, locations = handle_event_choice()
                step_times["handle_event_choice"] = (time.perf_counter() - step_start) * 1000
                log_info(f"✓ handle_event_choice() completed ({step_times['handle_event_choice']:.2f}ms)")
                log_info(f"  Choice number: {choice_num}")
                log_info(f"  Success: {success}")
                log_info(f"  Locations found: {len(locations)}")
            except Exception as e:
                step_times["handle_event_choice"] = (time.perf_counter() - step_start) * 1000
                log_error(f"❌ handle_event_choice() failed: {e} ({step_times['handle_event_choice']:.2f}ms)")
                choice_num = None
                success = False
                locations = choice_locations
            
            # Save overlay
            log_info("\n[Saving overlay]...")
            step_start = time.perf_counter()
            save_event_overlay(
                screenshot,
                event_name or "NOT DETECTED",
                choice_locations,
                choice_count,
                recommended_choice or choice_num,
                bool(found_events),
                analysis_result,
                i + 1,
            )
            step_times["save_overlay"] = (time.perf_counter() - step_start) * 1000
            log_info(f"✓ Overlay saved ({step_times['save_overlay']:.2f}ms)")
            
            # Calculate total processing time
            processing_time = (time.perf_counter() - iteration_start) * 1000
            stats["processing_times"].append(processing_time)
            stats["choice_counts"].append(choice_count)
            if recommended_choice:
                stats["recommended_choices"].append(recommended_choice)
            
            # Store iteration result
            iteration_results.append({
                "iteration": i + 1,
                "success": success and event_name is not None,
                "event_name": event_name,
                "choice_count": choice_count,
                "recommended_choice": recommended_choice or choice_num,
                "event_found": bool(found_events),
                "processing_time_ms": processing_time,
                "step_times": step_times,
            })
            
            stats["total_iterations"] += 1
            
            # Print detailed timing breakdown
            log_info(f"\n{'='*70}")
            log_info("TIMING BREAKDOWN")
            log_info(f"{'='*70}")
            log_info(f"Total Time: {processing_time:.2f}ms")
            log_info(f"\nStep-by-step timing:")
            log_info(f"  1. Screenshot capture:        {step_times.get('screenshot', 0):.2f}ms")
            log_info(f"  2. Count event choices:        {step_times.get('count_choices', 0):.2f}ms")
            log_info(f"  3. Extract event name:        {step_times.get('extract_event_name', 0):.2f}ms")
            if 'capture_region' in step_times:
                log_info(f"     - Capture region:          {step_times['capture_region']:.2f}ms")
            if 'ocr_extraction' in step_times:
                log_info(f"     - OCR extraction:         {step_times['ocr_extraction']:.2f}ms")
            log_info(f"  4. Database search:            {step_times.get('database_search', 0):.2f}ms")
            if 'exact_search' in step_times and step_times.get('exact_search', 0) > 0:
                log_info(f"     - Exact search:            {step_times['exact_search']:.2f}ms")
            if 'fuzzy_search' in step_times and step_times.get('fuzzy_search', 0) > 0:
                log_info(f"     - Fuzzy search:            {step_times['fuzzy_search']:.2f}ms")
            log_info(f"  5. Analyze options:            {step_times.get('step4_total', 0):.2f}ms")
            if 'load_priorities' in step_times:
                log_info(f"     - Load priorities:         {step_times['load_priorities']:.2f}ms")
            if 'analyze_options' in step_times:
                log_info(f"     - Analyze options:         {step_times['analyze_options']:.2f}ms")
            if 'map_choice' in step_times:
                log_info(f"     - Map choice number:       {step_times['map_choice']:.2f}ms")
            log_info(f"  6. Full handle_event_choice(): {step_times.get('handle_event_choice', 0):.2f}ms")
            handle_time = step_times.get('handle_event_choice', 0)
            if handle_time > 1500:
                # Most of the time is the intentional 1.5s sleep delay
                actual_processing = handle_time - 1500
                log_info(f"     - Sleep delay (stabilization): ~1500.00ms")
                log_info(f"     - Actual processing:           ~{actual_processing:.2f}ms")
            log_info(f"  7. Save overlay:               {step_times.get('save_overlay', 0):.2f}ms")
            
            # Calculate percentage breakdown
            if processing_time > 0:
                log_info(f"\nTime distribution:")
                for step_name, step_time in step_times.items():
                    if step_time > 0 and step_name not in ['capture_region', 'ocr_extraction', 'exact_search', 'fuzzy_search', 'load_priorities', 'analyze_options', 'map_choice', 'step4_total']:
                        percentage = (step_time / processing_time) * 100
                        log_info(f"  {step_name:25s}: {percentage:5.1f}% ({step_time:.2f}ms)")
                
                # Show actual processing time vs sleep time
                if handle_time > 1500:
                    actual_processing = handle_time - 1500
                    log_info(f"\n  Note: handle_event_choice() includes a 1.5s sleep delay")
                    log_info(f"        Actual processing time: ~{actual_processing:.2f}ms")
                    log_info(f"        Sleep delay: ~1500.00ms (for screen stabilization)")
            
            log_info(f"\n✓ Iteration {i+1} completed in {processing_time:.2f}ms")
            
        except Exception as e:
            log_error(f"❌ Error in iteration {i+1}: {e}")
            import traceback
            log_error(traceback.format_exc())
            stats["failed_detections"] += 1
            iteration_results.append({
                "iteration": i + 1,
                "success": False,
                "reason": str(e),
            })
    
    # Print summary statistics
    log_info("\n\n" + "=" * 70)
    log_info("SUMMARY STATISTICS")
    log_info("=" * 70)
    
    log_info(f"\nTotal Iterations: {stats['total_iterations']}")
    log_info(f"Successful Detections: {stats['successful_detections']}")
    log_info(f"Failed Detections: {stats['failed_detections']}")
    
    if stats["successful_detections"] > 0:
        success_rate = (stats["successful_detections"] / stats["total_iterations"]) * 100
        log_info(f"Success Rate: {success_rate:.1f}%")
    
    log_info(f"\nEvents Found in DB: {stats['events_found_in_db']}")
    log_info(f"Events Not Found: {stats['events_not_found']}")
    
    if stats["choice_counts"]:
        avg_choices = sum(stats["choice_counts"]) / len(stats["choice_counts"])
        min_choices = min(stats["choice_counts"])
        max_choices = max(stats["choice_counts"])
        log_info(f"\nChoice Count Statistics:")
        log_info(f"  Average: {avg_choices:.2f}")
        log_info(f"  Min: {min_choices}")
        log_info(f"  Max: {max_choices}")
    
    if stats["processing_times"]:
        avg_time = sum(stats["processing_times"]) / len(stats["processing_times"])
        min_time = min(stats["processing_times"])
        max_time = max(stats["processing_times"])
        log_info(f"\nProcessing Time Statistics:")
        log_info(f"  Total Time: {avg_time:.2f}ms")
        if len(iteration_results) > 0 and "step_times" in iteration_results[0]:
            # Show detailed step times in summary
            step_times = iteration_results[0]["step_times"]
            log_info(f"\n  Detailed Step Times:")
            log_info(f"    Screenshot:        {step_times.get('screenshot', 0):.2f}ms")
            log_info(f"    Count choices:     {step_times.get('count_choices', 0):.2f}ms")
            log_info(f"    Extract name:      {step_times.get('extract_event_name', 0):.2f}ms")
            log_info(f"    Database search:   {step_times.get('database_search', 0):.2f}ms")
            log_info(f"    Analyze options:   {step_times.get('step4_total', 0):.2f}ms")
            log_info(f"    handle_event():    {step_times.get('handle_event_choice', 0):.2f}ms")
            log_info(f"    Save overlay:      {step_times.get('save_overlay', 0):.2f}ms")
        else:
            log_info(f"  Min: {min_time:.2f}ms")
            log_info(f"  Max: {max_time:.2f}ms")
    
    if stats["event_names"]:
        log_info(f"\nUnique Event Names Detected ({len(set(stats['event_names']))}):")
        unique_names = list(set(stats["event_names"]))
        for name in unique_names[:10]:  # Show first 10
            count = stats["event_names"].count(name)
            log_info(f"  '{name}' ({count} times)")
        if len(unique_names) > 10:
            log_info(f"  ... and {len(unique_names) - 10} more")
    
    log_info(f"\n✓ All screenshots saved to: {OUTPUT_DIR}")
    log_info("=" * 70)
    
    return stats, iteration_results


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test event handling workflow")
    parser.add_argument(
        "--iterations",
        "-i",
        type=int,
        default=DEFAULT_ITERATIONS,
        help=f"Number of iterations (default: {DEFAULT_ITERATIONS}, use 1 for single test)",
    )
    
    args = parser.parse_args()
    
    try:
        stats, results = test_event_handling_workflow(iterations=args.iterations)
        
        # Return exit code based on success rate
        if stats["total_iterations"] > 0:
            success_rate = (stats["successful_detections"] / stats["total_iterations"]) * 100
            if success_rate >= 50:
                log_info("\n✓ Test completed successfully")
                return 0
            else:
                log_warning("\n⚠️  Test completed with low success rate")
                return 1
        else:
            log_error("\n❌ No iterations completed")
            return 1
            
    except KeyboardInterrupt:
        log_info("\n\nTest interrupted by user")
        return 130
    except Exception as e:
        log_error(f"\n❌ Test failed with error: {e}")
        import traceback
        log_error(traceback.format_exc())
        return 1


if __name__ == "__main__":
    sys.exit(main())

