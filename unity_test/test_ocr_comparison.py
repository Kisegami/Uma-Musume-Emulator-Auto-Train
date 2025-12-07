"""
Compare PaddleOCR vs Tesseract OCR speed on failure rate region.

This test:
1. Hovers over SPD training to show failure rate
2. Captures the failure region
3. Tests both OCR engines with direct OCR (no preprocessing)
4. Compares speed and accuracy

Run from project root:
    python -m unity_test.test_ocr_comparison
"""

import os
import sys
import time
import re

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.log import log_info, log_warning, log_error, log_debug
from utils.screenshot import take_screenshot
from utils.input import swipe
from utils.constants_unity import FAILURE_REGION_SPD
from core_unity.training_handling import go_to_training

# Try to import PaddleOCR TextRecognition
try:
    from paddleocr import TextRecognition
    PADDLEOCR_AVAILABLE = True
except ImportError:
    PADDLEOCR_AVAILABLE = False
    log_warning("PaddleOCR not installed. Install with: pip install paddleocr")

# Import Tesseract
try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False
    log_error("pytesseract not available")

import numpy as np
from PIL import Image


def ocr_tesseract_direct(image):
    """
    Direct OCR using Tesseract with no preprocessing.
    
    Args:
        image: PIL Image or numpy array
        
    Returns:
        tuple: (text, time_ms)
    """
    if not TESSERACT_AVAILABLE:
        return None, 0
    
    try:
        # Convert to numpy if PIL Image
        if isinstance(image, Image.Image):
            img_np = np.array(image)
        else:
            img_np = image
        
        start = time.perf_counter()
        # Direct OCR - no preprocessing, no special config
        text = pytesseract.image_to_string(img_np, lang='eng', config='--oem 3 --psm 6')
        elapsed = (time.perf_counter() - start) * 1000
        
        return text.strip(), elapsed
    except Exception as e:
        log_error(f"Tesseract OCR error: {e}")
        return None, 0


def ocr_paddleocr_direct(image):
    """
    Direct OCR using PaddleOCR TextRecognition (simple API).
    
    Args:
        image: PIL Image or numpy array
        
    Returns:
        tuple: (text, time_ms)
    """
    if not PADDLEOCR_AVAILABLE:
        return None, 0
    
    try:
        # Initialize TextRecognition model (only once, reuse)
        if not hasattr(ocr_paddleocr_direct, '_model'):
            log_info("Initializing PaddleOCR TextRecognition (first time may be slow)...")
            init_start = time.perf_counter()
            ocr_paddleocr_direct._model = TextRecognition()
            init_time = (time.perf_counter() - init_start) * 1000
            log_info(f"PaddleOCR initialized in {init_time:.2f}ms")
        
        # Save image to temp file (TextRecognition expects file path)
        import tempfile
        temp_file = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
        try:
            if isinstance(image, Image.Image):
                image.save(temp_file.name)
            else:
                Image.fromarray(image).save(temp_file.name)
            img_path = temp_file.name
        except Exception as e:
            log_error(f"Failed to save temp image: {e}")
            temp_file.close()
            os.unlink(temp_file.name)
            return None, 0
        
        # Run OCR
        start = time.perf_counter()
        output = ocr_paddleocr_direct._model.predict(input=img_path)
        elapsed = (time.perf_counter() - start) * 1000
        
        # Clean up temp file
        try:
            temp_file.close()
            os.unlink(img_path)
        except:
            pass
        
        # Extract text from result
        # Format: {'res': {'rec_text': '...', 'rec_score': 0.99, ...}}
        texts = []
        
        # Debug: log result structure on first run
        if not hasattr(ocr_paddleocr_direct, '_debug_logged'):
            log_info(f"DEBUG: PaddleOCR output type: {type(output)}")
            log_info(f"DEBUG: PaddleOCR output: {output}")
            try:
                output_list = list(output) if not isinstance(output, (list, tuple)) else output
                log_info(f"DEBUG: Output length: {len(output_list) if output_list else 0}")
                if output_list and len(output_list) > 0:
                    log_info(f"DEBUG: First result type: {type(output_list[0])}")
                    log_info(f"DEBUG: First result: {output_list[0]}")
                    if isinstance(output_list[0], dict):
                        log_info(f"DEBUG: First result keys: {list(output_list[0].keys())}")
            except Exception as e:
                log_info(f"DEBUG: Error inspecting output: {e}")
            ocr_paddleocr_direct._debug_logged = True
        
        for res in output:
            if isinstance(res, dict):
                # Try different formats
                if 'res' in res and isinstance(res['res'], dict):
                    # Format: {'res': {'rec_text': '...', 'rec_score': 0.99}}
                    rec_data = res['res']
                    if 'rec_text' in rec_data and rec_data['rec_text']:
                        texts.append(str(rec_data['rec_text']))
                elif 'rec_text' in res:
                    # Direct format: {'rec_text': '...', 'rec_score': 0.99}
                    if res['rec_text']:
                        texts.append(str(res['rec_text']))
        
        text = " ".join(texts) if texts else ""
        return text.strip(), elapsed
        
    except Exception as e:
        log_error(f"PaddleOCR error: {e}")
        return None, 0


def extract_percentage_from_text(text):
    """Extract percentage from OCR text using regex"""
    if not text:
        return None
    
    percentage_patterns = [
        r"(\d{1,3})\s*%",  # "29%", "29 %"
        r"%\s*(\d{1,3})",  # "% 29"
        r"(\d{1,3})",      # Just the number
    ]
    
    for pattern in percentage_patterns:
        match = re.search(pattern, text)
        if match:
            rate = int(match.group(1))
            if 0 <= rate <= 100:
                return rate
    return None


def test_ocr_comparison(screenshot_path="unity_test/ocr_test.png"):
    """Compare PaddleOCR vs Tesseract on SPD failure region"""
    
    log_info("=" * 70)
    log_info("OCR Engine Comparison: PaddleOCR vs Tesseract")
    log_info("=" * 70)
    log_info("\nTesting on SPD failure rate region with direct OCR (no preprocessing)")
    log_info(f"Using saved screenshot: {screenshot_path}\n")
    
    if not TESSERACT_AVAILABLE:
        log_error("Tesseract is not available. Cannot run comparison.")
        return None
    
    if not PADDLEOCR_AVAILABLE:
        log_warning("PaddleOCR is not available. Will only test Tesseract.")
        log_warning("Install with: pip install paddleocr")
    
    total_start = time.perf_counter()
    step_times = {}
    
    # Step 1: Load screenshot from file
    log_info("[Step 1] Loading screenshot from file...")
    step_start = time.perf_counter()
    if not os.path.exists(screenshot_path):
        log_error(f"Screenshot file not found: {screenshot_path}")
        log_error("Please provide a screenshot file or capture one first.")
        return None
    
    screenshot = Image.open(screenshot_path)
    load_time = (time.perf_counter() - step_start) * 1000
    step_times["load_screenshot"] = load_time
    log_info(f"  ✓ Screenshot loaded ({load_time:.2f}ms)")
    log_info(f"  Image size: {screenshot.size}")
    
    # Step 2: Crop failure region
    log_info("\n[Step 2] Cropping SPD failure region...")
    crop_start = time.perf_counter()
    left, top, right, bottom = FAILURE_REGION_SPD
    failure_region = screenshot.crop((left, top, right, bottom))
    crop_time = (time.perf_counter() - crop_start) * 1000
    step_times["crop"] = crop_time
    log_info(f"  ✓ Crop completed ({crop_time:.2f}ms)")
    log_info(f"  Region: {FAILURE_REGION_SPD}")
    log_info(f"  Cropped size: {failure_region.size}")
    
    # Save the region for inspection
    region_path = "unity_test/spd_failure_region_cropped.png"
    os.makedirs(os.path.dirname(region_path), exist_ok=True)
    failure_region.save(region_path)
    log_info(f"  ✓ Saved cropped region to: {region_path}")
    
    # Step 5: Test Tesseract OCR
    log_info("\n[Step 5] Testing Tesseract OCR (direct, no preprocessing)...")
    tesseract_results = []
    tesseract_times = []
    
    for i in range(5):
        text, elapsed = ocr_tesseract_direct(failure_region)
        tesseract_times.append(elapsed)
        percentage = extract_percentage_from_text(text)
        tesseract_results.append({
            "text": text,
            "percentage": percentage,
            "time": elapsed
        })
        log_info(f"  Run {i+1}: {elapsed:.2f}ms - Text: '{text}' - Percentage: {percentage}%")
        time.sleep(0.05)  # Small delay between runs
    
    avg_tesseract = sum(tesseract_times) / len(tesseract_times) if tesseract_times else 0
    
    # Step 6: Test PaddleOCR
    if PADDLEOCR_AVAILABLE:
        log_info("\n[Step 6] Testing PaddleOCR (direct, no preprocessing)...")
        paddleocr_results = []
        paddleocr_times = []
        
        for i in range(5):
            text, elapsed = ocr_paddleocr_direct(failure_region)
            paddleocr_times.append(elapsed)
            percentage = extract_percentage_from_text(text)
            paddleocr_results.append({
                "text": text,
                "percentage": percentage,
                "time": elapsed
            })
            log_info(f"  Run {i+1}: {elapsed:.2f}ms - Text: '{text}' - Percentage: {percentage}%")
            time.sleep(0.05)  # Small delay between runs
        
        avg_paddleocr = sum(paddleocr_times) / len(paddleocr_times) if paddleocr_times else 0
    else:
        paddleocr_results = []
        paddleocr_times = []
        avg_paddleocr = 0
    
    # Summary
    total_time = (time.perf_counter() - total_start) * 1000
    
    log_info("\n" + "=" * 70)
    log_info("COMPARISON SUMMARY")
    log_info("=" * 70)
    
    log_info(f"\nTesseract OCR:")
    if tesseract_times:
        log_info(f"  Average time: {avg_tesseract:.2f}ms")
        log_info(f"  Min time:     {min(tesseract_times):.2f}ms")
        log_info(f"  Max time:     {max(tesseract_times):.2f}ms")
        log_info(f"  Results:")
        for i, result in enumerate(tesseract_results, 1):
            log_info(f"    Run {i}: {result['percentage']}% (text: '{result['text']}')")
    
    if PADDLEOCR_AVAILABLE and paddleocr_times:
        log_info(f"\nPaddleOCR:")
        log_info(f"  Average time: {avg_paddleocr:.2f}ms")
        log_info(f"  Min time:     {min(paddleocr_times):.2f}ms")
        log_info(f"  Max time:     {max(paddleocr_times):.2f}ms")
        log_info(f"  Results:")
        for i, result in enumerate(paddleocr_results, 1):
            log_info(f"    Run {i}: {result['percentage']}% (text: '{result['text']}')")
    
    if avg_tesseract > 0 and avg_paddleocr > 0:
        speedup = avg_tesseract / avg_paddleocr
        if speedup > 1:
            log_info(f"\n⚡ PaddleOCR is {speedup:.2f}x FASTER than Tesseract")
        else:
            log_info(f"\n⚡ Tesseract is {1/speedup:.2f}x FASTER than PaddleOCR")
        
        time_diff = avg_tesseract - avg_paddleocr
        log_info(f"  Time difference: {abs(time_diff):.2f}ms ({'faster' if time_diff > 0 else 'slower'})")
    
    log_info(f"\nTotal test time: {total_time:.2f}ms")
    log_info(f"  - Setup (load screenshot, crop): {sum(step_times.values()):.2f}ms")
    log_info(f"  - OCR testing: {sum(tesseract_times) + sum(paddleocr_times):.2f}ms")
    
    log_info(f"\n💡 Notes:")
    log_info(f"  - Both engines use direct OCR (no preprocessing)")
    log_info(f"  - Tested on SPD failure region: {FAILURE_REGION_SPD}")
    log_info(f"  - Source screenshot: {screenshot_path}")
    log_info(f"  - Cropped region saved to: {region_path}")
    if not PADDLEOCR_AVAILABLE:
        log_info(f"  - Install PaddleOCR to compare: pip install paddleocr")
    
    log_info("=" * 70)
    
    return {
        "tesseract": {
            "times": tesseract_times,
            "avg": avg_tesseract,
            "results": tesseract_results
        },
        "paddleocr": {
            "times": paddleocr_times,
            "avg": avg_paddleocr,
            "results": paddleocr_results
        } if PADDLEOCR_AVAILABLE else None
    }


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Compare PaddleOCR vs Tesseract OCR")
    parser.add_argument(
        "--screenshot",
        "-s",
        type=str,
        default="unity_test/ocr_test.png",
        help="Path to screenshot file (default: unity_test/ocr_test.png)",
    )
    
    args = parser.parse_args()
    
    try:
        log_info("This test will compare PaddleOCR vs Tesseract OCR speed.")
        log_info(f"Using screenshot: {args.screenshot}\n")
        
        if not os.path.exists(args.screenshot):
            log_error(f"Screenshot file not found: {args.screenshot}")
            log_info("\nTo capture a new screenshot:")
            log_info("  1. Go to training screen")
            log_info("  2. Hover over SPD training")
            log_info("  3. Take screenshot and save to: unity_test/ocr_test.png")
            return 1
        
        results = test_ocr_comparison(args.screenshot)
        
        if results:
            log_info("\n✓ Comparison test completed")
        else:
            log_warning("\n⚠️  Test completed with issues")
        
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

