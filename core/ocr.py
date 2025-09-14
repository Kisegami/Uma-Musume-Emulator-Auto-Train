import cv2
import numpy as np
import pytesseract
import os
import sys
from PIL import Image, ImageOps, ImageEnhance
import json
import time

# Fix Windows console encoding for Unicode support
if os.name == 'nt':  # Windows
    try:
        # Set console to UTF-8 mode
        os.system('chcp 65001 > nul')
        # Also try to set stdout encoding
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass

# Configure Tesseract to use the custom trained data
tessdata_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'tessdata')
os.environ['TESSDATA_PREFIX'] = tessdata_dir

# Load config and check debug mode
with open("config.json", "r", encoding="utf-8") as config_file:
    config = json.load(config_file)
    DEBUG_MODE = config.get("debug_mode", False)

from utils.log import log_debug, log_info, log_warning, log_error

# Try to find tesseract executable automatically
try:
    # On Windows, try common installation paths
    if os.name == 'nt':
        possible_paths = [
            r'C:\Program Files\Tesseract-OCR\tesseract.exe',
            r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
            r'C:\Users\{}\AppData\Local\Programs\Tesseract-OCR\tesseract.exe'.format(os.getenv('USERNAME', ''))
        ]
        for path in possible_paths:
            if os.path.exists(path):
                pytesseract.pytesseract.tesseract_cmd = path
                break
except Exception:
    pass  # Fall back to system PATH

def verify_tesseract_config():
    """Verify which Tesseract configuration is being used"""
    try:
        # Get current tesseract command
        tesseract_cmd = getattr(pytesseract.pytesseract, 'tesseract_cmd', 'system PATH')
        log_info(f"🔍 Tesseract executable: {tesseract_cmd}")
        
        # Get current TESSDATA_PREFIX
        tessdata_prefix = os.environ.get('TESSDATA_PREFIX', 'Not set')
        log_info(f"🔍 TESSDATA_PREFIX: {tessdata_prefix}")
        
        # Check if custom tessdata is accessible
        if os.path.exists(tessdata_dir):
            custom_models = [f for f in os.listdir(tessdata_dir) if f.endswith('.traineddata')]
            log_info(f"🔍 Custom tessdata models: {custom_models}")
            
            # Try to get tesseract info to see which models it can see
            try:
                version = pytesseract.get_tesseract_version()
                languages = pytesseract.get_languages()
                log_info(f"🔍 Tesseract version: {version}")
                log_info(f"🔍 Available languages: {languages}")
            except Exception as e:
                log_info(f"🔍 Could not get Tesseract info: {e}")
        else:
            log_info(f"🔍 Custom tessdata directory not found: {tessdata_dir}")
            
    except Exception as e:
        log_info(f"🔍 Error verifying Tesseract config: {e}")

# Verify configuration on import
if DEBUG_MODE:
    verify_tesseract_config()

# Verify tessdata directory exists and contains models
if not os.path.exists(tessdata_dir):
    log_info(f"⚠️  Warning: tessdata directory not found: {tessdata_dir}")
    log_info(f"   Falling back to system Tesseract models")
else:
    # Check what models are available in custom tessdata
    available_models = []
    for file in os.listdir(tessdata_dir):
        if file.endswith('.traineddata'):
            available_models.append(file)
    
    if available_models:
        log_info(f"✅ Using custom Tesseract models from: {tessdata_dir}")
        log_info(f"   Available models: {', '.join(available_models)}")
    else:
        log_info(f"⚠️  tessdata directory exists but contains no .traineddata files: {tessdata_dir}")
        log_info(f"   Falling back to system Tesseract models")

def extract_text(pil_img: Image.Image) -> str:
    """Extract text from image using Tesseract OCR"""
    try:
        # Convert PIL image to numpy array if needed
        if isinstance(pil_img, Image.Image):
            img_np = np.array(pil_img)
        else:
            img_np = pil_img
            
        # Debug info about which tessdata is being used
        if DEBUG_MODE and os.path.exists(tessdata_dir):
            log_debug(f"Using custom tessdata from: {tessdata_dir}")
            
        # Use Tesseract with custom configuration for better accuracy
        # config = '--oem 3 --psm 6 -c tessedit_char_whitelist="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789%().- "'
        text = pytesseract.image_to_string(img_np, lang='eng')
        result = text.strip()
        
        # If no text extracted and in debug mode, save debug image
        if not result and DEBUG_MODE:
            debug_filename = f"debug_ocr_text_failed_{int(time.time())}.png"
            pil_img.save(debug_filename)
            log_debug(f"OCR text extraction failed, saved debug image: {debug_filename}")
            log_debug(f"Image size: {pil_img.size}")
        
        return result
    except Exception as e:
        if DEBUG_MODE:
            debug_filename = f"debug_ocr_text_error_{int(time.time())}.png"
            pil_img.save(debug_filename)
            log_debug(f"OCR text extraction error: {e}, saved debug image: {debug_filename}")
        log_warning(f"OCR extraction failed: {e}")
        return ""

def extract_number(pil_img: Image.Image) -> str:
    """Extract numbers from image using Tesseract OCR"""
    try:
        # Convert PIL image to numpy array if needed
        if isinstance(pil_img, Image.Image):
            img_np = np.array(pil_img)
        else:
            img_np = pil_img
            
        # Use Tesseract with configuration optimized for numbers
        config = '--oem 3 --psm 7 -c tessedit_char_whitelist=0123456789 '
        text = pytesseract.image_to_string(img_np, config=config, lang='eng')
        result = text.strip()
        
        # If no number extracted and in debug mode, save debug image
        if not result and DEBUG_MODE:
            debug_filename = f"debug_ocr_number_failed_{int(time.time())}.png"
            pil_img.save(debug_filename)
            log_debug(f"OCR number extraction failed, saved debug image: {debug_filename}")
            log_debug(f"Image size: {pil_img.size}")
        
        return result
    except Exception as e:
        if DEBUG_MODE:
            debug_filename = f"debug_ocr_number_error_{int(time.time())}.png"
            pil_img.save(debug_filename)
            log_debug(f"OCR number extraction error: {e}, saved debug image: {debug_filename}")
        log_warning(f"Number extraction failed: {e}")
        return ""

def extract_turn_number(pil_img: Image.Image) -> str:
    """Extract turn numbers with specialized configuration for better digit recognition"""
    try:
        # Convert PIL image to numpy array if needed
        if isinstance(pil_img, Image.Image):
            img_np = np.array(pil_img)
        else:
            img_np = pil_img
            
        # Try multiple PSM modes for better digit recognition
        configs = [
            '--oem 3 --psm 8 -c tessedit_char_whitelist=0123456789',  # Single word
            '--oem 3 --psm 7 -c tessedit_char_whitelist=0123456789',  # Single line
            '--oem 3 --psm 6 -c tessedit_char_whitelist=0123456789',  # Uniform block
        ]
        
        for config in configs:
            text = pytesseract.image_to_string(img_np, config=config, lang='eng')
            text = text.strip()
            if text and text.isdigit():
                return text
        
        # If no config worked, return the first non-empty result
        for config in configs:
            text = pytesseract.image_to_string(img_np, config=config, lang='eng')
            text = text.strip()
            if text:
                return text
                
        return ""
    except Exception as e:
        log_warning(f"Turn number extraction failed: {e}")
        return ""

def extract_failure_text(pil_img: Image.Image) -> str:
    """Extract failure rate text with specialized configuration"""
    try:
        # Convert PIL image to numpy array if needed
        if isinstance(pil_img, Image.Image):
            img_np = np.array(pil_img)
        else:
            img_np = pil_img
            
        # # Try multiple PSM modes for better text recognition
        # configs = [
        #     '--oem 3 --psm 6 -c tessedit_char_whitelist="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789%(). "',  # Uniform block
        #     '--oem 3 --psm 7 -c tessedit_char_whitelist="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789%(). "',  # Single line
        #     '--oem 3 --psm 8 -c tessedit_char_whitelist="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789%(). "',  # Single word
        #     '--oem 3 --psm 13 -c tessedit_char_whitelist="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789%(). "',  # Raw line
        # ]
        
        for config in configs:
            text = pytesseract.image_to_string(img_np, lang='eng')
            text = text.strip()
            if text:
                return text
                
        return ""
    except Exception as e:
        log_warning(f"Failure text extraction failed: {e}")
        return ""

def extract_failure_text_with_confidence(pil_img: Image.Image) -> tuple[str, float]:
    """Extract failure rate text with confidence score from Tesseract"""
    try:
        # Convert PIL image to numpy array if needed
        if isinstance(pil_img, Image.Image):
            img_np = np.array(pil_img)
        else:
            img_np = pil_img
            
        # # Use Tesseract with data output to get confidence scores
        # config = '--oem 3 --psm 6 -c tessedit_char_whitelist="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789%(). "'
        ocr_data = pytesseract.image_to_data(img_np, lang='eng', output_type=pytesseract.Output.DICT)
        
        # Extract text and calculate average confidence
        text_parts = []
        confidences = []
        
        for i, text in enumerate(ocr_data['text']):
            if text.strip():  # Only consider non-empty text
                text_parts.append(text)
                confidences.append(ocr_data['conf'][i])
        
        if text_parts:
            full_text = ' '.join(text_parts).strip()
            avg_confidence = sum(confidences) / len(confidences) / 100.0  # Convert to 0-1 scale
            return full_text, avg_confidence
        else:
            return "", 0.0
            
    except Exception as e:
        log_warning(f"Failure text extraction with confidence failed: {e}")
        return "", 0.0

def extract_event_name_text(pil_img: Image.Image) -> str:
    """Extract event name text using improved white specialization and OCR with confidence filtering"""
    try:
        # Normalize input to numpy array
        if isinstance(pil_img, Image.Image):
            img_np = np.array(pil_img)
        else:
            img_np = pil_img

        # Convert to grayscale
        if len(img_np.shape) == 3:
            gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
        else:
            gray = img_np

        # White specialization - find bright pixels (white text)
        _, cleaned = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY)

        # Clean up text with morphological operations
        kernel = np.ones((1,1), np.uint8)
        cleaned = cv2.morphologyEx(cleaned, cv2.MORPH_CLOSE, kernel)

        # OCR with confidence filtering
        data = pytesseract.image_to_data(cleaned, config="-c preserve_interword_spaces=1", lang='eng', output_type=pytesseract.Output.DICT)
        
        high_confidence_words = []
        for i in range(len(data['text'])):
            word = data['text'][i].strip()
            conf = int(data['conf'][i])
            if word and conf >= 80:
                high_confidence_words.append(word)
        
        result_text = ' '.join(high_confidence_words).strip()
        
        # Apply database matching (handles all post-processing internally)
        if result_text:
            result_text = find_best_event_match(result_text)
            log_debug(f"Event name OCR result: '{result_text}'")
            return result_text
        
        return ""
    except Exception as e:
        log_warning(f"Event name OCR extraction failed: {e}")
        return ""

def find_best_event_match(ocr_text):
    """Find best matching event from database using simple and efficient method"""
    try:
        import json
        import os
        from difflib import SequenceMatcher
        
        # Load event databases
        all_event_names = []
        
        # Load support card events
        if os.path.exists("assets/events/support_card.json"):
            with open("assets/events/support_card.json", "r", encoding="utf-8-sig") as f:
                support_events = json.load(f)
                for event in support_events:
                    event_name = event.get("EventName", "")
                    if event_name and event_name not in all_event_names:
                        all_event_names.append(event_name)
        
        # Load uma data events
        if os.path.exists("assets/events/uma_data.json"):
            with open("assets/events/uma_data.json", "r", encoding="utf-8-sig") as f:
                uma_data = json.load(f)
                for character in uma_data:
                    if "UmaEvents" in character:
                        for event in character["UmaEvents"]:
                            event_name = event.get("EventName", "")
                            if event_name and event_name not in all_event_names:
                                all_event_names.append(event_name)
        
        # Load ura finale events
        if os.path.exists("assets/events/ura_finale.json"):
            with open("assets/events/ura_finale.json", "r", encoding="utf-8-sig") as f:
                ura_events = json.load(f)
                for event in ura_events:
                    event_name = event.get("EventName", "")
                    if event_name and event_name not in all_event_names:
                        all_event_names.append(event_name)
        
        if not ocr_text or not all_event_names:
            return ocr_text
        
        def normalize(s):
            return s.replace("(❯)", "").replace("(❯❯)", "").replace("(❯❯❯)", "").strip()
        
        clean_ocr = normalize(ocr_text.strip())
        if not clean_ocr:
            return ocr_text
        
        best_match = ocr_text
        best_ratio = 0.0
        
        for db_event in all_event_names:
            db_norm = normalize(db_event)
            
            # Exact match
            if db_norm.lower() == clean_ocr.lower():
                return db_event
            
            # OCR contained in DB name
            if clean_ocr.lower() in db_norm.lower():
                if not best_match or len(db_norm) < len(best_match):
                    best_match = db_event
                    best_ratio = 0.92
            
            # Similarity match
            else:
                ratio = SequenceMatcher(None, clean_ocr.lower(), db_norm.lower()).ratio()
                if ratio > best_ratio and ratio >= 0.6:
                    best_ratio = ratio
                    best_match = db_event
        
        return best_match
    except Exception as e:
        log_warning(f"Event name matching failed: {e}")
        return ocr_text