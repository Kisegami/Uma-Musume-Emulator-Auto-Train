import cv2
import numpy as np
from PIL import Image
import os
from utils.screenshot import take_screenshot
from utils.log import log_debug, log_info, log_warning, log_error

def _get_project_root():
    """Get the project root directory"""
    # Try to find project root by looking for main.py or assets/ folder
    # Start from this file's location (utils/recognizer.py)
    current = os.path.dirname(os.path.abspath(__file__))
    # Go up one level from utils/ to get project root
    project_root = os.path.dirname(current)
    
    # Verify it's the project root by checking for main.py or assets/
    if os.path.exists(os.path.join(project_root, 'main.py')) or os.path.exists(os.path.join(project_root, 'assets')):
        return project_root
    
    # Fallback: try current working directory
    cwd = os.getcwd()
    if os.path.exists(os.path.join(cwd, 'main.py')) or os.path.exists(os.path.join(cwd, 'assets')):
        return cwd
    
    # Last resort: return the calculated root anyway
    return project_root

def _resolve_asset_path(template_path):
    """Resolve asset path relative to project root"""
    # If path is already absolute, use it as-is
    if os.path.isabs(template_path):
        return template_path
    
    # If path exists as-is (relative to current working directory), use it
    if os.path.exists(template_path):
        return os.path.abspath(template_path)
    
    # Otherwise, resolve relative to project root
    project_root = _get_project_root()
    resolved_path = os.path.join(project_root, template_path)
    
    # Normalize the path (handle .. and .)
    resolved_path = os.path.normpath(resolved_path)
    
    return resolved_path

def match_template(screenshot, template_path, confidence=0.8, region=None):
    """
    Match template image on screenshot using OpenCV
    
    Args:
        screenshot: PIL Image of the screen
        template_path: Path to template image
        confidence: Minimum confidence threshold
        region: Region to search in (x, y, width, height)
    
    Returns:
        List of (x, y, width, height) matches or None if not found
    """
    try:
        # Resolve template path relative to project root
        resolved_path = _resolve_asset_path(template_path)
        
        # Load template
        if not os.path.exists(resolved_path):
            log_error(f"Template not found: {template_path} (resolved to: {resolved_path})")
            return []
        
        template_path = resolved_path  # Use resolved path for cv2.imread
        
        template = cv2.imread(template_path, cv2.IMREAD_COLOR)
        if template is None:
            log_error(f"Failed to load template: {template_path}")
            return []
        
        # Convert screenshot to OpenCV format
        screenshot_cv = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
        
        # Crop to region if specified
        if region:
            x, y, w, h = region
            screenshot_cv = screenshot_cv[y:y+h, x:x+w]
        
        # Get template dimensions
        h, w = template.shape[:2]
        
        # Perform template matching
        result = cv2.matchTemplate(screenshot_cv, template, cv2.TM_CCOEFF_NORMED)
        
        # Find locations where the matching exceeds the threshold
        locations = np.where(result >= confidence)
        matches = []
        
        for pt in zip(*locations[::-1]):  # Switch columns and rows
            if region:
                # Adjust coordinates back to full screen
                pt = (pt[0] + region[0], pt[1] + region[1])
            
            matches.append((pt[0], pt[1], w, h))
        
        return matches if matches else []
        
    except Exception as e:
        log_error(f"Error in template matching: {e}")
        return []

def max_match_confidence(screenshot, template_path, region=None):
    """
    Compute the maximum template match score for a template against a screenshot.

    Args:
        screenshot: PIL Image of the screen
        template_path: Path to template image
        region: Optional region to search (x, y, w, h)

    Returns:
        float: max normalized correlation score in [0,1], or None on error
    """
    try:
        # Resolve template path relative to project root
        resolved_path = _resolve_asset_path(template_path)
        
        if not os.path.exists(resolved_path):
            log_error(f"Template not found: {template_path} (resolved to: {resolved_path})")
            return 0.0

        template = cv2.imread(resolved_path, cv2.IMREAD_COLOR)
        if template is None:
            log_error(f"Failed to load template: {template_path}")
            return 0.0

        screenshot_cv = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)

        if region:
            x, y, w, h = region
            screenshot_cv = screenshot_cv[y:y+h, x:x+w]

        result = cv2.matchTemplate(screenshot_cv, template, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
        return float(max_val)
    except Exception as e:
        log_error(f"Error computing max template confidence: {e}")
        return 0.0

def locate_on_screen(template_path, confidence=0.8, region=None):
    """
    Locate template on screen and return center coordinates
    
    Args:
        template_path: Path to template image
        confidence: Minimum confidence threshold
        region: Region to search in (x, y, width, height)
    
    Returns:
        (x, y) center coordinates or None if not found
    """
    screenshot = take_screenshot()
    matches = match_template(screenshot, template_path, confidence, region)
    
    if matches:
        # Return center of first match
        x, y, w, h = matches[0]
        return (x + w//2, y + h//2)
    
    return None

def locate_all_on_screen(template_path, confidence=0.8, region=None):
    """
    Locate all instances of template on screen
    
    Args:
        template_path: Path to template image
        confidence: Minimum confidence threshold
        region: Region to search in (x, y, width, height)
    
    Returns:
        List of (x, y, width, height) matches or empty list if not found
    """
    screenshot = take_screenshot()
    matches = match_template(screenshot, template_path, confidence, region)
    
    return matches if matches else []

def is_image_on_screen(template_path, confidence=0.8, region=None):
    """
    Check if template image is present on screen
    
    Args:
        template_path: Path to template image
        confidence: Minimum confidence threshold
        region: Region to search in (x, y, width, height)
    
    Returns:
        True if found, False otherwise
    """
    return locate_on_screen(template_path, confidence, region) is not None

 