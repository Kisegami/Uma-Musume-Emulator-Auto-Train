"""
URA scenario implementation (default/old scenario).

This is the base scenario that matches the current implementation.
Most methods just delegate to the existing core modules.
"""

from core_unity.scenarios.base_scenario import BaseScenario
from utils_unity.constants_phone import *


class UraScenario(BaseScenario):
    """
    URA scenario implementation.
    
    This is the default scenario that uses the existing codebase.
    It loads constants from utils_unity.constants_phone and uses all
    existing core modules as-is.
    """
    
    def __init__(self):
        super().__init__("ura")
    
    def _load_constants(self):
        """Load URA scenario constants from utils_unity.constants_phone"""
        from utils_unity.constants_phone import (
            SUPPORT_CARD_ICON_REGION, TURN_REGION, FAILURE_REGION, YEAR_REGION,
            CRITERIA_REGION, SPD_REGION, STA_REGION, PWR_REGION, GUTS_REGION, WIT_REGION,
            SKILL_PTS_REGION, FAILURE_REGION_SPD, FAILURE_REGION_STA, FAILURE_REGION_PWR,
            FAILURE_REGION_GUTS, FAILURE_REGION_WIT, EVENT_REGION, RACE_CARD_REGION,
            MOOD_REGION, MOOD_LIST
        )
        
        self._constants = {
            "SUPPORT_CARD_ICON_REGION": SUPPORT_CARD_ICON_REGION,
            "TURN_REGION": TURN_REGION,
            "FAILURE_REGION": FAILURE_REGION,
            "YEAR_REGION": YEAR_REGION,
            "CRITERIA_REGION": CRITERIA_REGION,
            "SPD_REGION": SPD_REGION,
            "STA_REGION": STA_REGION,
            "PWR_REGION": PWR_REGION,
            "GUTS_REGION": GUTS_REGION,
            "WIT_REGION": WIT_REGION,
            "SKILL_PTS_REGION": SKILL_PTS_REGION,
            "FAILURE_REGION_SPD": FAILURE_REGION_SPD,
            "FAILURE_REGION_STA": FAILURE_REGION_STA,
            "FAILURE_REGION_PWR": FAILURE_REGION_PWR,
            "FAILURE_REGION_GUTS": FAILURE_REGION_GUTS,
            "FAILURE_REGION_WIT": FAILURE_REGION_WIT,
            "EVENT_REGION": EVENT_REGION,
            "RACE_CARD_REGION": RACE_CARD_REGION,
            "MOOD_REGION": MOOD_REGION,
            "MOOD_LIST": MOOD_LIST,
        }
    
    # All methods inherit from BaseScenario and delegate to existing core modules
    # No overrides needed since this is the default scenario

