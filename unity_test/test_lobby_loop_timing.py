"""
Test for lobby loop checks with detailed timing measurements.
Measures time for all checks done in career_lobby() to identify bottlenecks.
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
from utils.recognizer import locate_on_screen, match_template
from core_unity.state import (
    check_mood,
    check_turn,
    check_current_year,
    check_goal_name,
    check_criteria,
    check_energy_bar,
    check_current_stats,
    check_dating_available,
    check_skill_points_cap,
)
from core_unity.execute import check_goal_criteria

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

def check_lobby_loop(timings: Dict) -> Dict:
    """Simulate one lobby loop iteration with detailed timing"""
    results = {}
    
    # Step 1: Initial screenshot
    print("\n[STEP] Taking initial screenshot...")
    with TimingContext("screenshot_initial", timings):
        screenshot = take_screenshot()
        if not screenshot:
            print("[ERROR] Failed to take screenshot")
            return {}
    
    # Step 2: UI element checks (batch checks on same screenshot)
    print("\n[STEP] Checking UI elements...")
    
    # Complete career check
    with TimingContext("check_complete_career", timings):
        complete_career_matches = match_template(screenshot, "assets/buttons/complete_career.png", confidence=0.8)
        results["complete_career"] = bool(complete_career_matches)
    
    # Claw machine check
    with TimingContext("check_claw", timings):
        claw_matches = match_template(screenshot, "assets/buttons/claw.png", confidence=0.8)
        results["claw"] = bool(claw_matches)
    
    # OK button check
    with TimingContext("check_ok_btn", timings):
        ok_matches = match_template(screenshot, "assets/buttons/ok_btn.png", confidence=0.8)
        results["ok_btn"] = bool(ok_matches)
    
    # Event check
    with TimingContext("check_event", timings):
        event_choice_region = (6, 450, 126, 1776)
        event_matches = match_template(screenshot, "assets/icons/event_choice_1.png", confidence=0.7, region=event_choice_region)
        results["event"] = bool(event_matches)
    
    # Unity Cup check
    with TimingContext("check_unity_cup", timings):
        unity_cup_matches = match_template(screenshot, "assets/unity/unity_cup.png", confidence=0.8)
        results["unity_cup"] = bool(unity_cup_matches)
    
    # Inspiration check
    with TimingContext("check_inspiration", timings):
        inspiration_matches = match_template(screenshot, "assets/buttons/inspiration_btn.png", confidence=0.5)
        results["inspiration"] = bool(inspiration_matches)
    
    # Cancel button check
    with TimingContext("check_cancel", timings):
        cancel_matches = match_template(screenshot, "assets/buttons/cancel_lobby.png", confidence=0.8)
        results["cancel"] = bool(cancel_matches)
    
    # Close button check
    with TimingContext("check_close", timings):
        close_matches = match_template(screenshot, "assets/buttons/close.png", confidence=0.8)
        results["close"] = bool(close_matches)
    
    # Next button check
    with TimingContext("check_next", timings):
        next_matches = match_template(screenshot, "assets/buttons/next_btn.png", confidence=0.8)
        results["next"] = bool(next_matches)
    
    # Tazuna hint check (lobby confirmation)
    with TimingContext("check_tazuna_hint", timings):
        tazuna_hint_matches = match_template(screenshot, "assets/ui/tazuna_hint.png", confidence=0.8)
        results["tazuna_hint"] = bool(tazuna_hint_matches)
    
    # Step 3: Take fresh screenshot after lobby confirmation
    print("\n[STEP] Taking fresh screenshot after lobby confirmation...")
    with TimingContext("screenshot_fresh", timings):
        screenshot = take_screenshot()
        if not screenshot:
            print("[ERROR] Failed to take fresh screenshot")
            return results
    
    # Step 4: Infirmary check
    print("\n[STEP] Checking infirmary...")
    with TimingContext("check_infirmary", timings):
        infirmary_matches = match_template(screenshot, "assets/buttons/infirmary_btn2.png", confidence=0.9)
        results["infirmary"] = bool(infirmary_matches)
    
    # Step 5: State checks
    print("\n[STEP] Checking game state...")
    
    with TimingContext("check_mood", timings):
        mood = check_mood(screenshot)
        results["mood"] = mood
    
    with TimingContext("check_turn", timings):
        turn = check_turn(screenshot)
        results["turn"] = turn
    
    with TimingContext("check_year", timings):
        year = check_current_year(screenshot)
        results["year"] = year
    
    with TimingContext("check_goal_name", timings):
        goal_name = check_goal_name(screenshot)
        results["goal_name"] = goal_name
    
    with TimingContext("check_criteria", timings):
        criteria = check_criteria(screenshot)
        results["criteria"] = criteria
    
    # Step 6: Energy and stats
    print("\n[STEP] Checking energy and stats...")
    
    with TimingContext("check_energy", timings):
        energy = check_energy_bar(screenshot)
        results["energy"] = energy
    
    with TimingContext("check_stats", timings):
        stats = check_current_stats(screenshot)
        results["stats"] = stats
    
    with TimingContext("check_dating", timings):
        dating = check_dating_available(screenshot)
        results["dating"] = dating
    
    # Step 7: Goal analysis
    print("\n[STEP] Analyzing goal criteria...")
    with TimingContext("check_goal_criteria", timings):
        goal_analysis = check_goal_criteria({"text": results.get("criteria", "")}, results.get("year", ""), results.get("turn", 1))
        results["goal_analysis"] = goal_analysis
    
    # Step 8: Race day check
    print("\n[STEP] Checking for race day...")
    with TimingContext("check_race_day", timings):
        goal_matches = match_template(screenshot, "assets/unity/goal.png", confidence=0.8)
        results["race_day"] = bool(goal_matches)
    
    # Step 9: Skill points cap check
    print("\n[STEP] Checking skill points cap...")
    with TimingContext("check_skill_points_cap", timings):
        try:
            check_skill_points_cap(screenshot)
            results["skill_points_cap"] = True
        except Exception as e:
            results["skill_points_cap"] = f"Error: {e}"
    
    return results

def print_timing_summary(timings: Dict):
    """Print detailed timing summary"""
    print("\n" + "="*80)
    print("LOBBY LOOP TIMING SUMMARY")
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
    
    # Group by category
    screenshot_keys = [k for k in timings.keys() if "screenshot" in k]
    ui_check_keys = [k for k in timings.keys() if k.startswith("check_") and k not in ["check_mood", "check_turn", "check_year", "check_goal_name", "check_criteria", "check_energy", "check_stats", "check_dating", "check_goal_criteria", "check_skill_points_cap"]]
    state_check_keys = ["check_mood", "check_turn", "check_year", "check_goal_name", "check_criteria"]
    analysis_keys = ["check_energy", "check_stats", "check_dating", "check_goal_criteria", "check_race_day", "check_skill_points_cap"]
    
    screenshot_total = sum(sum(timings.get(k, [])) for k in screenshot_keys)
    ui_check_total = sum(sum(timings.get(k, [])) for k in ui_check_keys)
    state_check_total = sum(sum(timings.get(k, [])) for k in state_check_keys)
    analysis_total = sum(sum(timings.get(k, [])) for k in analysis_keys)
    total_all = sum(total_times.values())
    
    print("\n" + "="*80)
    print("CATEGORY BREAKDOWN")
    print("="*80)
    print(f"  Screenshots:        {screenshot_total:8.3f}s ({screenshot_total/total_all*100:5.1f}%)")
    print(f"  UI Element Checks:  {ui_check_total:8.3f}s ({ui_check_total/total_all*100:5.1f}%)")
    print(f"  State Checks:       {state_check_total:8.3f}s ({state_check_total/total_all*100:5.1f}%)")
    print(f"  Analysis Checks:   {analysis_total:8.3f}s ({analysis_total/total_all*100:5.1f}%)")
    print(f"  TOTAL:              {total_all:8.3f}s")
    
    # Top 10 slowest operations
    print("\n" + "="*80)
    print("TOP 10 SLOWEST OPERATIONS")
    print("="*80)
    for i, (key, total_time) in enumerate(sorted_times[:10], 1):
        percentage = (total_time / total_all * 100) if total_all > 0 else 0
        print(f"  {i:2d}. {key:40s}: {total_time:8.3f}s ({percentage:5.1f}%)")
    
    # Overall statistics
    all_times = [t for times in timings.values() for t in times]
    if all_times:
        print("\n" + "="*80)
        print("OVERALL STATISTICS")
        print("="*80)
        print(f"  Total operations: {len(all_times)}")
        print(f"  Total time: {sum(all_times):.3f}s")
        print(f"  Average operation time: {sum(all_times)/len(all_times):.3f}s")
        print(f"  Min operation time: {min(all_times):.3f}s")
        print(f"  Max operation time: {max(all_times):.3f}s")

def main():
    """Main test function"""
    print("="*80)
    print("LOBBY LOOP TIMING TEST")
    print("="*80)
    print("\nThis test will:")
    print("  1. Connect to emulator")
    print("  2. Simulate one lobby loop iteration")
    print("  3. Measure timing for all checks")
    print("  4. Identify bottlenecks")
    print("\n" + "="*80 + "\n")
    
    timings = defaultdict(list)
    
    # Step 1: Connect to emulator
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
    
    # Step 2: Run one lobby loop iteration
    print("\n[STEP] Running lobby loop iteration...")
    start_time = time.time()
    results = check_lobby_loop(timings)
    total_time = time.time() - start_time
    
    # Step 3: Print timing summary
    print_timing_summary(timings)
    
    # Step 4: Print results summary
    print("\n" + "="*80)
    print("RESULTS SUMMARY")
    print("="*80)
    print(f"Total loop time: {total_time:.3f}s")
    print("\nDetected Elements:")
    for key, value in results.items():
        if key not in ["mood", "turn", "year", "goal_name", "criteria", "energy", "stats", "dating", "goal_analysis"]:
            print(f"  {key:20s}: {value}")
    
    print("\nGame State:")
    print(f"  Mood: {results.get('mood', 'Unknown')}")
    print(f"  Turn: {results.get('turn', 'Unknown')}")
    print(f"  Year: {results.get('year', 'Unknown')}")
    print(f"  Goal: {results.get('goal_name', 'Unknown')}")
    print(f"  Criteria: {results.get('criteria', 'Unknown')}")
    print(f"  Energy: {results.get('energy', 0):.1f}%")
    stats = results.get('stats', {})
    print(f"  Stats: SPD={stats.get('spd', 0)}, STA={stats.get('sta', 0)}, PWR={stats.get('pwr', 0)}, GUTS={stats.get('guts', 0)}, WIT={stats.get('wit', 0)}")
    print(f"  Dating: {results.get('dating', False)}")
    print(f"  Race Day: {results.get('race_day', False)}")
    
    print("\n" + "="*80)
    print("TEST COMPLETED")
    print("="*80)
    print("\nBOTTLENECK ANALYSIS:")
    print("  Check the 'TOP 10 SLOWEST OPERATIONS' section above to identify")
    print("  which checks are taking the most time. Focus optimization efforts there.")

if __name__ == "__main__":
    main()

