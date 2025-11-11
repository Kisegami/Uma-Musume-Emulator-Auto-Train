import json
import os
from difflib import SequenceMatcher
from utils.skill_recognizer import scan_all_skills_with_scroll

# Load config for debug mode
try:
    with open("config.json", "r") as f:
        config = json.load(f)
    DEBUG_MODE = config.get("debug_mode", False)
except:
    DEBUG_MODE = False

def debug_print(message):
    """Print debug message only if DEBUG_MODE is enabled"""
    if DEBUG_MODE:
        print(message)

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
                debug_print(f"[DEBUG] Loading skills from config file: {config_path}")
        except Exception as e:
            debug_print(f"[DEBUG] Could not read config.json, using default skills.json: {e}")
            config_path = "skills.json"
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
            debug_print(f"[DEBUG] Successfully loaded skills config from: {config_path}")
            return config
    except FileNotFoundError:
        print(f"[ERROR] {config_path} not found. Creating default config")
        default_config = {
            "skill_priority": [],
            "gold_skill_upgrades": {}
        }
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(default_config, f, indent=4)
        return default_config
    except Exception as e:
        print(f"[ERROR] Error loading {config_path}: {e}")
        return {"skill_priority": [], "gold_skill_upgrades": {}}

def fuzzy_match_skill_name(skill_name, target_name, threshold=0.8):
    """
    Check if two skill names match using fuzzy matching.
    
    Args:
        skill_name: Name from OCR scan
        target_name: Name from config file
        threshold: Minimum similarity ratio (0.0 to 1.0)
    
    Returns:
        bool: True if names match closely enough
    """
    # Normalize both names for comparison
    name1 = skill_name.lower().strip()
    name2 = target_name.lower().strip()
    
    # Exact match first
    if name1 == name2:
        return True
    
    # Fuzzy match using sequence matcher
    similarity = SequenceMatcher(None, name1, name2).ratio()
    return similarity >= threshold

def find_matching_skill(skill_name, available_skills):
    """
    Find a skill in available_skills that matches skill_name (with fuzzy matching).
    
    Args:
        skill_name: Name to search for
        available_skills: List of available skill dicts
    
    Returns:
        dict or None: Matching skill dict, or None if not found
    """
    # Try exact match first
    for skill in available_skills:
        if skill['name'].lower().strip() == skill_name.lower().strip():
            return skill
    
    # Try fuzzy matching
    for skill in available_skills:
        if fuzzy_match_skill_name(skill['name'], skill_name):
            debug_print(f"[DEBUG] Fuzzy match: '{skill['name']}' matches '{skill_name}'")
            return skill
    
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
    
    print("[INFO] Creating purchase plan")
    debug_print(f"[DEBUG] Priority list: {len(skill_priority)} skills")
    debug_print(f"[DEBUG] Gold upgrades: {len(gold_upgrades)} relationships")
    debug_print(f"[DEBUG] Available skills: {len(available_skills)} skills")
    
    for priority_skill in skill_priority:
        # Check if this is a gold skill (key in gold_upgrades)
        if priority_skill in gold_upgrades:
            base_skill_name = gold_upgrades[priority_skill]
            
            # Rule 1: If gold skill appears → buy it (try exact then fuzzy match)
            skill = available_by_name.get(priority_skill) or find_matching_skill(priority_skill, available_skills)
            if skill:
                purchase_plan.append(skill)
                print(f"[INFO] Gold skill found: {skill['name']} - {skill['price']}")
                
            # Rule 2: If gold not available but base skill appears → buy base
            else:
                base_skill = available_by_name.get(base_skill_name) or find_matching_skill(base_skill_name, available_skills)
                if base_skill:
                    purchase_plan.append(base_skill)
                    print(f"[INFO] Base skill found: {base_skill['name']} - {base_skill['price']} (for {priority_skill})")
                
        else:
            # Regular skill - just buy if available (try exact then fuzzy match)
            skill = available_by_name.get(priority_skill) or find_matching_skill(priority_skill, available_skills)
            if skill:
                purchase_plan.append(skill)
                print(f"[INFO] Regular skill: {skill['name']} - {skill['price']}")
    
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
    
    print(f"\n[INFO] Filtering skills by available points ({available_points})")
    print("=" * 60)
    
    for skill in purchase_plan:
        try:
            skill_cost = int(skill['price']) if skill['price'].isdigit() else 0
            
            if total_cost + skill_cost <= available_points:
                affordable_skills.append(skill)
                total_cost += skill_cost
                remaining_points = available_points - total_cost
                print(f"✅ {skill['name']:<30} | Cost: {skill_cost:<4} | Remaining: {remaining_points}")
            else:
                needed_points = skill_cost - (available_points - total_cost)
                print(f"❌ {skill['name']:<30} | Cost: {skill_cost:<4} | Need {needed_points} more points")
                
        except ValueError:
            print(f"⚠️  {skill['name']:<30} | Invalid price: {skill['price']}")
    
    remaining_points = available_points - total_cost
    
    print("=" * 60)
    print(f"[INFO] Budget Summary:")
    print(f"   Available points: {available_points}")
    print(f"   Total cost: {total_cost}")
    print(f"   Remaining points: {remaining_points}")
    print(f"   Affordable skills: {len(affordable_skills)}/{len(purchase_plan)}")
    
    return affordable_skills, total_cost, remaining_points

def calculate_total_cost(purchase_plan):
    """Calculate total skill points needed for purchase plan."""
    total = sum(int(skill['price']) for skill in purchase_plan if skill['price'].isdigit())
    return total

def print_purchase_summary(purchase_plan):
    """Print a nice summary of the purchase plan."""
    if not purchase_plan:
        print("📋 No skills to purchase based on your priority list.")
        return
    
    print(f"\n📋 PURCHASE PLAN:")
    print("=" * 60)
    
    total_cost = 0
    for i, skill in enumerate(purchase_plan, 1):
        price = skill['price']
        if price.isdigit():
            total_cost += int(price)
        print(f"  {i:2d}. {skill['name']:<30} | Price: {price}")
    
    print("=" * 60)
    print(f"Total Cost: {total_cost} skill points")
    print(f"Skills to buy: {len(purchase_plan)}")

def test_purchase_optimizer():
    """Test function for the purchase optimizer."""
    print("🧪 Testing Purchase Optimizer...")
    
    # Load config
    config = load_skill_config()

    # Live scan via scroll to collect skills from the UI
    print("[INFO] Scanning skills via scroll to build available list...")
    scan = scan_all_skills_with_scroll(confidence=0.9, brightness_threshold=150, max_scrolls=20)
    available_skills = [{"name": s.get("name", "Unknown"), "price": s.get("price", "0")} for s in scan.get("all_skills", [])]

    if not available_skills:
        print("[WARNING] No skills found via scan. Falling back to sample data.")
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
