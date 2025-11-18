"""
Scenario manager for loading and switching between different game scenarios.
"""

import json
import os
from typing import Optional
from core.scenarios.base_scenario import BaseScenario
from utils.log import log_info, log_warning, log_error, log_debug

# Global scenario instance
_current_scenario: Optional[BaseScenario] = None


def load_scenario(scenario_name: Optional[str] = None) -> BaseScenario:
    """
    Load a scenario by name.
    
    Args:
        scenario_name: Name of the scenario to load. If None, loads from config.
        
    Returns:
        BaseScenario instance
    """
    global _current_scenario
    
    # If no name provided, try to load from config
    if scenario_name is None:
        try:
            with open("config.json", "r", encoding="utf-8") as f:
                config = json.load(f)
                scenario_name = config.get("scenario", "ura")
        except Exception as e:
            log_warning(f"Could not load scenario from config: {e}, defaulting to 'ura'")
            scenario_name = "ura"
    
    # Normalize scenario name
    scenario_name = scenario_name.lower().strip()
    
    # Load the appropriate scenario
    if scenario_name == "ura" or scenario_name == "default":
        from core.scenarios.ura_scenario import UraScenario
        _current_scenario = UraScenario()
    elif scenario_name == "new_scenario" or scenario_name == "new":
        from core.scenarios.new_scenario import NewScenario
        _current_scenario = NewScenario()
    elif scenario_name == "unity_cup":
        # Example: Unity Cup scenario (uncomment when ready)
        # from core.scenarios.unity_cup_scenario import UnityCupScenario
        # _current_scenario = UnityCupScenario()
        log_warning(f"Unity Cup scenario not yet implemented, defaulting to 'ura'")
        from core.scenarios.ura_scenario import UraScenario
        _current_scenario = UraScenario()
    else:
        log_warning(f"Unknown scenario '{scenario_name}', defaulting to 'ura'")
        from core.scenarios.ura_scenario import UraScenario
        _current_scenario = UraScenario()
    
    log_info(f"Loaded scenario: {_current_scenario.name}")
    return _current_scenario


def get_scenario() -> BaseScenario:
    """
    Get the current scenario instance.
    
    Returns:
        BaseScenario instance (loads default if not already loaded)
    """
    global _current_scenario
    
    if _current_scenario is None:
        _current_scenario = load_scenario()
    
    return _current_scenario


def set_scenario(scenario: BaseScenario):
    """
    Set the current scenario instance (for testing or manual switching).
    
    Args:
        scenario: BaseScenario instance to set
    """
    global _current_scenario
    _current_scenario = scenario
    log_info(f"Scenario set to: {scenario.name}")

