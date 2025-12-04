"""
Standalone region/detection test for Unity Cup using `utils_unity/constants_phone.py`.

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
from typing import Optional, List, Tuple

from PIL import ImageDraw

from utils_unity.log import log_info, log_warning, log_error, log_debug
from utils_unity.screenshot import take_screenshot
from utils_unity.recognizer import locate_on_screen, match_template
from utils_unity.constants_phone import (
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
    loc = locate_on_screen(path, confidence=0.8)
    if loc:
        log_info(f"[{name}] FOUND at {loc}")
    else:
        log_warning(f"[{name}] NOT FOUND")
    return loc


def test_buttons_and_tazuna(screenshot) -> List[Tuple[str, Tuple[int, int]]]:
    log_info("\n=== BUTTON / UI ELEMENT CHECK ===")
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

    return hits


def test_state_ocr(screenshot):
    log_info("\n=== STATE / OCR CHECK ===")

    # Mood
    mood = check_mood(screenshot)
    log_info(f"Mood: {mood} (valid list: {MOOD_LIST})")

    # Year
    year = check_current_year(screenshot)
    log_info(f"Year: {year}")

    # Goal name
    goal_name = check_goal_name(screenshot)
    log_info(f"Goal name: {goal_name}")

    # Criteria/status text
    criteria_text = check_criteria(screenshot)
    log_info(f"Criteria text: {criteria_text}")

    # Stats
    stats = check_current_stats(screenshot)
    log_info(
        "Stats: "
        f"SPD={stats.get('spd', 0)}, "
        f"STA={stats.get('sta', 0)}, "
        f"PWR={stats.get('pwr', 0)}, "
        f"GUTS={stats.get('guts', 0)}, "
        f"WIT={stats.get('wit', 0)}"
    )

    # Energy
    energy = check_energy_bar(screenshot)
    log_info(f"Energy: {energy:.1f}%")

    # Dating available
    dating = check_dating_available(screenshot)
    log_info(f"Dating available: {dating}")

    # Print regions for manual verification
    log_debug("\nRegions from utils_unity.constants_phone:")
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
        rate, conf = check_failure(screenshot, train_type)
        log_info(f"[{train_type.upper()}] failure: {rate}% (confidence={conf:.2f})")
    except Exception as e:
        log_error(f"[{train_type.upper()}] failure check error: {e}")


def test_failure_all_normal():
    """
    Perform the normal in-game failure check flow for all stats via check_training().

    This will:
    - go_to_training() (tap the training button)
    - run check_training(), which hovers each training, shows failure %, and OCRs it
    - log the resulting failure rates from the returned dict
    """
    log_info("\n=== FAILURE REGION / NORMAL FLOW CHECK (ALL STATS) ===")

    # Go to training screen
    if not go_to_training():
        log_error("Could not go to training screen (training_btn not found). Make sure training screen is available.")
        return None, None

    # Let screen stabilize a bit
    import time as _time
    _time.sleep(0.5)

    # This will perform the usual swipe/hover + OCR for each stat
    results = check_training()

    if not results:
        log_warning("check_training() returned no results.")
        return None, None

    # Log a compact summary
    for key in ["spd", "sta", "pwr", "guts", "wit"]:
        if key in results:
            data = results[key]
            fail = data.get("failure", None)
            conf = data.get("confidence", None)
            log_info(f"[{key.upper()}] failure: {fail}% (confidence={conf:.2f} if conf is not None else 0.0)")

    # Take a screenshot for plotting after the training check
    screenshot = take_screenshot()
    return screenshot, results


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
        img = screenshot.convert("RGB").copy()
        draw = ImageDraw.Draw(img)

        # Region rectangles (constants from utils_unity.constants_phone)
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
        log_info(f"Saved debug region plot to: {out_path}")
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
        log_info("  python -m unity_test.test_unity_regions failure <spd|sta|pwr|guts|wit>")
        log_info("  python -m unity_test.test_unity_regions failure_all")
        return

    mode = args[0].lower()

    if mode == "buttons":
        log_info("Mode: BUTTONS")
        log_info("Make sure lobby screen with buttons is visible.")
        screenshot = take_screenshot()
        button_hits = test_buttons_and_tazuna(screenshot)
        save_debug_plot(screenshot, button_hits=button_hits, failure_train_type=None)

    elif mode == "state":
        log_info("Mode: STATE")
        log_info("Make sure a normal turn/lobby screen is visible.")
        screenshot = take_screenshot()
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

        log_info(f"Mode: FAILURE ({train_type.upper()})")
        log_info("Make sure training screen is visible with failure % showing.")
        screenshot = take_screenshot()
        test_failure_region(screenshot, train_type)
        save_debug_plot(screenshot, button_hits=None, failure_train_type=train_type)

    elif mode == "failure_all":
        log_info("Mode: FAILURE_ALL (normal flow via check_training)")
        log_info("Make sure training screen is reachable (bot will tap training button).")

        screenshot, _results = test_failure_all_normal()
        if screenshot is not None:
            save_debug_plot(screenshot, button_hits=None, failure_train_type="all")

    else:
        log_error(f"Unknown mode '{mode}'. Use buttons/state/failure or -h for help.")

    log_info("\nDone. Use these results to adjust regions in `utils_unity/constants_phone.py`.")


if __name__ == "__main__":
    main()


