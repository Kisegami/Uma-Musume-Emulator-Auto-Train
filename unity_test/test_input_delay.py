"""
Test to see if input_delay is necessary for proper operation.

This test will:
1. Test operations with input_delay (current behavior)
2. Test operations without input_delay (modified behavior)
3. Compare results to see if delay is necessary

Run from project root:
    python -m unity_test.test_input_delay
"""

import os
import sys
import time
import json

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.log import log_info, log_warning, log_error, log_debug
from utils.input import tap, swipe
from utils.device import run_adb
from utils.screenshot import take_screenshot


def test_with_delay():
    """Test input operations with normal input_delay"""
    log_info("\n" + "=" * 70)
    log_info("TEST 1: With input_delay (current behavior)")
    log_info("=" * 70)
    
    # Get current input_delay
    try:
        with open('config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
            adb_config = config.get('adb_config', {})
            input_delay = float(adb_config.get('input_delay', 0.5))
    except:
        input_delay = 0.5
    
    log_info(f"Current input_delay: {input_delay}s")
    log_info("Testing tap and swipe operations...\n")
    
    times = []
    for i in range(3):
        start = time.perf_counter()
        # Test tap
        result = tap(540, 960)  # Center of screen
        elapsed = (time.perf_counter() - start) * 1000
        times.append(elapsed)
        log_info(f"  Tap {i+1}: {elapsed:.2f}ms")
        time.sleep(0.1)
    
    avg_time = sum(times) / len(times)
    log_info(f"\nAverage time with delay: {avg_time:.2f}ms")
    return avg_time


def test_without_delay():
    """Test input operations without input_delay by calling run_adb directly with add_input_delay=False"""
    log_info("\n" + "=" * 70)
    log_info("TEST 2: Without input_delay (modified behavior)")
    log_info("=" * 70)
    
    log_info("Testing tap and swipe operations WITHOUT input_delay...\n")
    
    times = []
    for i in range(3):
        start = time.perf_counter()
        # Test tap without delay
        result = run_adb(['shell', 'input', 'tap', '540', '960'], add_input_delay=False)
        elapsed = (time.perf_counter() - start) * 1000
        times.append(elapsed)
        log_info(f"  Tap {i+1}: {elapsed:.2f}ms")
        time.sleep(0.1)
    
    avg_time = sum(times) / len(times)
    log_info(f"\nAverage time without delay: {avg_time:.2f}ms")
    return avg_time


def test_rapid_inputs():
    """Test rapid input commands to see if delay prevents issues"""
    log_info("\n" + "=" * 70)
    log_info("TEST 3: Rapid Input Commands (stress test)")
    log_info("=" * 70)
    
    log_info("Testing 10 rapid taps to see if delay prevents input conflicts...\n")
    
    # With delay
    log_info("With input_delay:")
    start = time.perf_counter()
    for i in range(10):
        tap(540, 960)
    with_delay_time = (time.perf_counter() - start) * 1000
    log_info(f"  10 taps completed in {with_delay_time:.2f}ms")
    time.sleep(0.5)
    
    # Without delay
    log_info("\nWithout input_delay:")
    start = time.perf_counter()
    for i in range(10):
        run_adb(['shell', 'input', 'tap', '540', '960'], add_input_delay=False)
    without_delay_time = (time.perf_counter() - start) * 1000
    log_info(f"  10 taps completed in {without_delay_time:.2f}ms")
    
    speedup = with_delay_time / without_delay_time if without_delay_time > 0 else 0
    log_info(f"\nSpeedup: {speedup:.2f}x faster without delay")
    
    return with_delay_time, without_delay_time


def test_hover_without_delay():
    """Test hover operation without delay"""
    log_info("\n" + "=" * 70)
    log_info("TEST 4: Hover Operation Without Delay")
    log_info("=" * 70)
    
    # Training coordinates (SPD)
    start_x, start_y = 165, 1557
    end_x, end_y = start_x, start_y - 200
    
    log_info("Testing hover swipe without input_delay...\n")
    
    # With delay (normal)
    start = time.perf_counter()
    swipe(start_x, start_y, end_x, end_y, duration_ms=100)
    time.sleep(0.1)
    with_delay = (time.perf_counter() - start) * 1000
    log_info(f"With delay: {with_delay:.2f}ms")
    time.sleep(0.5)
    
    # Without delay
    start = time.perf_counter()
    run_adb(['shell', 'input', 'swipe', str(start_x), str(start_y), str(end_x), str(end_y), '100'], add_input_delay=False)
    time.sleep(0.1)
    without_delay = (time.perf_counter() - start) * 1000
    log_info(f"Without delay: {without_delay:.2f}ms")
    
    speedup = with_delay / without_delay if without_delay > 0 else 0
    log_info(f"\nSpeedup: {speedup:.2f}x faster")
    
    return with_delay, without_delay


def main():
    """Main entry point"""
    try:
        log_info("=" * 70)
        log_info("Input Delay Necessity Test")
        log_info("=" * 70)
        log_info("\nThis test will check if input_delay is necessary for proper operation.")
        log_info("Make sure emulator is connected and game is running.")
        log_info("WARNING: This will perform taps on the screen!\n")
        time.sleep(3)  # Give user time to read
        
        # Test 1: Normal operations
        avg_with = test_with_delay()
        
        # Test 2: Without delay
        avg_without = test_without_delay()
        
        # Test 3: Rapid inputs
        rapid_with, rapid_without = test_rapid_inputs()
        
        # Test 4: Hover operation
        hover_with, hover_without = test_hover_without_delay()
        
        # Summary
        log_info("\n" + "=" * 70)
        log_info("SUMMARY")
        log_info("=" * 70)
        log_info(f"\nTime comparison:")
        log_info(f"  Single tap:")
        log_info(f"    With delay:    {avg_with:.2f}ms")
        log_info(f"    Without delay: {avg_without:.2f}ms")
        log_info(f"    Speedup:       {avg_with / avg_without:.2f}x faster")
        
        log_info(f"\n  Rapid taps (10x):")
        log_info(f"    With delay:    {rapid_with:.2f}ms")
        log_info(f"    Without delay: {rapid_without:.2f}ms")
        log_info(f"    Speedup:       {rapid_with / rapid_without:.2f}x faster")
        
        log_info(f"\n  Hover operation:")
        log_info(f"    With delay:    {hover_with:.2f}ms")
        log_info(f"    Without delay: {hover_without:.2f}ms")
        log_info(f"    Speedup:       {hover_with / hover_without:.2f}x faster")
        
        log_info(f"\n💡 Recommendation:")
        if avg_without < avg_with * 0.8:  # Significant speedup
            log_info("  ✓ Removing input_delay provides significant speedup")
            log_info("  ✓ Consider setting input_delay to 0.0 or very low (0.05-0.1)")
            log_info("  ⚠️  Monitor for input conflicts or missed taps")
        else:
            log_info("  ⚠️  Delay may be necessary for your emulator")
            log_info("  ✓ Try reducing input_delay to 0.1-0.2s instead of removing it")
        
        log_info("\nTo disable input_delay:")
        log_info("  1. Edit config.json")
        log_info("  2. Set 'input_delay' to 0.0 in 'adb_config'")
        log_info("  3. Or modify utils/device.py to default to 0.0")
        
        log_info("=" * 70)
        
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

