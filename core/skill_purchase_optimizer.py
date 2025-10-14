import json
import os
import sys
from difflib import SequenceMatcher
from core.skill_recognizer import scan_all_skills_with_scroll
from utils.log import log_debug, log_info, log_warning, log_error

# Global cache for skill names
_all_skill_names = None

def load_all_skill_names():
    """Load all valid skill names from uma_skills.json"""
    global _all_skill_names
    if _all_skill_names is not None:
        return _all_skill_names
    
    try:
        skills_file_path = "assets/skills/uma_skills.json"
        if os.path.exists(skills_file_path):
            with open(skills_file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                _all_skill_names = data.get("skills", [])
                log_debug(f"Loaded {len(_all_skill_names)} skill names from {skills_file_path}")
                return _all_skill_names
        else:
            log_warning(f"Skill names file not found: {skills_file_path}")
            return []
    except Exception as e:
        log_error(f"Error loading skill names: {e}")
        return []

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

# debug_print is imported from utils.log

def load_skill_config(config_path=None):
    """
    Load skill configuration from JSON file.
    
    Args:
        config_path: Path to skills config file. If None, loads from config.json's skill_file setting.
    
    Returns:
        dict: Configuration with skill_priority and gold_skill_upgrades
    """
    # If no config_path provided, try to load from config.json
    if config_path is None:
        try:
            with open("config.json", 'r', encoding='utf-8') as f:
                main_config = json.load(f)
                config_path = main_config.get("skill_file", "skills.json")
                log_debug(f"Loading skills from config file: {config_path}")
        except Exception as e:
            log_debug(f"Could not read config.json, using default skills.json: {e}")
            config_path = "skills.json"
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
            log_debug(f"Successfully loaded skills config from: {config_path}")
            return config
    except FileNotFoundError:
        log_error(f"{config_path} not found. Creating default config")
        default_config = {
            "skill_priority": [],
            "gold_skill_upgrades": {}
        }
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(default_config, f, indent=4)
        return default_config
    except Exception as e:
        log_error(f"Error loading {config_path}: {e}")
        return {"skill_priority": [], "gold_skill_upgrades": {}}

def clean_ocr_text(text):
    """
    Clean OCR text by removing common artifacts and normalizing.
    
    Args:
        text: Raw OCR text
    
    Returns:
        str: Cleaned text
    """
    if not text:
        return ""
    
    # Remove extra whitespace and normalize
    text = ' '.join(text.split())
    
    # Common OCR corrections
    corrections = {
        '0': 'O',  # Zero to letter O
        '1': 'I',  # One to letter I (in some contexts)
        '5': 'S',  # Five to letter S (in some contexts)
        '8': 'B',  # Eight to letter B (in some contexts)
    }
    
    # Apply corrections carefully (only at word boundaries to avoid over-correction)
    # This is conservative - we may want to expand this based on actual OCR errors seen
    
    return text.strip()

def find_best_real_skill_match(ocr_skill_name, target_skill_name=None, threshold=0.85):
    """
    Find the best matching real skill name from the game's skill list.
    Uses the actual uma_skills.json to ensure we only match real skills.
    
    Args:
        ocr_skill_name: Skill name detected by OCR (potentially with errors)
        target_skill_name: Skill name from user config (optional, for validation)
        threshold: Minimum similarity ratio (0.0 to 1.0)
    
    Returns:
        dict: {
            'match': str or None,  # Best matching real skill name
            'confidence': float,   # Confidence score (0.0 to 1.0)
            'exact_match': bool,   # True if exact match found
            'is_target_match': bool  # True if matches the target skill
        }
    """
    all_skills = load_all_skill_names()
    if not all_skills:
        log_warning("No skill names loaded - falling back to basic matching")
        if target_skill_name:
            return {
                'match': target_skill_name,
                'confidence': 0.8,
                'exact_match': False,
                'is_target_match': True
            }
        return {
            'match': None,
            'confidence': 0.0,
            'exact_match': False,
            'is_target_match': False
        }
    
    # Clean the OCR input
    clean_ocr = clean_ocr_text(ocr_skill_name).lower().strip()
    
    if not clean_ocr:
        return {
            'match': None,
            'confidence': 0.0,
            'exact_match': False,
            'is_target_match': False
        }
    
    best_match = None
    best_confidence = 0.0
    exact_match = False
    is_target_match = False
    
    # Try exact match first
    for skill in all_skills:
        if clean_ocr == skill.lower().strip():
            exact_match = True
            best_match = skill
            best_confidence = 1.0
            is_target_match = (target_skill_name and skill.lower().strip() == target_skill_name.lower().strip())
            break
    
    # If no exact match, try fuzzy matching against all real skills
    if not exact_match:
        for skill in all_skills:
            skill_clean = skill.lower().strip()
            
            # Pre-filter: Skip skills that have significantly different word structure
            # Only if target is specified and we have high-confidence word differences
            if target_skill_name:
                target_clean = target_skill_name.lower().strip()
                target_words = set(target_clean.split())
                skill_words = set(skill_clean.split())
                ocr_words = set(clean_ocr.split())
                
                # Check if this is the target skill - if so, allow it through for fuzzy matching
                if skill_clean == target_clean:
                    pass  # Always allow target skill through
                # If word counts are very different, this is likely a different skill
                elif abs(len(skill_words) - len(target_words)) > 1:
                    # But allow if OCR text has similar word count (OCR might have split/joined words)
                    if abs(len(ocr_words) - len(skill_words)) > 1:
                        continue
                # Check for added qualifier words (like "Quick" in "Quick Acceleration")
                else:
                    extra_words_in_skill = skill_words - target_words
                    # Skip if there are significant extra qualifying words
                    qualifying_words = ['quick', 'fast', 'slow', 'super', 'ultra', 'mega', 'mini', 'great', 'grand', 'advanced', 'enhanced']
                    significant_extras = [w for w in extra_words_in_skill if w in qualifying_words]
                    if significant_extras:
                        continue
            
            # Calculate similarity
            similarity = SequenceMatcher(None, clean_ocr, skill_clean).ratio()
            
            # Bonus for target skill match (if we're looking for a specific target)
            # But only if the similarity is already quite high to prevent false matches
            if target_skill_name and skill_clean == target_skill_name.lower().strip() and similarity >= 0.9:
                similarity += 0.05  # Small bonus for target match, only for high-confidence matches
                similarity = min(similarity, 1.0)  # Cap at 1.0
            
            if similarity > best_confidence and similarity >= threshold:
                best_match = skill
                best_confidence = similarity
                is_target_match = (target_skill_name and skill_clean == target_skill_name.lower().strip())
    
    log_debug(f"Skill match: '{ocr_skill_name}' -> '{best_match}' (confidence: {best_confidence:.3f}, target: {target_skill_name})")
    
    return {
        'match': best_match,
        'confidence': best_confidence,
        'exact_match': exact_match,
        'is_target_match': is_target_match
    }

def fuzzy_match_skill_name(skill_name, target_name, threshold=0.8):
    """
    Check if two skill names match using the real skill database.
    This replaces the old fuzzy matching with precise matching against known skills.
    
    Args:
        skill_name: Name from OCR scan
        target_name: Name from config file
        threshold: Minimum similarity ratio (0.0 to 1.0)
    
    Returns:
        bool: True if the OCR skill matches the target skill
    """
    # Use the new precise matching system
    result = find_best_real_skill_match(skill_name, target_name, threshold)
    
    # Return True only if we found a match AND it matches the target AND meets threshold
    return (result['match'] is not None and 
            result['is_target_match'] and 
            result['confidence'] >= threshold)

def find_matching_skill(skill_name, available_skills):
    """
    Find a skill in available_skills that matches skill_name using precise real skill matching.
    
    Args:
        skill_name: Name to search for (from user config)
        available_skills: List of available skill dicts (from OCR)
    
    Returns:
        dict or None: Matching skill dict, or None if not found
    """
    # Try exact match first
    skill_name_clean = skill_name.lower().strip()
    for skill in available_skills:
        if skill['name'].lower().strip() == skill_name_clean:
            log_debug(f"Exact match found: '{skill['name']}' matches '{skill_name}'")
            return skill
    
    # Use the new precise matching system to find best matches for each available skill
    best_skill = None
    best_confidence = 0.0
    
    for skill in available_skills:
        # Check if this available skill matches our target skill
        match_result = find_best_real_skill_match(skill['name'], skill_name, threshold=0.8)
        
        if match_result['is_target_match'] and match_result['confidence'] > best_confidence:
            best_skill = skill
            best_confidence = match_result['confidence']
            log_debug(f"Real skill match: '{skill['name']}' -> '{match_result['match']}' matches target '{skill_name}' (confidence: {match_result['confidence']:.3f})")
    
    if best_skill:
        log_debug(f"Best match found: '{best_skill['name']}' for target '{skill_name}' (confidence: {best_confidence:.3f})")
        return best_skill
    
    log_debug(f"No match found for '{skill_name}' in available skills")
    return None

def create_purchase_plan(available_skills, config):
    """
    Create optimized purchase plan based on available skills and config.
    
    Simple logic:
    - If gold skill appears → buy it
    - If gold skill not available but base skill appears → buy base skill
    
    Args:
        available_skills: List of skill dicts with 'name' and 'price'
        config: Config dict from skills.json
    
    Returns:
        List of skills to purchase in order
    """
    skill_priority = config.get("skill_priority", [])
    gold_upgrades = config.get("gold_skill_upgrades", {})
    
    # Create lookup for available skills (exact match)
    available_by_name = {skill['name']: skill for skill in available_skills}
    
    purchase_plan = []
    
    log_info(f"Creating purchase plan")
    log_debug(f"Priority list: {len(skill_priority)} skills")
    log_debug(f"Gold upgrades: {len(gold_upgrades)} relationships")
    log_debug(f"Available skills: {len(available_skills)} skills")
    
    for priority_skill in skill_priority:
        # Check if this is a gold skill (key in gold_upgrades)
        if priority_skill in gold_upgrades:
            base_skill_name = gold_upgrades[priority_skill]
            
            # Rule 1: If gold skill appears → buy it (try exact then fuzzy match)
            skill = available_by_name.get(priority_skill) or find_matching_skill(priority_skill, available_skills)
            if skill:
                purchase_plan.append(skill)
                log_info(f"Gold skill found: {skill['name']} - {skill['price']}")
                
            # Rule 2: If gold not available but base skill appears → buy base
            else:
                base_skill = available_by_name.get(base_skill_name) or find_matching_skill(base_skill_name, available_skills)
                if base_skill:
                    purchase_plan.append(base_skill)
                    log_info(f"Base skill found: {base_skill['name']} - {base_skill['price']} (for {priority_skill}")
                
        else:
            # Regular skill - just buy if available (try exact then fuzzy match)
            skill = available_by_name.get(priority_skill) or find_matching_skill(priority_skill, available_skills)
            if skill:
                purchase_plan.append(skill)
                log_info(f"Regular skill: {skill['name']} - {skill['price']}")
    
    return purchase_plan

def filter_affordable_skills(purchase_plan, available_points):
    """
    Filter purchase plan to only include skills that can be afforded.
    
    Args:
        purchase_plan: List of skills to purchase
        available_points: Available skill points
    
    Returns:
        tuple: (affordable_skills, total_cost, remaining_points)
    """
    affordable_skills = []
    total_cost = 0
    
    log_info(f"\n[INFO] Filtering skills by available points ({available_points})")
    log_info(f"=" * 60)
    
    for skill in purchase_plan:
        try:
            skill_cost = int(skill['price']) if skill['price'].isdigit() else 0
            
            if total_cost + skill_cost <= available_points:
                affordable_skills.append(skill)
                total_cost += skill_cost
                remaining_points = available_points - total_cost
                log_info(f"✅ {skill['name']:<30} | Cost: {skill_cost:<4} | Remaining: {remaining_points}")
            else:
                needed_points = skill_cost - (available_points - total_cost)
                log_info(f"❌ {skill['name']:<30} | Cost: {skill_cost:<4} | Need {needed_points} more points")
                
        except ValueError:
            log_info(f"⚠️  {skill['name']:<30} | Invalid price: {skill['price']}")
    
    remaining_points = available_points - total_cost
    
    log_info(f"=" * 60)
    log_info(f"Budget Summary:")
    log_info(f"   Available points: {available_points}")
    log_info(f"   Total cost: {total_cost}")
    log_info(f"   Remaining points: {remaining_points}")
    log_info(f"   Affordable skills: {len(affordable_skills)}/{len(purchase_plan)}")
    
    return affordable_skills, total_cost, remaining_points

def calculate_total_cost(purchase_plan):
    """Calculate total skill points needed for purchase plan."""
    total = sum(int(skill['price']) for skill in purchase_plan if skill['price'].isdigit())
    return total

def print_purchase_summary(purchase_plan):
    """Print a nice summary of the purchase plan."""
    if not purchase_plan:
        log_info(f"📋 No skills to purchase based on your priority list.")
        return
    
    log_info(f"\n📋 PURCHASE PLAN:")
    log_info(f"=" * 60)
    
    total_cost = 0
    for i, skill in enumerate(purchase_plan, 1):
        price = skill['price']
        if price.isdigit():
            total_cost += int(price)
        log_info(f"  {i:2d}. {skill['name']:<30} | Price: {price}")
    
    log_info(f"=" * 60)
    log_info(f"Total Cost: {total_cost} skill points")
    log_info(f"Skills to buy: {len(purchase_plan)}")

def test_purchase_optimizer():
    """Test function for the purchase optimizer."""
    log_info(f"🧪 Testing Purchase Optimizer...")
    
    # Load config
    config = load_skill_config()

    # Live scan via scroll to collect skills from the UI
    log_info(f"Scanning skills via scroll to build available list...")
    scan = scan_all_skills_with_scroll(confidence=0.9, brightness_threshold=150, max_scrolls=20)
    available_skills = [{"name": s.get("name", "Unknown"), "price": s.get("price", "0")} for s in scan.get("all_skills", [])]

    if not available_skills:
        log_warning(f"No skills found via scan. Falling back to sample data.")
        available_skills = [
            {"name": "Shooting For Victory", "price": "160"},
            {"name": "Homestretch Haste", "price": "153"},
            {"name": "Deep Breaths", "price": "144"},
            {"name": "Pressure", "price": "160"},
            {"name": "The Coast Is Clear", "price": "220"},
            {"name": "I Can See Right Through You", "price": "110"},
            {"name": "After-School Stroll", "price": "170"},
            {"name": "Uma Stan", "price": "160"}
        ]

    # Create purchase plan
    purchase_plan = create_purchase_plan(available_skills, config)
    
    # Print summary
    print_purchase_summary(purchase_plan)

if __name__ == "__main__":
    test_purchase_optimizer()
