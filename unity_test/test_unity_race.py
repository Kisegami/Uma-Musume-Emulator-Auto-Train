"""
Manual test runner for the Unity Race workflow.

Run from project root:

    python -m unity_test.test_unity_race

Make sure:
- You are in the lobby where the Unity Cup button is visible.
- The screen is stable (no popups blocking buttons).

This script will:
- Log a quick pre-check for Unity Cup and Unity Race buttons.
- Invoke core_unity.unity_race_handling.unity_race_workflow() once.
- Report success/failure and how long it took.
"""

import time

from utils_unity.log import log_info, log_warning, log_error, log_debug
from utils_unity.recognizer import locate_on_screen
from utils_unity.screenshot import take_screenshot

from core_unity.unity_race_handling import unity_race_workflow


def precheck():
    """
    Optional pre-check to see if key buttons are on screen before running.
    """
    cup = locate_on_screen("assets/unity/unity_cup.png", confidence=0.8)
    race_btn = locate_on_screen("assets/unity/unity_race.png", confidence=0.8)

    log_info(f"Precheck - Unity Cup present: {bool(cup)}; Unity Race button present: {bool(race_btn)}")


def main():
    log_info("Unity Race Test Runner")
    log_info("=" * 40)
    log_info("Ensure Unity Cup (and Unity Race) is visible in lobby before running.")

    precheck()

    start = time.time()
    try:
        ok = unity_race_workflow()
        elapsed = time.time() - start
        if ok:
            log_info(f"Unity race workflow completed successfully in {elapsed:.2f}s")
        else:
            log_warning(f"Unity race workflow returned False (elapsed {elapsed:.2f}s)")
    except Exception as e:
        elapsed = time.time() - start
        log_error(f"Unity race workflow error after {elapsed:.2f}s: {e}")


if __name__ == "__main__":
    main()


