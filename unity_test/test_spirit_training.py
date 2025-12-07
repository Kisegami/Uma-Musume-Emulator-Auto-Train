"""
Standalone test for Unity/Spirit training detection with location output.

Run from project root:

    python -m unity_test.test_spirit_training

It will:
- Capture 10 screenshots on the training screen
- For each screenshot, detect spirit_training icons and their locations
- Print per-shot counts and x,y coordinates (center of each icon)
- Print average count and a detection-confidence metric
- Save an overlay image for the last screenshot:
  unity_test/debug_spirit_training_overlay.png
"""

import os
from typing import List, Tuple

from PIL import ImageDraw

from utils.log import log_info, log_warning, log_error, log_debug
from utils.screenshot import take_screenshot
from utils.recognizer import match_template
from utils.template_matching import deduplicated_matches
from utils.constants_unity import SUPPORT_CARD_ICON_REGION


TEMPLATE_PATH = "assets/unity/spirit_training.png"
BURST_ED_TEMPLATE = "assets/unity/burst_ed.png"

# Offset from spirit training center to check region for burst_ed.png
# Based on example: Spirit Training center (1018, 643) => check region (990, 667, 1056, 784) in (x1, y1, x2, y2) format
REGION_WIDTH = 66
REGION_HEIGHT = 117
LEFT_OFFSET = -28  # 28 pixels to the left of spirit training center
TOP_OFFSET = 24    # 24 pixels below spirit training center (positive = below)


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


def check_spirit_training_extra(screenshot, spirit_training_boxes: List[Tuple[int, int, int, int]]) -> List[Tuple[int, int, int, int, bool, int, int, int, int]]:
    """
    Check for burst_ed.png under each spirit training location.
    
    Returns:
        List of tuples: (x, y, w, h, has_burst_ed, region_left, region_top, region_right, region_bottom) for each spirit training icon
    """
    if not spirit_training_boxes:
        return []
    
    if not os.path.exists(BURST_ED_TEMPLATE):
        log_warning(f"Burst_ed template not found: {BURST_ED_TEMPLATE}")
        return [(x, y, w, h, False, 0, 0, 0, 0) for x, y, w, h in spirit_training_boxes]
    
    results = []
    img_width, img_height = screenshot.size
    
    for x, y, w, h in spirit_training_boxes:
        # Calculate spirit training center
        center_x = x + w // 2
        center_y = y + h // 2
        
        # Calculate region to check (x1, y1, x2, y2) format = (left, top, right, bottom)
        region_left = center_x + LEFT_OFFSET
        region_top = center_y + TOP_OFFSET
        region_right = region_left + REGION_WIDTH
        region_bottom = region_top + REGION_HEIGHT
        
        # Store original region before bounds clamping (x1, y1, x2, y2)
        original_region = (region_left, region_top, region_right, region_bottom)
        
        # Ensure region is within screenshot bounds
        region_left = max(0, min(img_width - 1, region_left))
        region_top = max(0, min(img_height - 1, region_top))
        region_right = max(region_left + 1, min(img_width, region_right))
        region_bottom = max(region_top + 1, min(img_height, region_bottom))
        
        # Convert to OpenCV format (x, y, width, height)
        region_cv = (region_left, region_top, region_right - region_left, region_bottom - region_top)
        
        # Check for burst_ed.png in this region
        matches = match_template(screenshot, BURST_ED_TEMPLATE, confidence=0.8, region=region_cv)
        has_burst_ed = bool(matches)
        
        results.append((x, y, w, h, has_burst_ed, original_region[0], original_region[1], original_region[2], original_region[3]))
        
        if has_burst_ed:
            log_debug(f"  Found burst_ed.png below spirit training at ({center_x}, {center_y}) in region {region_cv}")
    
    return results


def save_overlay(screenshot, boxes: List[Tuple[int, int, int, int]], extra_info: List[Tuple[int, int, int, int, bool]] = None, out_path: str = "unity_test/debug_spirit_training_overlay.png"):
    """Save screenshot with SUPPORT_CARD_ICON_REGION and detected spirit icons drawn."""
    try:
        img = screenshot.convert("RGB").copy()
        draw = ImageDraw.Draw(img)

        # Draw overall support-card region
        left, top, right, bottom = SUPPORT_CARD_ICON_REGION
        draw.rectangle([left, top, right, bottom], outline="cyan", width=3)
        draw.text((left + 3, top + 3), "SUPPORT_CARD_ICON_REGION", fill="cyan")

        # Draw each detected icon with coordinates
        for idx, box_data in enumerate(boxes, start=1):
            if extra_info and idx <= len(extra_info):
                x, y, w, h, has_burst_ed, region_left, region_top, region_right, region_bottom = extra_info[idx - 1]
                color = "lime" if has_burst_ed else "yellow"
                extra_label = " [EXTRA]" if has_burst_ed else ""
            else:
                x, y, w, h = box_data
                color = "yellow"
                extra_label = ""
                region_left = region_top = region_right = region_bottom = 0
            
            center_x = x + w // 2
            center_y = y + h // 2
            draw.rectangle([x, y, x + w, y + h], outline=color, width=3)
            # Draw center point
            draw.ellipse([center_x - 3, center_y - 3, center_x + 3, center_y + 3], fill=color, outline=color)
            draw.text((x + 2, y + 2), f"SPIRIT#{idx}{extra_label}", fill=color)
            draw.text((x + 2, y + 18), f"({center_x},{center_y})", fill=color)
            
            # Draw burst_ed check region for all spirit training icons (not just those with burst_ed)
            if extra_info and idx <= len(extra_info):
                draw.rectangle([region_left, region_top, region_right, region_bottom], outline="orange", width=2)
                draw.text((region_left + 2, region_top + 2), "BURST_ED_REGION", fill="orange")
                if has_burst_ed:
                    draw.rectangle([region_left, region_top, region_right, region_bottom], outline="lime", width=2)
                    draw.text((region_left + 2, region_top + 2), "BURST_ED ✓", fill="lime")

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
    extra_counts: List[int] = []
    last_screenshot = None
    last_boxes: List[Tuple[int, int, int, int]] = []
    last_extra_info: List[Tuple[int, int, int, int, bool, int, int, int, int]] = []

    for i in range(10):
        time.sleep(0.2)  # small delay between captures
        screenshot = take_screenshot()
        boxes = detect_spirit_training(screenshot)
        count = len(boxes)
        
        # Check for spirit training extra (after burst)
        extra_info = check_spirit_training_extra(screenshot, boxes)
        extra_count = sum(1 for _, _, _, _, has_extra, _, _, _, _ in extra_info if has_extra)

        counts.append(count)
        extra_counts.append(extra_count)
        last_screenshot = screenshot
        last_boxes = boxes
        last_extra_info = extra_info

        # Output count and locations
        log_info(f"[{i+1}/10] Spirit/unity icons detected: {count} (extra: {extra_count})")
        if boxes:
            for idx, box_info in enumerate(extra_info, start=1):
                x, y, w, h, has_burst_ed, region_left, region_top, region_right, region_bottom = box_info
                center_x = x + w // 2
                center_y = y + h // 2
                extra_label = " [SPIRIT TRAINING EXTRA - After Burst]" if has_burst_ed else ""
                log_info(f"  Spirit Training #{idx}: Location (x={center_x}, y={center_y}) | Bounding box: ({x}, {y}, {w}, {h}){extra_label}")
                log_info(f"    Extra region (burst_ed check) [x1, y1, x2, y2]: ({region_left}, {region_top}, {region_right}, {region_bottom})")
        else:
            log_info("  No spirit training icons found in this screenshot")

    total = sum(counts)
    total_extra = sum(extra_counts)
    avg = total / len(counts) if counts else 0.0
    avg_extra = total_extra / len(extra_counts) if extra_counts else 0.0
    frames_with_any = sum(1 for c in counts if c > 0)
    frames_with_extra = sum(1 for c in extra_counts if c > 0)
    confidence = frames_with_any / len(counts) if counts else 0.0
    extra_confidence = frames_with_extra / len(extra_counts) if extra_counts else 0.0

    log_info("")
    log_info("=" * 50)
    log_info("SUMMARY")
    log_info("=" * 50)
    log_info(f"Total icons over 10 samples: {total}")
    log_info(f"Average icons per screenshot: {avg:.2f}")
    log_info(f"Detection confidence (frames with ≥1 hit): {frames_with_any}/10 ({confidence*100:.1f}%)")
    log_info("")
    log_info(f"Total spirit training extra (after burst) over 10 samples: {total_extra}")
    log_info(f"Average spirit training extra per screenshot: {avg_extra:.2f}")
    log_info(f"Spirit training extra confidence (frames with ≥1 hit): {frames_with_extra}/10 ({extra_confidence*100:.1f}%)")
    
    # Output final screenshot details
    if last_screenshot is not None and last_boxes:
        log_info("")
        log_info("Final screenshot spirit training locations:")
        for idx, box_info in enumerate(last_extra_info, start=1):
            x, y, w, h, has_burst_ed, region_left, region_top, region_right, region_bottom = box_info
            center_x = x + w // 2
            center_y = y + h // 2
            extra_label = " [SPIRIT TRAINING EXTRA - After Burst]" if has_burst_ed else ""
            log_info(f"  Spirit Training #{idx}: Center (x={center_x}, y={center_y}) | Top-left ({x}, {y}) | Size {w}x{h}{extra_label}")
            log_info(f"    Extra region (burst_ed check) [x1, y1, x2, y2]: ({region_left}, {region_top}, {region_right}, {region_bottom})")
        save_overlay(last_screenshot, last_boxes, last_extra_info)
        log_info("")
        log_info(f"Overlay image saved to: unity_test/debug_spirit_training_overlay.png")
    elif last_screenshot is not None:
        log_info("")
        log_info("No spirit training icons found in final screenshot")
        save_overlay(last_screenshot, last_boxes, [])


if __name__ == "__main__":
    main()



