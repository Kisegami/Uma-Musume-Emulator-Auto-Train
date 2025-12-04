"""
Standalone test for Unity/Spirit training count over multiple screenshots.

Run from project root:

    python -m unity_test.test_spirit_training

It will:
- Capture 10 screenshots on the training screen
- For each screenshot, count spirit_training icons
- Print per-shot counts
- Print average count and a detection-confidence metric
- Save an overlay image for the last screenshot:
  unity_test/debug_spirit_training_overlay.png
"""

import os
from typing import List, Tuple

from PIL import ImageDraw

from utils_unity.log import log_info, log_warning, log_error, log_debug
from utils_unity.screenshot import take_screenshot
from utils_unity.recognizer import match_template
from utils_unity.template_matching import deduplicated_matches
from utils_unity.constants_phone import SUPPORT_CARD_ICON_REGION


TEMPLATE_PATH = "assets/unity/spirit_training.png"


def detect_spirit_training(screenshot) -> List[Tuple[int, int, int, int]]:
    """Return bounding boxes (x, y, w, h) of spirit training icons in the configured region."""
    if not os.path.exists(TEMPLATE_PATH):
        log_warning(f"Spirit training template not found: {TEMPLATE_PATH}")
        return []

    left, top, right, bottom = SUPPORT_CARD_ICON_REGION
    region_cv = (left, top, right - left, bottom - top)
    log_debug(f"Searching spirit training icons in region {region_cv} using {TEMPLATE_PATH}")

    matches = match_template(screenshot, TEMPLATE_PATH, confidence=0.8, region=region_cv)
    filtered = deduplicated_matches(matches, threshold=30) if matches else []

    log_debug(f"Raw matches: {matches}")
    log_debug(f"Filtered matches: {filtered}")
    return filtered or []


def save_overlay(screenshot, boxes: List[Tuple[int, int, int, int]], out_path: str = "unity_test/debug_spirit_training_overlay.png"):
    """Save screenshot with SUPPORT_CARD_ICON_REGION and detected spirit icons drawn."""
    try:
        img = screenshot.convert("RGB").copy()
        draw = ImageDraw.Draw(img)

        # Draw overall support-card region
        left, top, right, bottom = SUPPORT_CARD_ICON_REGION
        draw.rectangle([left, top, right, bottom], outline="cyan", width=3)
        draw.text((left + 3, top + 3), "SUPPORT_CARD_ICON_REGION", fill="cyan")

        # Draw each detected icon
        for idx, (x, y, w, h) in enumerate(boxes, start=1):
            draw.rectangle([x, y, x + w, y + h], outline="yellow", width=3)
            draw.text((x + 2, y + 2), f"SPIRIT#{idx}", fill="yellow")

        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        img.save(out_path)
        log_info(f"Saved spirit training overlay to: {out_path}")
    except Exception as e:
        log_error(f"Failed to save spirit training overlay: {e}")


def main():
    import time

    log_info("Unity Test - Spirit Training Count (10 samples)")
    log_info("=" * 50)
    log_info("Make sure training screen is visible with spirit/unity icons.")
    log_info("Capturing 10 screenshots and detecting spirit training icons...\n")

    counts: List[int] = []
    last_screenshot = None
    last_boxes: List[Tuple[int, int, int, int]] = []

    for i in range(10):
        time.sleep(0.2)  # small delay between captures
        screenshot = take_screenshot()
        boxes = detect_spirit_training(screenshot)
        count = len(boxes)

        counts.append(count)
        last_screenshot = screenshot
        last_boxes = boxes

        log_info(f"[{i+1}/10] Spirit/unity icons detected: {count}")

    total = sum(counts)
    avg = total / len(counts) if counts else 0.0
    frames_with_any = sum(1 for c in counts if c > 0)
    confidence = frames_with_any / len(counts) if counts else 0.0

    log_info("")
    log_info(f"Total icons over 10 samples: {total}")
    log_info(f"Average icons per screenshot: {avg:.2f}")
    log_info(f"Detection confidence (frames with ≥1 hit): {frames_with_any}/10 ({confidence*100:.1f}%)")

    if last_screenshot is not None:
        save_overlay(last_screenshot, last_boxes)


if __name__ == "__main__":
    main()



