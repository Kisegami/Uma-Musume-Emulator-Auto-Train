"""
Test for state checking workflow with detailed timing measurements.
Measures time for all state checks: mood, turn, year, goal, criteria, energy, stats, dating.
"""

import time
import os
import sys
from typing import Dict
from collections import defaultdict

# Add parent directory to path to import utils
_script_dir = os.path.dirname(os.path.abspath(__file__))
_parent_dir = os.path.dirname(_script_dir)
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)

# Import utils
from utils.screenshot import take_screenshot
from core_unity.state import (
    check_mood,
    check_turn,
    check_current_year,
    check_goal_name,
    check_criteria,
    check_energy_bar,
    check_current_stats,
    check_dating_available,
)

# Timing context manager
class TimingContext:
    """Context manager for timing operations"""
    def __init__(self, name: str, timings: Dict):
        self.name = name
        self.timings = timings
        self.start_time = None
        
    def __enter__(self):
        self.start_time = time.time()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        elapsed = time.time() - self.start_time
        self.timings[self.name].append(elapsed)

def check_all_states(timings: Dict) -> Dict:
    """Check all game states with detailed timing"""
    print("\n[STEP] Taking screenshot for state checks...")
    with TimingContext("screenshot", timings):
        screenshot = take_screenshot()
        if not screenshot:
            print("[ERROR] Failed to take screenshot")
            return {}
    
    results = {}
    
    # Check mood
    print("\n[CHECK] Checking mood...")
    with TimingContext("check_mood", timings):
        mood = check_mood(screenshot)
        results["mood"] = mood
        print(f"  [RESULT] Mood: {mood}")
    
    # Check turn
    print("\n[CHECK] Checking turn...")
    with TimingContext("check_turn", timings):
        turn = check_turn(screenshot)
        results["turn"] = turn
        print(f"  [RESULT] Turn: {turn}")
    
    # Check year
    print("\n[CHECK] Checking year...")
    with TimingContext("check_year", timings):
        year = check_current_year(screenshot)
        results["year"] = year
        print(f"  [RESULT] Year: {year}")
    
    # Check goal name
    print("\n[CHECK] Checking goal name...")
    with TimingContext("check_goal_name", timings):
        goal_name = check_goal_name(screenshot)
        results["goal_name"] = goal_name
        print(f"  [RESULT] Goal: {goal_name}")
    
    # Check criteria
    print("\n[CHECK] Checking criteria...")
    with TimingContext("check_criteria", timings):
        criteria = check_criteria(screenshot)
        results["criteria"] = criteria
        print(f"  [RESULT] Criteria: {criteria}")
    
    # Check energy bar
    print("\n[CHECK] Checking energy bar...")
    with TimingContext("check_energy", timings):
        energy = check_energy_bar(screenshot)
        results["energy"] = energy
        print(f"  [RESULT] Energy: {energy:.1f}%")
    
    # Check current stats
    print("\n[CHECK] Checking current stats...")
    with TimingContext("check_stats", timings):
        stats = check_current_stats(screenshot)
        results["stats"] = stats
        print(f"  [RESULT] Stats: {stats}")
    
    # Check dating available
    print("\n[CHECK] Checking dating availability...")
    with TimingContext("check_dating", timings):
        dating = check_dating_available(screenshot)
        results["dating"] = dating
        print(f"  [RESULT] Dating available: {dating}")
    
    return results

def print_timing_summary(timings: Dict):
    """Print detailed timing summary"""
    print("\n" + "="*80)
    print("TIMING SUMMARY")
    print("="*80)
    
    # Calculate totals
    total_times = {}
    for key, times in timings.items():
        total_times[key] = sum(times)
    
    # Sort by total time
    sorted_times = sorted(total_times.items(), key=lambda x: x[1], reverse=True)
    
    print("\nTotal Time by Operation:")
    print("-" * 80)
    for key, total_time in sorted_times:
        count = len(timings[key])
        avg_time = total_time / count if count > 0 else 0
        print(f"  {key:40s} | Total: {total_time:8.3f}s | Count: {count:3d} | Avg: {avg_time:6.3f}s")
    
    # Overall statistics
    all_times = [t for times in timings.values() for t in times]
    if all_times:
        print("\nOverall Statistics:")
        print("-" * 80)
        print(f"  Total operations: {len(all_times)}")
        print(f"  Total time: {sum(all_times):.3f}s")
        print(f"  Average operation time: {sum(all_times)/len(all_times):.3f}s")
        print(f"  Min operation time: {min(all_times):.3f}s")
        print(f"  Max operation time: {max(all_times):.3f}s")
    
    # State check breakdown
    state_checks = ["check_mood", "check_turn", "check_year", "check_goal_name", 
                    "check_criteria", "check_energy", "check_stats", "check_dating"]
    state_total = sum(sum(timings.get(k, [])) for k in state_checks)
    screenshot_total = sum(timings.get("screenshot", []))
    
    if state_total > 0:
        print("\nState Check Breakdown:")
        print("-" * 80)
        print(f"  Total state check time: {state_total:.3f}s")
        print(f"  Screenshot time: {screenshot_total:.3f}s")
        print(f"  Average per state check: {state_total / len(state_checks):.3f}s")
        
        print("\n  Individual State Checks:")
        for check in state_checks:
            if check in timings and timings[check]:
                check_time = sum(timings[check])
                percentage = (check_time / state_total * 100) if state_total > 0 else 0
                print(f"    - {check:25s}: {check_time:8.3f}s ({percentage:5.1f}%)")

def main():
    """Main test function"""
    print("="*80)
    print("STATE CHECK TIMING TEST")
    print("="*80)
    print("\nThis test will:")
    print("  1. Connect to emulator")
    print("  2. Take a screenshot")
    print("  3. Check all game states (mood, turn, year, goal, criteria, energy, stats, dating)")
    print("  4. Output detailed timing for each check")
    print("\n" + "="*80 + "\n")
    
    timings = defaultdict(list)
    
    # Step 1: Connect to emulator (test screenshot)
    print("[STEP] Testing emulator connection...")
    with TimingContext("emulator_connection", timings):
        test_screenshot = take_screenshot()
        if not test_screenshot:
            print("[ERROR] Failed to connect to emulator. Please check:")
            print("  - ADB is installed and in PATH")
            print("  - Emulator is running")
            print("  - config.json has correct adb_config settings")
            return
        print(f"[SUCCESS] Emulator connected. Screenshot size: {test_screenshot.size}")
    
    # Step 2: Check all states
    print("\n[STEP] Starting state checks...")
    start_time = time.time()
    results = check_all_states(timings)
    total_time = time.time() - start_time
    
    # Step 3: Print timing summary
    print_timing_summary(timings)
    
    # Step 4: Print results summary
    print("\n" + "="*80)
    print("RESULTS SUMMARY")
    print("="*80)
    print(f"Total time: {total_time:.3f}s")
    print("\nState Check Results:")
    print(f"  Mood: {results.get('mood', 'Unknown')}")
    print(f"  Turn: {results.get('turn', 'Unknown')}")
    print(f"  Year: {results.get('year', 'Unknown')}")
    print(f"  Goal: {results.get('goal_name', 'Unknown')}")
    print(f"  Criteria: {results.get('criteria', 'Unknown')}")
    print(f"  Energy: {results.get('energy', 0):.1f}%")
    stats = results.get('stats', {})
    print(f"  Stats: SPD={stats.get('spd', 0)}, STA={stats.get('sta', 0)}, PWR={stats.get('pwr', 0)}, GUTS={stats.get('guts', 0)}, WIT={stats.get('wit', 0)}")
    print(f"  Dating available: {results.get('dating', False)}")
    
    print("\n" + "="*80)
    print("TEST COMPLETED")
    print("="*80)

if __name__ == "__main__":
    main()

