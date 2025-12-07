"""
Standalone region/detection test for Unity Cup using `utils/constants_unity.py`.

Run this while the Unity Cup scenario is open on the emulator:

    python -m unity_test.test_unity_regions

It will:
- Take one screenshot
- Test:
  - tazuna_hint (lobby marker)
  - stats (SPD/STA/PWR/GUTS/WIT) via OCR
  - energy bar percentage
  - mood
  - goal name
  - year text
  - presence of training / rest / recreation / infirmary buttons
"""

import os
import sys
import time
from typing import Optional, List, Tuple

from PIL import ImageDraw

from utils.log import log_info, log_warning, log_error, log_debug
from utils.screenshot import take_screenshot
from utils.recognizer import locate_on_screen, match_template
from utils.constants_unity import (
    SUPPORT_CARD_ICON_REGION,
    MOOD_REGION,
    TURN_REGION,
    FAILURE_REGION,
    YEAR_REGION,
    CRITERIA_REGION,
    SKILL_PTS_REGION,
    SPD_REGION,
    STA_REGION,
    PWR_REGION,
    GUTS_REGION,
    WIT_REGION,
    EVENT_REGION,
    RACE_CARD_REGION,
    DEFAULT_SCREEN_REGION,
    MOOD_LIST,
    FAILURE_REGION_SPD,
    FAILURE_REGION_STA,
    FAILURE_REGION_PWR,
    FAILURE_REGION_GUTS,
    FAILURE_REGION_WIT,
)

from core_unity.state import (
    check_mood,
    check_current_year,
    check_criteria,
    check_goal_name,
    check_current_stats,
    check_energy_bar,
    check_dating_available,
)
from core_unity.training_handling import check_failure, go_to_training, check_training


ASSETS = {
    "tazuna_hint": "assets/ui/tazuna_hint.png",
    "training_btn": "assets/buttons/training_btn.png",
    "rest_btn": "assets/buttons/rest_btn.png",
    "rest_summer_btn": "assets/buttons/rest_summer_btn.png",
    "recreation_btn": "assets/buttons/recreation_btn.png",
    "infirmary_btn": "assets/buttons/infirmary_btn.png",
    "infirmary_btn2": "assets/buttons/infirmary_btn2.png",
}


def _check_asset(name: str, path: str, screenshot) -> Optional[tuple]:
    """Helper to locate a single asset on screen."""
    if not os.path.exists(path):
        log_warning(f"[{name}] asset not found on disk: {path}")
        return None

    # NOTE: current locate_on_screen implementation does not accept a screenshot parameter,
    # it captures internally, so we just call it with path + confidence.
    start = time.perf_counter()
    loc = locate_on_screen(path, confidence=0.8)
    elapsed = (time.perf_counter() - start) * 1000
    
    if loc:
        log_info(f"[{name}] FOUND at {loc} ({elapsed:.2f}ms)")
    else:
        log_warning(f"[{name}] NOT FOUND ({elapsed:.2f}ms)")
    return loc


def test_buttons_and_tazuna(screenshot) -> List[Tuple[str, Tuple[int, int]]]:
    log_info("\n=== BUTTON / UI ELEMENT CHECK ===")
    total_start = time.perf_counter()
    hits: List[Tuple[str, Tuple[int, int]]] = []

    loc = _check_asset("tazuna_hint", ASSETS["tazuna_hint"], screenshot)
    if loc:
        hits.append(("tazuna_hint", loc))

    loc = _check_asset("training_btn", ASSETS["training_btn"], screenshot)
    if loc:
        hits.append(("training_btn", loc))

    # Rest buttons (normal + summer)
    rest_loc = _check_asset("rest_btn", ASSETS["rest_btn"], screenshot)
    if rest_loc:
        hits.append(("rest_btn", rest_loc))
    else:
        rest_summer_loc = _check_asset("rest_summer_btn", ASSETS["rest_summer_btn"], screenshot)
        if rest_summer_loc:
            hits.append(("rest_summer_btn", rest_summer_loc))

    # Recreation buttons (normal + summer-rest reused in execute.py)
    recreation_loc = _check_asset("recreation_btn", ASSETS["recreation_btn"], screenshot)
    if recreation_loc:
        hits.append(("recreation_btn", recreation_loc))
    else:
        rec_summer_loc = _check_asset("rest_summer_btn (as recreation)", ASSETS["rest_summer_btn"], screenshot)
        if rec_summer_loc:
            hits.append(("recreation_summer_btn", rec_summer_loc))

    # Infirmary buttons
    infirmary_loc = _check_asset("infirmary_btn2", ASSETS["infirmary_btn2"], screenshot)
    if infirmary_loc:
        hits.append(("infirmary_btn2", infirmary_loc))
    else:
        infirmary_loc = _check_asset("infirmary_btn", ASSETS["infirmary_btn"], screenshot)
        if infirmary_loc:
            hits.append(("infirmary_btn", infirmary_loc))

    total_time = (time.perf_counter() - total_start) * 1000
    log_info(f"\nTotal button check time: {total_time:.2f}ms")
    return hits


def test_state_ocr(screenshot):
    log_info("\n=== STATE / OCR CHECK ===")
    total_start = time.perf_counter()
    step_times = {}

    # Mood
    step_start = time.perf_counter()
    mood = check_mood(screenshot)
    step_times["mood"] = (time.perf_counter() - step_start) * 1000
    log_info(f"Mood: {mood} (valid list: {MOOD_LIST}) ({step_times['mood']:.2f}ms)")

    # Year
    step_start = time.perf_counter()
    year = check_current_year(screenshot)
    step_times["year"] = (time.perf_counter() - step_start) * 1000
    log_info(f"Year: {year} ({step_times['year']:.2f}ms)")

    # Goal name
    step_start = time.perf_counter()
    goal_name = check_goal_name(screenshot)
    step_times["goal_name"] = (time.perf_counter() - step_start) * 1000
    log_info(f"Goal name: {goal_name} ({step_times['goal_name']:.2f}ms)")

    # Criteria/status text
    step_start = time.perf_counter()
    criteria_text = check_criteria(screenshot)
    step_times["criteria"] = (time.perf_counter() - step_start) * 1000
    log_info(f"Criteria text: {criteria_text} ({step_times['criteria']:.2f}ms)")

    # Stats
    step_start = time.perf_counter()
    stats = check_current_stats(screenshot)
    step_times["stats"] = (time.perf_counter() - step_start) * 1000
    log_info(
        f"Stats: "
        f"SPD={stats.get('spd', 0)}, "
        f"STA={stats.get('sta', 0)}, "
        f"PWR={stats.get('pwr', 0)}, "
        f"GUTS={stats.get('guts', 0)}, "
        f"WIT={stats.get('wit', 0)} "
        f"({step_times['stats']:.2f}ms)"
    )

    # Energy
    step_start = time.perf_counter()
    energy = check_energy_bar(screenshot)
    step_times["energy"] = (time.perf_counter() - step_start) * 1000
    log_info(f"Energy: {energy:.1f}% ({step_times['energy']:.2f}ms)")

    # Dating available
    step_start = time.perf_counter()
    dating = check_dating_available(screenshot)
    step_times["dating"] = (time.perf_counter() - step_start) * 1000
    log_info(f"Dating available: {dating} ({step_times['dating']:.2f}ms)")

    # Print timing summary
    total_time = (time.perf_counter() - total_start) * 1000
    log_info(f"\n=== TIMING SUMMARY ===")
    log_info(f"Total time: {total_time:.2f}ms")
    log_info(f"Breakdown:")
    for step_name, step_time in step_times.items():
        percentage = (step_time / total_time) * 100 if total_time > 0 else 0
        log_info(f"  {step_name:12s}: {step_time:7.2f}ms ({percentage:5.1f}%)")

    # Print regions for manual verification
    log_debug("\nRegions from utils.constants_unity:")
    log_debug(f"  MOOD_REGION={MOOD_REGION}")
    log_debug(f"  YEAR_REGION={YEAR_REGION}")
    log_debug(f"  CRITERIA_REGION={CRITERIA_REGION}")
    log_debug(f"  SPD_REGION={SPD_REGION}")
    log_debug(f"  STA_REGION={STA_REGION}")
    log_debug(f"  PWR_REGION={PWR_REGION}")
    log_debug(f"  GUTS_REGION={GUTS_REGION}")
    log_debug(f"  WIT_REGION={WIT_REGION}")
    log_debug(f"  SKILL_PTS_REGION={SKILL_PTS_REGION}")
    log_debug(f"  ENERGY (hardcoded in state.check_energy_bar)")


def test_failure_region(screenshot, train_type: str):
    """
    Test OCR on failure region for a single training type using check_failure.
    """
    train_type = train_type.lower()
    if train_type not in ["spd", "sta", "pwr", "guts", "wit"]:
        log_error(f"Invalid train_type '{train_type}'. Must be one of spd/sta/pwr/guts/wit.")
        return

    log_info(f"\n=== FAILURE REGION / OCR CHECK ({train_type.upper()}) ===")

    try:
        start = time.perf_counter()
        rate, conf = check_failure(screenshot, train_type)
        elapsed = (time.perf_counter() - start) * 1000
        log_info(f"[{train_type.upper()}] failure: {rate}% (confidence={conf:.2f}) ({elapsed:.2f}ms)")
    except Exception as e:
        elapsed = 0
        log_error(f"[{train_type.upper()}] failure check error: {e}")


def test_failure_all_normal(disable_input_delay=False):
    """
    Perform the normal in-game failure check flow for all stats via check_training().

    This will:
    - go_to_training() (tap the training button)
    - run check_training(), which hovers each training, shows failure %, and OCRs it
    - log the resulting failure rates from the returned dict
    
    Args:
        disable_input_delay: If True, temporarily set input_delay to 0.0 for this test
    """
    log_info("\n=== FAILURE REGION / NORMAL FLOW CHECK (ALL STATS) ===")
    
    # Handle input_delay modification if requested
    original_delay = None
    config_modified = False
    if disable_input_delay:
        log_info("⚠️  Testing with input_delay DISABLED (set to 0.0)")
        try:
            import json
            # Read current config
            with open('config.json', 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # Save original delay
            adb_config = config.get('adb_config', {})
            original_delay = adb_config.get('input_delay', 0.5)
            log_info(f"  Original input_delay: {original_delay}s")
            
            # Set to 0.0
            if 'adb_config' not in config:
                config['adb_config'] = {}
            config['adb_config']['input_delay'] = 0.0
            
            # Write back
            with open('config.json', 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            
            config_modified = True
            log_info(f"  Temporarily set input_delay to: 0.0s")
            log_info(f"  (Will restore to {original_delay}s after test)\n")
            
            # Force reload by clearing any cached config
            import utils.device
            if hasattr(utils.device, '_cached_config'):
                delattr(utils.device, '_cached_config')
                
        except Exception as e:
            log_warning(f"  Failed to modify input_delay: {e}")
            log_warning(f"  Continuing with current config...\n")
    
    total_start = time.perf_counter()

    # Go to training screen
    step_start = time.perf_counter()
    if not go_to_training():
        log_error("Could not go to training screen (training_btn not found). Make sure training screen is available.")
        # Restore config if modified
        if config_modified:
            _restore_input_delay(original_delay)
        return None, None
    go_to_training_time = (time.perf_counter() - step_start) * 1000
    log_info(f"Go to training screen: {go_to_training_time:.2f}ms")

    # Let screen stabilize a bit
    step_start = time.perf_counter()
    time.sleep(0.5)
    sleep_time = (time.perf_counter() - step_start) * 1000
    log_info(f"Screen stabilization: {sleep_time:.2f}ms")

    # This will perform the usual swipe/hover + OCR for each stat
    step_start = time.perf_counter()
    results = check_training()
    check_training_time = (time.perf_counter() - step_start) * 1000

    if not results:
        log_warning("check_training() returned no results.")
        return None, None

    # Log a compact summary
    log_info(f"\ncheck_training() total time: {check_training_time:.2f}ms")
    for key in ["spd", "sta", "pwr", "guts", "wit"]:
        if key in results:
            data = results[key]
            fail = data.get("failure", None)
            conf = data.get("confidence", None)
            conf_str = f"{conf:.2f}" if conf is not None else "0.0"
            log_info(f"[{key.upper()}] failure: {fail}% (confidence={conf_str})")

    # Take a screenshot for plotting after the training check
    step_start = time.perf_counter()
    screenshot = take_screenshot()
    screenshot_time = (time.perf_counter() - step_start) * 1000
    
    total_time = (time.perf_counter() - total_start) * 1000
    log_info(f"\n=== TIMING SUMMARY ===")
    log_info(f"Total time: {total_time:.2f}ms")
    log_info(f"Breakdown:")
    log_info(f"  go_to_training:  {go_to_training_time:7.2f}ms")
    log_info(f"  sleep (0.5s):    {sleep_time:7.2f}ms")
    log_info(f"  check_training:  {check_training_time:7.2f}ms")
    log_info(f"  screenshot:      {screenshot_time:7.2f}ms")
    
    # Restore original input_delay if modified
    if config_modified:
        _restore_input_delay(original_delay)
        log_info(f"\n✓ Restored input_delay to: {original_delay}s")
    
    return screenshot, results


def _restore_input_delay(original_delay):
    """Restore input_delay to original value"""
    try:
        import json
        with open('config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        if 'adb_config' not in config:
            config['adb_config'] = {}
        config['adb_config']['input_delay'] = original_delay
        
        with open('config.json', 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
    except Exception as e:
        log_error(f"Failed to restore input_delay: {e}")


def save_debug_plot(
    screenshot,
    button_hits: Optional[List[Tuple[str, Tuple[int, int]]]] = None,
    failure_train_type: Optional[str] = None,
    out_path: str = "unity_test/debug_unity_regions.png",
):
    """
    Save a PNG with the screenshot and all important bounding boxes / hit points drawn.
    """
    try:
        start = time.perf_counter()
        img = screenshot.convert("RGB").copy()
        draw = ImageDraw.Draw(img)

        # Region rectangles (constants from utils.constants_unity)
        regions = [
            ("MOOD", MOOD_REGION, "red"),
            ("YEAR", YEAR_REGION, "orange"),
            ("CRITERIA", CRITERIA_REGION, "yellow"),
            ("SPD", SPD_REGION, "lime"),
            ("STA", STA_REGION, "green"),
            ("PWR", PWR_REGION, "cyan"),
            ("GUTS", GUTS_REGION, "blue"),
            ("WIT", WIT_REGION, "magenta"),
            ("SKILL_PTS", SKILL_PTS_REGION, "white"),
        ]

        # Energy bar region (from check_energy_bar in core_unity.state)
        # Hardcoded there as (x=330, y=203, w=602, h=72)
        energy_region = (330, 203, 330 + 602, 203 + 72)
        regions.append(("ENERGY", energy_region, "pink"))

        # Optionally draw failure regions depending on mode
        if failure_train_type:
            ft = failure_train_type.lower()
            if ft == "all":
                regions.extend(
                    [
                        ("SPD_FAIL", FAILURE_REGION_SPD, "red"),
                        ("STA_FAIL", FAILURE_REGION_STA, "orange"),
                        ("PWR_FAIL", FAILURE_REGION_PWR, "yellow"),
                        ("GUTS_FAIL", FAILURE_REGION_GUTS, "green"),
                        ("WIT_FAIL", FAILURE_REGION_WIT, "cyan"),
                    ]
                )
            else:
                if ft == "spd":
                    regions.append(("SPD_FAIL", FAILURE_REGION_SPD, "red"))
                elif ft == "sta":
                    regions.append(("STA_FAIL", FAILURE_REGION_STA, "orange"))
                elif ft == "pwr":
                    regions.append(("PWR_FAIL", FAILURE_REGION_PWR, "yellow"))
                elif ft == "guts":
                    regions.append(("GUTS_FAIL", FAILURE_REGION_GUTS, "green"))
                elif ft == "wit":
                    regions.append(("WIT_FAIL", FAILURE_REGION_WIT, "cyan"))

        for name, (left, top, right, bottom), color in regions:
            draw.rectangle([left, top, right, bottom], outline=color, width=3)
            # Small label in the corner
            draw.text((left + 3, top + 3), name, fill=color)

        # Draw centers for detected buttons (if any)
        if button_hits:
            for name, (cx, cy) in button_hits:
                r = 10
                draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline="yellow", width=3)
                draw.text((cx + r + 2, cy), name, fill="yellow")

        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        img.save(out_path)
        elapsed = (time.perf_counter() - start) * 1000
        log_info(f"Saved debug region plot to: {out_path} ({elapsed:.2f}ms)")
    except Exception as e:
        log_error(f"Failed to save debug plot: {e}")


def main():
    args = sys.argv[1:]

    if not args or args[0] in ("-h", "--help"):
        log_info("Unity Test - Region / Detection Check")
        log_info("=" * 50)
        log_info("Usage:")
        log_info("  python -m unity_test.test_unity_regions buttons")
        log_info("  python -m unity_test.test_unity_regions state")
        log_info("  python -m unity_test.test_unity_regions failure <spd|sta|pwr|guts|wit> [--hover]")
        log_info("  python -m unity_test.test_unity_regions failure_all [--no-delay]")
        log_info("\nOptions:")
        log_info("  --hover       For failure mode: automatically hover over training type first")
        log_info("  --no-delay    Disable input_delay for failure_all test (temporarily sets to 0.0)")
        log_info("\nExamples:")
        log_info("  python -m unity_test.test_unity_regions failure spd --hover")
        log_info("  python -m unity_test.test_unity_regions failure_all --no-delay")
        return

    mode = args[0].lower()

    if mode == "buttons":
        log_info("Mode: BUTTONS")
        log_info("Make sure lobby screen with buttons is visible.")
        screenshot_start = time.perf_counter()
        screenshot = take_screenshot()
        screenshot_time = (time.perf_counter() - screenshot_start) * 1000
        log_info(f"Screenshot capture: {screenshot_time:.2f}ms")
        
        button_hits = test_buttons_and_tazuna(screenshot)
        save_debug_plot(screenshot, button_hits=button_hits, failure_train_type=None)

    elif mode == "state":
        log_info("Mode: STATE")
        log_info("Make sure a normal turn/lobby screen is visible.")
        screenshot_start = time.perf_counter()
        screenshot = take_screenshot()
        screenshot_time = (time.perf_counter() - screenshot_start) * 1000
        log_info(f"Screenshot capture: {screenshot_time:.2f}ms")
        
        test_state_ocr(screenshot)
        save_debug_plot(screenshot, button_hits=None, failure_train_type=None)

    elif mode == "failure":
        if len(args) < 2:
            log_error("Failure mode requires a training type: spd/sta/pwr/guts/wit")
            return
        train_type = args[1].lower()
        if train_type not in ["spd", "sta", "pwr", "guts", "wit"]:
            log_error(f"Invalid training type '{train_type}'. Must be one of spd/sta/pwr/guts/wit.")
            return

        # Check if user wants to hover first (--hover or -h flag)
        hover_first = "--hover" in args or "-h" in args
        
        if hover_first:
            log_info(f"Mode: FAILURE ({train_type.upper()}) - WITH HOVER")
            log_info("Make sure you're in career lobby (bot will navigate and hover).")
            
            # Go to training screen
            from core_unity.training_handling import go_to_training
            step_start = time.perf_counter()
            if not go_to_training():
                log_error("Could not go to training screen (training_btn not found).")
                return
            go_to_training_time = (time.perf_counter() - step_start) * 1000
            log_info(f"Go to training screen: {go_to_training_time:.2f}ms")
            
            # Wait for stabilization
            time.sleep(0.5)
            
            # Hover over the training type
            from utils.input import swipe
            training_coords = {
                "spd": (165, 1557),
                "sta": (357, 1563),
                "pwr": (546, 1557),
                "guts": (735, 1566),
                "wit": (936, 1572)
            }
            coords = training_coords[train_type]
            start_x, start_y = coords
            end_x, end_y = start_x, start_y - 200
            
            log_info(f"Hovering over {train_type.upper()} training...")
            hover_start = time.perf_counter()
            swipe(start_x, start_y, end_x, end_y, duration_ms=100)
            time.sleep(0.1)
            hover_time = (time.perf_counter() - hover_start) * 1000
            log_info(f"Hover completed: {hover_time:.2f}ms")
        else:
            log_info(f"Mode: FAILURE ({train_type.upper()})")
            log_info("Make sure training screen is visible with failure % showing.")
            log_info("(Use --hover flag to automatically hover first)")
        
        screenshot_start = time.perf_counter()
        screenshot = take_screenshot()
        screenshot_time = (time.perf_counter() - screenshot_start) * 1000
        log_info(f"Screenshot capture: {screenshot_time:.2f}ms")
        
        test_failure_region(screenshot, train_type)
        save_debug_plot(screenshot, button_hits=None, failure_train_type=train_type)

    elif mode == "failure_all":
        # Check for --no-delay flag
        disable_delay = "--no-delay" in args or "-n" in args
        if disable_delay:
            log_info("Mode: FAILURE_ALL (normal flow via check_training) - WITH NO INPUT DELAY")
        else:
            log_info("Mode: FAILURE_ALL (normal flow via check_training)")
        log_info("Make sure training screen is reachable (bot will tap training button).")

        screenshot, _results = test_failure_all_normal(disable_input_delay=disable_delay)
        if screenshot is not None:
            save_debug_plot(screenshot, button_hits=None, failure_train_type="all")

    else:
        log_error(f"Unknown mode '{mode}'. Use buttons/state/failure or -h for help.")

    log_info("\nDone. Use these results to adjust regions in `utils/constants_unity.py`.")


if __name__ == "__main__":
    main()


