"""
New scenario implementation template.

This is a template for implementing a new game scenario.
Override methods here to provide scenario-specific behavior.

To use this:
1. Copy this file and rename it to your scenario name
2. Override methods that need different behavior
3. Update scenario_manager.py to load your scenario
4. Add scenario-specific constants and asset paths
"""

from core_unity.scenarios.base_scenario import BaseScenario
from typing import Optional, Dict, Any
from PIL import Image
from utils_unity.log import log_info, log_debug


class NewScenario(BaseScenario):
    """
    New scenario implementation.
    
    Override methods here to provide scenario-specific behavior.
    Methods not overridden will use the base implementation (URA scenario).
    """
    
    def __init__(self):
        super().__init__("new_scenario")
    
    def _load_constants(self):
        """
        Load new scenario-specific constants.
        
        Override this to provide different regions, coordinates, etc.
        """
        # Example: Different regions for new scenario
        # You can define new regions here or import from a new constants file
        self._constants = {
            # Example regions (adjust these to match your new scenario)
            "SUPPORT_CARD_ICON_REGION": (876, 253, 1080, 1171),  # May be different
            "TURN_REGION": (21, 149, 210, 239),  # May be different
            "FAILURE_REGION": (45, 1357, 1044, 1465),  # May be different
            "YEAR_REGION": (21, 66, 333, 96),  # May be different
            "CRITERIA_REGION": (363, 153, 867, 201),  # May be different
            "SPD_REGION": (108, 1284, 204, 1326),  # May be different
            "STA_REGION": (273, 1284, 375, 1329),  # May be different
            "PWR_REGION": (444, 1284, 543, 1326),  # May be different
            "GUTS_REGION": (621, 1281, 711, 1323),  # May be different
            "WIT_REGION": (780, 1284, 876, 1323),  # May be different
            "SKILL_PTS_REGION": (903, 1383, 1035, 1443),  # May be different
            "FAILURE_REGION_SPD": (109, 1404, 205, 1442),  # May be different
            "FAILURE_REGION_STA": (308, 1404, 389, 1442),  # May be different
            "FAILURE_REGION_PWR": (501, 1404, 579, 1442),  # May be different
            "FAILURE_REGION_GUTS": (691, 1404, 769, 1442),  # May be different
            "FAILURE_REGION_WIT": (881, 1404, 962, 1442),  # May be different
            "EVENT_REGION": (168, 347, 825, 434),  # May be different
            "RACE_CARD_REGION": (0, 0, 610, 220),  # May be different
            "MOOD_REGION": (819, 211, 969, 274),  # May be different
            "MOOD_LIST": ["AWFUL", "BAD", "NORMAL", "GOOD", "GREAT", "UNKNOWN"],
        }
    
    def get_asset_path(self, asset_type: str, asset_name: str) -> str:
        """
        Override if assets are in different locations for new scenario.
        
        Example: If new scenario has assets in assets/new_scenario/buttons/
        """
        # Option 1: Use scenario-specific asset folder
        # return f"assets/{self.name}/{asset_type}/{asset_name}"
        
        # Option 2: Use same assets (default)
        return super().get_asset_path(asset_type, asset_name)
    
    # ========== Override methods that need different behavior ==========
    
    # Example: Override check_training if new scenario has different detection logic
    # def check_training(self):
    #     """New scenario may have different training detection logic"""
    #     log_debug(f"[{self.name}] Using new scenario training detection")
    #     # Implement new detection logic here
    #     # You can still call base methods if needed
    #     return super().check_training()  # Or implement completely new logic
    
    # Example: Override check_failure if regions are different
    # def check_failure(self, screenshot: Optional[Image.Image] = None, train_type: str = None):
    #     """New scenario may have different failure rate regions"""
    #     log_debug(f"[{self.name}] Using new scenario failure detection")
    #     # Use self.get_constant("FAILURE_REGION_SPD") to get scenario-specific region
    #     # Implement new detection logic here
    #     return super().check_failure(screenshot, train_type)
    
    # Example: Override do_train if training coordinates are different
    # def do_train(self, train_type: str):
    #     """New scenario may have different training button coordinates"""
    #     log_debug(f"[{self.name}] Using new scenario training coordinates")
    #     # Define new coordinates here
    #     training_coords = {
    #         "spd": (165, 1557),  # May be different
    #         "sta": (357, 1563),  # May be different
    #         # ... etc
    #     }
    #     # Implement new logic here
    
    # Example: Override career_lobby if main loop logic is different
    # def career_lobby(self):
    #     """New scenario may have different main loop logic"""
    #     log_info(f"[{self.name}] Starting new scenario career lobby")
    #     # Implement new main loop logic here
    #     # You can still reuse common functions like handle_event_choice()
    
    # Note: Methods like handle_event_choice(), check_skill_points_cap(), etc.
    # are typically reusable and don't need overriding unless the new scenario
    # has fundamentally different event/skill systems.
    
    # ========== New Methods (Not in Base Scenario) ==========
    # You can add completely new methods that don't exist in the base class
    
    # Example: Unity Cup specific method
    # def check_unity_cup_feature(self, screenshot):
    #     """New method specific to Unity Cup scenario"""
    #     log_debug(f"[{self.name}] Checking Unity Cup feature...")
    #     # Your new detection logic here
    #     return result
    
    # Example: New training feature detection
    # def check_training_bonus(self, screenshot):
    #     """Detect training bonuses specific to new scenario"""
    #     log_debug(f"[{self.name}] Checking training bonus...")
    #     # Your new detection logic here
    #     return bonus_data
    
    # Example: New UI element handling
    # def handle_new_ui_element(self, screenshot):
    #     """Handle new UI elements in Unity Cup"""
    #     log_debug(f"[{self.name}] Handling new UI element...")
    #     # Your new handling logic here
    #     return success

