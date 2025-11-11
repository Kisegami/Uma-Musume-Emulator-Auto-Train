import pytesseract
from PIL import Image, ImageOps, ImageEnhance
import numpy as np
import cv2
import os
import json

# Configure Tesseract to use the custom trained data
tessdata_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'tessdata')
os.environ['TESSDATA_PREFIX'] = tessdata_dir

# Load config and check debug mode
with open("config.json", "r", encoding="utf-8") as config_file:
    config = json.load(config_file)
    DEBUG_MODE = config.get("debug_mode", False)

def debug_print(message):
    """Print debug message only if DEBUG_MODE is enabled"""
    if DEBUG_MODE:
        print(message)

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

def extract_text(pil_img: Image.Image) -> str:
    """Extract text from image using Tesseract OCR"""
    try:
        # Convert PIL image to numpy array if needed
        if isinstance(pil_img, Image.Image):
            img_np = np.array(pil_img)
        else:
            img_np = pil_img
            
        # Use Tesseract with custom configuration for better accuracy
        config = '--oem 3 --psm 6 -c tessedit_char_whitelist="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789%().- "'
        text = pytesseract.image_to_string(img_np, config=config, lang='eng')
        return text.strip()
    except Exception as e:
        print(f"[WARNING] OCR extraction failed: {e}")
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
        return text.strip()
    except Exception as e:
        print(f"[WARNING] Number extraction failed: {e}")
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
        print(f"[WARNING] Turn number extraction failed: {e}")
        return ""

def extract_mood_text(pil_img: Image.Image) -> str:
    """Extract mood text with specialized configuration for better text recognition"""
    try:
        # Convert PIL image to numpy array if needed
        if isinstance(pil_img, Image.Image):
            img_np = np.array(pil_img)
        else:
            img_np = pil_img
            
        # Try multiple PSM modes for better text recognition
        configs = [
            '--oem 3 --psm 8 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz',  # Single word
            '--oem 3 --psm 7 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz',  # Single line
            '--oem 3 --psm 6 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz',  # Uniform block
        ]
        
        for config in configs:
            text = pytesseract.image_to_string(img_np, config=config, lang='eng')
            text = text.strip()
            if text:
                return text
                
        return ""
    except Exception as e:
        print(f"[WARNING] Mood text extraction failed: {e}")
        return ""

def extract_failure_text(pil_img: Image.Image) -> str:
    """Extract failure rate text with specialized configuration"""
    try:
        # Convert PIL image to numpy array if needed
        if isinstance(pil_img, Image.Image):
            img_np = np.array(pil_img)
        else:
            img_np = pil_img
            
        # Try multiple PSM modes for better text recognition
        configs = [
            '--oem 3 --psm 6 -c tessedit_char_whitelist="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789%(). "',  # Uniform block
            '--oem 3 --psm 7 -c tessedit_char_whitelist="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789%(). "',  # Single line
            '--oem 3 --psm 8 -c tessedit_char_whitelist="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789%(). "',  # Single word
            '--oem 3 --psm 13 -c tessedit_char_whitelist="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789%(). "',  # Raw line
        ]
        
        for config in configs:
            text = pytesseract.image_to_string(img_np, config=config, lang='eng')
            text = text.strip()
            if text:
                return text
                
        return ""
    except Exception as e:
        print(f"[WARNING] Failure text extraction failed: {e}")
        return ""

def extract_failure_text_with_confidence(pil_img: Image.Image) -> tuple[str, float]:
    """Extract failure rate text with confidence score from Tesseract"""
    try:
        # Convert PIL image to numpy array if needed
        if isinstance(pil_img, Image.Image):
            img_np = np.array(pil_img)
        else:
            img_np = pil_img
            
        # Use Tesseract with data output to get confidence scores
        config = '--oem 3 --psm 6 -c tessedit_char_whitelist="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789%(). "'
        ocr_data = pytesseract.image_to_data(img_np, config=config, lang='eng', output_type=pytesseract.Output.DICT)
        
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
        print(f"[WARNING] Failure text extraction with confidence failed: {e}")
        return "", 0.0

def extract_event_name_text(pil_img: Image.Image) -> str:
    """Extract event name text using a simple OCR path first, then a robust fallback.
    Steps: 2x upscale -> grayscale -> autocontrast/contrast/sharpness -> OCR with whitelist preserving spaces.
    """
    try:
        # Normalize input to numpy array
        if isinstance(pil_img, Image.Image):
            img_np = np.array(pil_img)
        else:
            img_np = pil_img

        # 2x upscale
        height, width = img_np.shape[:2]
        new_width = int(width * 2.0)
        new_height = int(height * 2.0)
        scaled_img = cv2.resize(img_np, (new_width, new_height), interpolation=cv2.INTER_CUBIC)

        # Grayscale
        if len(scaled_img.shape) == 3:
            gray = cv2.cvtColor(scaled_img, cv2.COLOR_BGR2GRAY)
        else:
            gray = scaled_img

        # White specialization and sharpness using PIL
        try:
            pil_gray = Image.fromarray(gray).convert("L")
            pil_enh = ImageOps.autocontrast(pil_gray, cutoff=1)
            pil_enh = ImageEnhance.Contrast(pil_enh).enhance(1.8)
            pil_enh = ImageEnhance.Sharpness(pil_enh).enhance(1.8)
            enhanced_gray = np.array(pil_enh)
            debug_print("[DEBUG] Applied autocontrast/contrast/sharpness to grayscale image")
        except Exception as enh_e:
            debug_print(f"[DEBUG] Enhancement pipeline failed: {enh_e}")
            enhanced_gray = gray

        # Simple OCR path (no PSM), preserve spaces
        try:
            cfg_simple = "-c tessedit_char_whitelist=\"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz1234567890'!,♪☆():.-?!\" -c preserve_interword_spaces=1 -c user_defined_dpi=300"
            debug_print(f"[DEBUG] Simple OCR cfg: {cfg_simple}")
            simple_text = pytesseract.image_to_string(enhanced_gray, config=cfg_simple, lang='eng')
            simple_text = (simple_text or "").strip()
            debug_print(f"[DEBUG] Simple OCR raw: '{simple_text}'")
            # Optionally save enhanced image for debugging
            if DEBUG_MODE:
                from datetime import datetime
                ts = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
                try:
                    Image.fromarray(enhanced_gray).save(f"event_ocr_simple_{ts}.png")
                except Exception:
                    pass
            if simple_text:
                import re
                simple_text = re.sub(r'\b(Star|star)\b', '☆', simple_text)
                if 'Escape' in simple_text and not simple_text.endswith('!'):
                    simple_text += '!'
                # Keep spaces; just clean prefix before first uppercase
                m = re.search(r'[A-Z]', simple_text)
                if m:
                    simple_text = simple_text[m.start():]
                # CamelCase spacing if any
                simple_text = re.sub(r'([a-z])([A-Z])', r'\1 \2', simple_text)
                # Fuzzy match against DB
                simple_text = find_best_event_match(simple_text)
                return simple_text
        except Exception as simple_e:
            debug_print(f"[DEBUG] Simple OCR path failed: {simple_e}")

        # Fallback: binarize and run image_to_data with multiple PSMs
        _, binary = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY_INV)
        processed = cv2.bitwise_not(binary)
        img_np_proc = processed

        configs = [
            "--oem 3 --psm 8 -c tessedit_char_whitelist=\"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'!,♪☆():.-?!\" -c preserve_interword_spaces=1 -c user_defined_dpi=300",
            "--oem 3 --psm 7 -c tessedit_char_whitelist=\"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'!,♪☆():.-?!\" -c preserve_interword_spaces=1 -c user_defined_dpi=300",
            "--oem 3 --psm 6 -c tessedit_char_whitelist=\"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'!,♪☆():.-?!\" -c preserve_interword_spaces=1 -c user_defined_dpi=300",
        ]
        for config in configs:
            try:
                debug_print(f"[DEBUG] Tesseract config: {config}")
                data = pytesseract.image_to_data(img_np_proc, config=config, lang='eng', output_type=pytesseract.Output.DICT)
            except Exception as ocr_e:
                print(f"[WARNING] image_to_data failed for config: {config}. Error: {ocr_e}")
                continue

            # Collect words with confidence
            text_parts = []
            conf_parts = []
            for i, word in enumerate(data['text']):
                w = (word or '').strip()
                try:
                    conf_val = float(data['conf'][i])
                except Exception:
                    conf_val = -1
                if w and conf_val >= 60:
                    text_parts.append(w)
                    conf_parts.append(conf_val)

            raw_joined = ' '.join([(w or '').strip() for w in data['text'] if (w or '').strip()])
            debug_print(f"[DEBUG] Raw OCR (no filter): '{raw_joined}'")
            if conf_parts:
                avg_conf = sum(conf_parts) / len(conf_parts)
                debug_print(f"[DEBUG] Filtered words: {len(text_parts)}, avg conf: {avg_conf:.1f}")
            else:
                debug_print("[DEBUG] No words passed confidence filter")

            text = ' '.join(text_parts).strip()

            # Post-processing and fuzzy match
            import re
            text = re.sub(r'\b(Star|star)\b', '☆', text)
            text = re.sub(r'\b(star)\b', '☆', text)
            text = re.sub(r'\b(Star)\b', '☆', text)
            if 'Escape' in text and not text.endswith('!'):
                text += '!'
            text = find_best_event_match(text)
            match = re.search(r'[A-Z]', text)
            if match:
                text = text[match.start():]
            if text:
                text = re.sub(r'([a-z])([A-Z])', r'\1 \2', text)
            debug_print(f"[DEBUG] Post-processed OCR text: '{text}'")
            if text:
                return text
        return ""
    except Exception as e:
        print(f"[WARNING] Event name OCR extraction failed: {e}")
        return ""

def find_best_event_match(ocr_text):
    """Find the best matching event name from the database using robust heuristics.
    Preference order:
      1) Exact case-insensitive match
      2) Exact match ignoring spaces/punctuation
      3) Token containment (all OCR tokens present in DB name)
      4) Highest similarity ratio (>= 0.80), with prefix match allowed only when OCR length >= 4
    """
    try:
        import json
        import os
        import re
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

        # Helper normalizers
        def normalize(s: str) -> str:
            return s.replace("(❯)", "").replace("(❯❯)", "").replace("(❯❯❯)", "").strip()

        def strip_spaces_punct(s: str) -> str:
            return re.sub(r"[^A-Za-z0-9☆']+", "", s).lower()

        def tokens(s: str) -> set[str]:
            return set(re.findall(r"[A-Za-z0-9☆']+", s.lower()))

        # Clean OCR
        clean_ocr_text = (ocr_text or "").strip().rstrip("'\"`").strip()
        if not clean_ocr_text:
            return ocr_text

        ocr_norm = normalize(clean_ocr_text)
        ocr_nospace = strip_spaces_punct(ocr_norm)
        ocr_tokens = tokens(ocr_norm)

        # Pass 1: exact case-insensitive
        for name in all_event_names:
            if normalize(name).lower() == ocr_norm.lower():
                debug_print(f"[DEBUG] Exact match: '{ocr_text}' -> '{name}'")
                return name

        # Pass 2: exact ignoring spaces/punct
        for name in all_event_names:
            if strip_spaces_punct(normalize(name)) == ocr_nospace:
                debug_print(f"[DEBUG] No-space match: '{ocr_text}' -> '{name}'")
                return name

        # Pass 3: token containment
        token_candidates = []
        for name in all_event_names:
            name_norm = normalize(name)
            name_tokens = tokens(name_norm)
            if ocr_tokens and ocr_tokens.issubset(name_tokens):
                token_candidates.append(name)
        if token_candidates:
            # Prefer the shortest candidate (most specific) to avoid mapping to longer unrelated names
            best = min(token_candidates, key=lambda n: len(n))
            debug_print(f"[DEBUG] Token match: '{ocr_text}' -> '{best}'")
            return best

        # Pass 4: similarity ratio with threshold
        best_match = ocr_text
        best_ratio = 0.0
        for db_event_name in all_event_names:
            clean_db_name = normalize(db_event_name)
            ratio = SequenceMatcher(None, ocr_norm.lower(), clean_db_name.lower()).ratio()
            prefix_ok = len(ocr_norm) >= 4 and clean_db_name.lower().startswith(ocr_norm.lower())
            if ((ratio >= 0.80 and ratio > best_ratio) or prefix_ok):
                best_ratio = ratio
                best_match = db_event_name

        if best_match != ocr_text:
            debug_print(f"[DEBUG] OCR: '{ocr_text}' -> Matched: '{best_match}' (ratio: {best_ratio:.3f})")
        else:
            debug_print(f"[DEBUG] OCR: '{ocr_text}' -> No match found (best ratio: {best_ratio:.3f})")
        return best_match
    except Exception as e:
        print(f"[WARNING] Event name matching failed: {e}")
        return ocr_text

def extract_event_name_text_debug(pil_img: Image.Image, save_prefix: str = "event_debug") -> dict:
    """
    Extract event name text from image using Tesseract OCR with PSM 6, 7, 8.
    Uses the exact same approach as event_ocr.py for consistency.
    """
    import cv2
    import numpy as np
    import pytesseract
    from PIL import ImageDraw

    if isinstance(pil_img, Image.Image):
        img_np = np.array(pil_img)
    else:
        img_np = pil_img
    if img_np.shape[-1] == 4:
        img_np = cv2.cvtColor(img_np, cv2.COLOR_RGBA2RGB)

    # Use the exact same config as event_ocr.py
    config = '-c tessedit_char_whitelist="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz1234567890 \'!,♪☆():.-?!" -c tessedit_pageseg_mode=7 -c user_defined_dpi=300'
    
    # Use image_to_data to get confidence scores (like event_ocr.py)
    data = pytesseract.image_to_data(img_np, config=config, lang='eng', output_type=pytesseract.Output.DICT)
    
    # Extract text and bounding boxes with confidence filtering (>= 90% like event_ocr.py)
    text_results = []
    full_text = ""
    
    for i in range(len(data['text'])):
        text = data['text'][i].strip()
        conf = data['conf'][i]
        
        if text and conf >= 60:  # Lower threshold to catch more text including special characters
            x = data['left'][i]
            y = data['top'][i]
            w = data['width'][i]
            h = data['height'][i]
            
            text_results.append({
                'text': text,
                'confidence': conf,
                'bbox': (x, y, w, h)
            })
            
            full_text += text + " "
    
    full_text = full_text.strip()
    
    # Post-processing: Handle common OCR mistakes with special characters
    import re
    # Replace common OCR mistakes for special characters
    full_text = re.sub(r'\b(Star|star)\b', '☆', full_text)  # OCR might read ☆ as "Star"
    full_text = re.sub(r'\b(star)\b', '☆', full_text)  # Lowercase "star"
    full_text = re.sub(r'\b(Star)\b', '☆', full_text)  # Capital "Star"
    
    # Add missing exclamation marks if the event name suggests it
    if 'Escape' in full_text and not full_text.endswith('!'):
        full_text += '!'
    
    # General post-processing: Try to find the best matching event name from database
    full_text = find_best_event_match(full_text)
    
    # Post-processing: Remove everything before first uppercase letter
    match = re.search(r'[A-Z]', full_text)
    if match:
        full_text = full_text[match.start():]
    
    # Post-processing: Insert spaces before uppercase letters that follow lowercase letters
    if full_text:
        full_text = re.sub(r'([a-z])([A-Z])', r'\1 \2', full_text)
    
    # Calculate average confidence
    if text_results:
        avg_conf = sum(result['confidence'] for result in text_results) / len(text_results) / 100.0
    else:
        avg_conf = 0.0
    
    # Draw bounding boxes
    annotated = pil_img.copy() if isinstance(pil_img, Image.Image) else Image.fromarray(img_np)
    draw = ImageDraw.Draw(annotated)
    for result in text_results:
        x, y, w, h = result['bbox']
        draw.rectangle([x, y, x + w, y + h], outline='red', width=2)
    
    img_path = f"{save_prefix}_result.png"
    annotated.save(img_path)
    
    # Return in the same format as before for compatibility
    results = {
        7: {  # Use PSM 7 as the main result
            'text': full_text,
            'confidence': avg_conf,
            'image_path': img_path,
        }
    }
    
    return results
