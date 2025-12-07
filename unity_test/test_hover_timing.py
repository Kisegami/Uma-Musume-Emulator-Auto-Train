"""
Demonstration test for hover operation timing breakdown.

This test shows why the hover operation takes time by breaking down each component:
1. ADB command execution time
2. Swipe duration (100ms)
3. Sleep delay (100ms)
4. Total hover time

Run from project root:
    python -m unity_test.test_hover_timing
"""

import os
import sys
import time

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.log import log_info, log_warning, log_error, log_debug
from utils.input import swipe
from utils.device import run_adb
from utils.screenshot import take_screenshot


def test_hover_timing_breakdown():
    """Break down the hover operation to show where time is spent"""
    
    log_info("=" * 70)
    log_info("Hover Operation Timing Breakdown Demonstration")
    log_info("=" * 70)
    log_info("\nThis test demonstrates why hover takes time by measuring each component.\n")
    
    # Training coordinates (using SPD as example)
    training_coords = {
        "spd": (165, 1557),
        "sta": (357, 1563),
        "pwr": (546, 1557),
        "guts": (735, 1566),
        "wit": (936, 1572)
    }
    
    # Test with SPD training
    key = "spd"
    coords = training_coords[key]
    start_x, start_y = coords
    end_x, end_y = start_x, start_y - 200  # Move up 200 pixels
    duration_ms = 100
    
    log_info(f"Testing hover for {key.upper()} training:")
    log_info(f"  Start: ({start_x}, {start_y})")
    log_info(f"  End:   ({end_x}, {end_y})")
    log_info(f"  Distance: 200 pixels")
    log_info(f"  Swipe duration: {duration_ms}ms")
    log_info(f"  Sleep after swipe: 100ms\n")
    
    # Check input_delay from config
    import json
    try:
        with open('config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
            adb_config = config.get('adb_config', {})
            input_delay = float(adb_config.get('input_delay', 0.5))
    except:
        input_delay = 0.5
    
    log_info(f"  Config input_delay: {input_delay}s ({input_delay*1000:.0f}ms)")
    log_info(f"  (This delay is added by run_adb() before executing 'input' commands)\n")
    
    # Test 1: Measure ADB command execution time (includes input_delay)
    log_info("=" * 70)
    log_info("Test 1: ADB Command Execution Time (includes input_delay)")
    log_info("=" * 70)
    
    adb_times = []
    for i in range(5):
        start = time.perf_counter()
        # Execute the command (includes input_delay sleep)
        command = ['shell', 'input', 'swipe', str(start_x), str(start_y), str(end_x), str(end_y), str(duration_ms)]
        result = run_adb(command)
        exec_time = (time.perf_counter() - start) * 1000
        adb_times.append(exec_time)
        
        log_info(f"  Run {i+1}: ADB execution = {exec_time:.2f}ms")
        log_info(f"           (includes {input_delay*1000:.0f}ms input_delay + actual command time)")
        time.sleep(0.1)  # Small delay between tests
    
    avg_adb = sum(adb_times) / len(adb_times)
    log_info(f"\n  Average ADB execution time: {avg_adb:.2f}ms")
    log_info(f"  (Includes {input_delay*1000:.0f}ms input_delay from config)")
    
    # Test 2: Measure swipe() function call (includes ADB + any overhead)
    log_info("\n" + "=" * 70)
    log_info("Test 2: swipe() Function Call Time")
    log_info("=" * 70)
    
    swipe_times = []
    for i in range(5):
        start = time.perf_counter()
        result = swipe(start_x, start_y, end_x, end_y, duration_ms=duration_ms)
        elapsed = (time.perf_counter() - start) * 1000
        swipe_times.append(elapsed)
        
        log_info(f"  Run {i+1}: swipe() call = {elapsed:.2f}ms")
        time.sleep(0.1)  # Small delay between tests
    
    avg_swipe = sum(swipe_times) / len(swipe_times)
    log_info(f"\n  Average swipe() call time: {avg_swipe:.2f}ms")
    
    # Test 3: Measure complete hover operation (swipe + sleep)
    log_info("\n" + "=" * 70)
    log_info("Test 3: Complete Hover Operation (swipe + sleep)")
    log_info("=" * 70)
    
    hover_times = []
    for i in range(5):
        hover_start = time.perf_counter()
        
        # Swipe operation
        swipe_start = time.perf_counter()
        swipe(start_x, start_y, end_x, end_y, duration_ms=duration_ms)
        swipe_elapsed = (time.perf_counter() - swipe_start) * 1000
        
        # Sleep delay
        sleep_start = time.perf_counter()
        time.sleep(0.1)  # Wait for hover effect to register
        sleep_elapsed = (time.perf_counter() - sleep_start) * 1000
        
        hover_elapsed = (time.perf_counter() - hover_start) * 1000
        hover_times.append(hover_elapsed)
        
        log_info(f"  Run {i+1}:")
        log_info(f"    - Swipe: {swipe_elapsed:.2f}ms")
        log_info(f"    - Sleep: {sleep_elapsed:.2f}ms")
        log_info(f"    - Total: {hover_elapsed:.2f}ms")
        time.sleep(0.1)  # Small delay between tests
    
    avg_hover = sum(hover_times) / len(hover_times)
    log_info(f"\n  Average complete hover time: {avg_hover:.2f}ms")
    
    # Test 4: Measure swipe duration impact
    log_info("\n" + "=" * 70)
    log_info("Test 4: Swipe Duration Impact")
    log_info("=" * 70)
    log_info("Testing different swipe durations to see impact on total time:\n")
    
    durations = [50, 100, 150, 200]
    for dur in durations:
        start = time.perf_counter()
        swipe(start_x, start_y, end_x, end_y, duration_ms=dur)
        elapsed = (time.perf_counter() - start) * 1000
        log_info(f"  Duration {dur:3d}ms: Total time = {elapsed:.2f}ms")
        time.sleep(0.1)
    
    # Summary
    log_info("\n" + "=" * 70)
    log_info("SUMMARY")
    log_info("=" * 70)
    log_info(f"\nHover operation breakdown:")
    log_info(f"  1. Input delay (config):    {input_delay*1000:.0f}ms (from adb_config.input_delay)")
    log_info(f"  2. ADB command execution:  ~{avg_adb - input_delay*1000:.2f}ms (actual command)")
    log_info(f"  3. Swipe duration:         {duration_ms}ms (gesture execution time)")
    log_info(f"  4. Sleep delay:            100ms (wait for hover effect)")
    log_info(f"  5. Total hover time:      ~{avg_hover:.2f}ms")
    log_info(f"\nTime distribution:")
    if avg_hover > 0:
        input_delay_pct = (input_delay*1000 / avg_hover) * 100
        adb_pct = ((avg_adb - input_delay*1000) / avg_hover) * 100
        swipe_pct = (duration_ms / avg_hover) * 100
        sleep_pct = (100 / avg_hover) * 100
        log_info(f"  - Input delay:     {input_delay_pct:.1f}% ({input_delay*1000:.0f}ms)")
        log_info(f"  - ADB execution:   {adb_pct:.1f}%")
        log_info(f"  - Swipe duration:  {swipe_pct:.1f}%")
        log_info(f"  - Sleep delay:      {sleep_pct:.1f}%")
    
    log_info(f"\nWhy hover takes time:")
    log_info(f"  • Input delay: {input_delay*1000:.0f}ms delay before ADB 'input' commands (configurable)")
    log_info(f"  • ADB command: ~{avg_adb - input_delay*1000:.2f}ms to send command to emulator")
    log_info(f"  • Swipe gesture: {duration_ms}ms to complete the swipe")
    log_info(f"  • Hover effect: 100ms sleep to let game register hover and show support cards")
    log_info(f"  • Total: ~{avg_hover:.2f}ms per training type")
    log_info(f"\nFor 5 training types: ~{avg_hover * 5:.2f}ms total hover time")
    log_info(f"\n💡 To reduce hover time:")
    log_info(f"   - Reduce 'input_delay' in config.json (default: 0.5s)")
    log_info(f"   - Reduce swipe duration (currently {duration_ms}ms)")
    log_info(f"   - Reduce sleep delay (currently 100ms)")
    log_info("=" * 70)


def main():
    """Main entry point"""
    try:
        log_info("Make sure emulator is connected and game is running.")
        log_info("This test will perform swipes - make sure you're on a safe screen.\n")
        time.sleep(2)  # Give user time to read
        
        test_hover_timing_breakdown()
        
        log_info("\n✓ Test completed")
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

