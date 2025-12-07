"""
Demonstration test for failure check timing breakdown.

This test shows how long each failure check takes and what operations are involved:
1. Screenshot capture (if needed)
2. Region cropping
3. OCR processing
4. Text extraction and parsing

Run from project root:
    python -m unity_test.test_failure_check_timing
"""

import os
import sys
import time

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.log import log_info, log_warning, log_error, log_debug
from utils.screenshot import take_screenshot, capture_region
from utils.input import swipe
from utils.constants_unity import (
    FAILURE_REGION_SPD,
    FAILURE_REGION_STA,
    FAILURE_REGION_PWR,
    FAILURE_REGION_GUTS,
    FAILURE_REGION_WIT,
)
from core_unity.training_handling import check_failure, go_to_training


def test_failure_check_timing():
    """Test failure check timing for each training type"""
    
    log_info("=" * 70)
    log_info("Failure Check Timing Demonstration")
    log_info("=" * 70)
    log_info("\nThis test demonstrates the timing breakdown of failure check operations.")
    log_info("Make sure you're on the training screen with failure % visible.\n")
    
    # Training types and their regions
    training_types = {
        "spd": FAILURE_REGION_SPD,
        "sta": FAILURE_REGION_STA,
        "pwr": FAILURE_REGION_PWR,
        "guts": FAILURE_REGION_GUTS,
        "wit": FAILURE_REGION_WIT,
    }
    
    log_info("Taking initial screenshot...")
    screenshot_start = time.perf_counter()
    screenshot = take_screenshot()
    screenshot_time = (time.perf_counter() - screenshot_start) * 1000
    log_info(f"Screenshot captured: {screenshot_time:.2f}ms\n")
    
    results = {}
    
    for train_type, region in training_types.items():
        log_info("=" * 70)
        log_info(f"Testing {train_type.upper()} Failure Check")
        log_info("=" * 70)
        log_info(f"Region: {region}")
        
        # Test 1: Region cropping time
        step_start = time.perf_counter()
        left, top, right, bottom = region
        cropped = screenshot.crop((left, top, right, bottom))
        crop_time = (time.perf_counter() - step_start) * 1000
        log_info(f"  Region crop: {crop_time:.2f}ms")
        
        # Test 2: Full check_failure call with detailed breakdown
        log_info(f"  Running check_failure()...")
        step_start = time.perf_counter()
        try:
            # Note: check_failure may take multiple screenshots and retries
            # The timing includes all retries and OCR attempts
            rate, confidence = check_failure(screenshot, train_type)
            check_time = (time.perf_counter() - step_start) * 1000
            results[train_type] = {
                "rate": rate,
                "confidence": confidence,
                "time": check_time,
                "crop_time": crop_time
            }
            log_info(f"  check_failure(): {check_time:.2f}ms")
            log_info(f"  Result: {rate}% (confidence: {confidence:.2f})")
            
            # Breakdown estimate (based on typical OCR timing)
            # OCR typically takes 50-150ms per attempt
            # check_failure tries up to 6 times (3 white + 3 yellow)
            # So typical time is 100-300ms if successful on first attempt
            # Up to 600-900ms if it needs retries
            if check_time > 500:
                log_info(f"  ⚠️  Slow check - likely needed multiple OCR retries")
            elif check_time < 200:
                log_info(f"  ✓ Fast check - likely succeeded on first OCR attempt")
        except Exception as e:
            log_error(f"  check_failure() failed: {e}")
            results[train_type] = {
                "rate": None,
                "confidence": None,
                "time": 0,
                "crop_time": crop_time,
                "error": str(e)
            }
        
        log_info("")
    
    # Summary
    log_info("=" * 70)
    log_info("TIMING SUMMARY")
    log_info("=" * 70)
    
    total_time = sum(r.get("time", 0) for r in results.values())
    total_crop = sum(r.get("crop_time", 0) for r in results.values())
    
    log_info(f"\nPer-training-type timing:")
    for train_type, data in results.items():
        check_time = data.get("time", 0)
        crop_time = data.get("crop_time", 0)
        rate = data.get("rate", "N/A")
        conf = data.get("confidence", "N/A")
        
        if "error" in data:
            log_info(f"  {train_type.upper()}: ERROR - {data['error']}")
        else:
            log_info(f"  {train_type.upper()}: {check_time:6.2f}ms (crop: {crop_time:.2f}ms) - {rate}% (conf: {conf:.2f})")
    
    log_info(f"\nTotal time for all 5 checks: {total_time:.2f}ms")
    log_info(f"Average time per check: {total_time / len(results):.2f}ms")
    log_info(f"Total crop time: {total_crop:.2f}ms")
    
    # Breakdown analysis
    if total_time > 0:
        log_info(f"\nTime distribution:")
        for train_type, data in results.items():
            check_time = data.get("time", 0)
            if check_time > 0:
                percentage = (check_time / total_time) * 100
                log_info(f"  {train_type.upper()}: {percentage:5.1f}% ({check_time:.2f}ms)")
    
    # Compare with screenshot time
    log_info(f"\nScreenshot vs Failure Checks:")
    log_info(f"  Screenshot capture: {screenshot_time:.2f}ms")
    log_info(f"  All failure checks: {total_time:.2f}ms")
    if screenshot_time > 0:
        ratio = total_time / screenshot_time
        log_info(f"  Ratio: {ratio:.2f}x (failure checks take {ratio:.1f}x longer than screenshot)")
    
    log_info(f"\n💡 Failure Check Breakdown:")
    log_info(f"  Each check_failure() call:")
    log_info(f"    - Crops region from screenshot: ~{total_crop/len(results):.2f}ms")
    log_info(f"    - Image processing (mask/enhance): ~10-20ms")
    log_info(f"    - OCR (per attempt): ~50-150ms")
    log_info(f"    - Pattern matching: <1ms")
    log_info(f"    - Retries (if needed): +100ms per retry + 0.1s sleep")
    log_info(f"  Total: Typically 100-300ms if successful, up to 600-900ms with retries")
    log_info(f"  For 5 training types: ~{total_time:.0f}ms total")
    
    log_info("=" * 70)
    
    return results


def test_single_stat_failure_check(train_type: str):
    """
    Test failure check for a single training type.
    This function:
    1. Goes to training screen
    2. Hovers over the specific training type
    3. Takes screenshot
    4. Checks failure rate
    5. Shows detailed timing breakdown
    
    Args:
        train_type: One of 'spd', 'sta', 'pwr', 'guts', 'wit'
    """
    train_type = train_type.lower()
    if train_type not in ["spd", "sta", "pwr", "guts", "wit"]:
        log_error(f"Invalid train_type '{train_type}'. Must be one of spd/sta/pwr/guts/wit.")
        return None
    
    log_info("=" * 70)
    log_info(f"Single Stat Failure Check Test: {train_type.upper()}")
    log_info("=" * 70)
    log_info("\nThis test will:")
    log_info("  1. Go to training screen")
    log_info("  2. Hover over the training type")
    log_info("  3. Check failure rate")
    log_info("  4. Show detailed timing breakdown\n")
    
    total_start = time.perf_counter()
    step_times = {}
    
    # Step 1: Go to training screen
    log_info("[Step 1] Going to training screen...")
    step_start = time.perf_counter()
    if not go_to_training():
        log_error("Could not go to training screen (training_btn not found).")
        return None
    step_times["go_to_training"] = (time.perf_counter() - step_start) * 1000
    log_info(f"  ✓ Training screen reached ({step_times['go_to_training']:.2f}ms)")
    
    # Step 2: Wait for screen to stabilize
    log_info("\n[Step 2] Waiting for screen to stabilize...")
    step_start = time.perf_counter()
    time.sleep(0.5)
    step_times["stabilization"] = (time.perf_counter() - step_start) * 1000
    log_info(f"  ✓ Screen stabilized ({step_times['stabilization']:.2f}ms)")
    
    # Step 3: Hover over the training type
    log_info(f"\n[Step 3] Hovering over {train_type.upper()} training...")
    training_coords = {
        "spd": (165, 1557),
        "sta": (357, 1563),
        "pwr": (546, 1557),
        "guts": (735, 1566),
        "wit": (936, 1572)
    }
    
    coords = training_coords[train_type]
    start_x, start_y = coords
    end_x, end_y = start_x, start_y - 200  # Move up 200 pixels
    
    step_start = time.perf_counter()
    swipe_start = time.perf_counter()
    swipe(start_x, start_y, end_x, end_y, duration_ms=100)
    step_times["swipe"] = (time.perf_counter() - swipe_start) * 1000
    
    sleep_start = time.perf_counter()
    time.sleep(0.1)  # Wait for hover effect
    step_times["hover_sleep"] = (time.perf_counter() - sleep_start) * 1000
    step_times["hover_total"] = (time.perf_counter() - step_start) * 1000
    log_info(f"  ✓ Hover completed ({step_times['hover_total']:.2f}ms)")
    log_info(f"    - Swipe: {step_times['swipe']:.2f}ms")
    log_info(f"    - Sleep: {step_times['hover_sleep']:.2f}ms")
    
    # Step 4: Take screenshot
    log_info("\n[Step 4] Taking screenshot...")
    step_start = time.perf_counter()
    screenshot = take_screenshot()
    step_times["screenshot"] = (time.perf_counter() - step_start) * 1000
    log_info(f"  ✓ Screenshot captured ({step_times['screenshot']:.2f}ms)")
    
    # Step 5: Check failure rate
    log_info(f"\n[Step 5] Checking failure rate for {train_type.upper()}...")
    step_start = time.perf_counter()
    try:
        rate, confidence = check_failure(screenshot, train_type)
        step_times["failure_check"] = (time.perf_counter() - step_start) * 1000
        log_info(f"  ✓ Failure check completed ({step_times['failure_check']:.2f}ms)")
        log_info(f"  Result: {rate}% (confidence: {confidence:.2f})")
        
        if step_times["failure_check"] > 500:
            log_info(f"  ⚠️  Slow check - likely needed multiple OCR retries")
        elif step_times["failure_check"] < 200:
            log_info(f"  ✓ Fast check - likely succeeded on first OCR attempt")
    except Exception as e:
        step_times["failure_check"] = (time.perf_counter() - step_start) * 1000
        log_error(f"  ❌ Failure check failed: {e} ({step_times['failure_check']:.2f}ms)")
        rate = None
        confidence = None
    
    # Summary
    total_time = (time.perf_counter() - total_start) * 1000
    step_times["total"] = total_time
    
    log_info("\n" + "=" * 70)
    log_info("TIMING SUMMARY")
    log_info("=" * 70)
    log_info(f"\nTotal time: {total_time:.2f}ms")
    log_info(f"\nBreakdown:")
    log_info(f"  1. Go to training:     {step_times.get('go_to_training', 0):7.2f}ms")
    log_info(f"  2. Stabilization:      {step_times.get('stabilization', 0):7.2f}ms")
    log_info(f"  3. Hover operation:    {step_times.get('hover_total', 0):7.2f}ms")
    log_info(f"     - Swipe:            {step_times.get('swipe', 0):7.2f}ms")
    log_info(f"     - Sleep:            {step_times.get('hover_sleep', 0):7.2f}ms")
    log_info(f"  4. Screenshot:         {step_times.get('screenshot', 0):7.2f}ms")
    log_info(f"  5. Failure check:      {step_times.get('failure_check', 0):7.2f}ms")
    
    if total_time > 0:
        log_info(f"\nTime distribution:")
        for step_name, step_time in step_times.items():
            if step_name != "total" and step_time > 0:
                percentage = (step_time / total_time) * 100
                log_info(f"  {step_name:20s}: {percentage:5.1f}% ({step_time:.2f}ms)")
    
    log_info("=" * 70)
    
    return {
        "train_type": train_type,
        "rate": rate,
        "confidence": confidence,
        "timing": step_times
    }


def test_failure_check_multiple_runs():
    """Test failure check timing across multiple runs to show consistency"""
    
    log_info("\n" + "=" * 70)
    log_info("Failure Check Consistency Test (Multiple Runs)")
    log_info("=" * 70)
    log_info("\nTesting each training type 5 times to show timing consistency...\n")
    
    training_types = ["spd", "sta", "pwr", "guts", "wit"]
    
    all_results = {}
    
    for train_type in training_types:
        log_info(f"Testing {train_type.upper()} (5 runs):")
        times = []
        rates = []
        confidences = []
        
        for i in range(5):
            screenshot = take_screenshot()
            start = time.perf_counter()
            try:
                rate, confidence = check_failure(screenshot, train_type)
                elapsed = (time.perf_counter() - start) * 1000
                times.append(elapsed)
                rates.append(rate)
                confidences.append(confidence)
                log_info(f"  Run {i+1}: {elapsed:.2f}ms - {rate}% (conf: {confidence:.2f})")
            except Exception as e:
                log_error(f"  Run {i+1}: ERROR - {e}")
            time.sleep(0.1)  # Small delay between runs
        
        if times:
            all_results[train_type] = {
                "times": times,
                "avg": sum(times) / len(times),
                "min": min(times),
                "max": max(times),
                "rates": rates,
                "confidences": confidences
            }
            log_info(f"  Average: {all_results[train_type]['avg']:.2f}ms")
            log_info(f"  Range: {all_results[train_type]['min']:.2f}ms - {all_results[train_type]['max']:.2f}ms")
        log_info("")
    
    # Summary
    log_info("=" * 70)
    log_info("CONSISTENCY SUMMARY")
    log_info("=" * 70)
    
    for train_type, data in all_results.items():
        log_info(f"\n{train_type.upper()}:")
        log_info(f"  Average time: {data['avg']:.2f}ms")
        log_info(f"  Min time:     {data['min']:.2f}ms")
        log_info(f"  Max time:     {data['max']:.2f}ms")
        log_info(f"  Variation:    {data['max'] - data['min']:.2f}ms")
        if data['avg'] > 0:
            variation_pct = ((data['max'] - data['min']) / data['avg']) * 100
            log_info(f"  Variation %:  {variation_pct:.1f}%")
    
    log_info("=" * 70)
    
    return all_results


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test failure check timing")
    parser.add_argument(
        "--single",
        "-s",
        type=str,
        choices=["spd", "sta", "pwr", "guts", "wit"],
        help="Test a single training type (will hover first)",
    )
    parser.add_argument(
        "--all",
        "-a",
        action="store_true",
        help="Test all training types (requires already on training screen with hover)",
    )
    parser.add_argument(
        "--consistency",
        "-c",
        action="store_true",
        help="Run consistency test (multiple runs)",
    )
    
    args = parser.parse_args()
    
    try:
        if args.single:
            # Single stat test - will handle hover automatically
            log_info("Single Stat Failure Check Test")
            log_info("Make sure you're in the career lobby (bot will navigate to training).\n")
            time.sleep(2)
            
            result = test_single_stat_failure_check(args.single)
            if result:
                log_info("\n✓ Single stat test completed")
            return 0
        
        elif args.all:
            # Test all stats (assumes already on training screen with hover)
            log_info("All Stats Failure Check Test")
            log_info("Make sure you're on the training screen with failure % visible.\n")
            time.sleep(2)
            
            results = test_failure_check_timing()
            log_info("\n✓ All stats test completed")
            return 0
        
        elif args.consistency:
            # Consistency test
            log_info("Consistency Test")
            log_info("Make sure you're on the training screen with failure % visible.\n")
            time.sleep(2)
            
            consistency_results = test_failure_check_multiple_runs()
            log_info("\n✓ Consistency test completed")
            return 0
        
        else:
            # Default: show help and run single stat test
            log_info("Failure Check Timing Test")
            log_info("=" * 70)
            log_info("\nUsage:")
            log_info("  Single stat test (recommended - handles hover automatically):")
            log_info("    python -m unity_test.test_failure_check_timing --single spd")
            log_info("    python -m unity_test.test_failure_check_timing -s sta")
            log_info("\n  All stats test (requires already on training screen with hover):")
            log_info("    python -m unity_test.test_failure_check_timing --all")
            log_info("    python -m unity_test.test_failure_check_timing -a")
            log_info("\n  Consistency test (multiple runs):")
            log_info("    python -m unity_test.test_failure_check_timing --consistency")
            log_info("    python -m unity_test.test_failure_check_timing -c")
            log_info("\nExample - Test SPD failure check:")
            log_info("    python -m unity_test.test_failure_check_timing -s spd")
            return 0
        
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

