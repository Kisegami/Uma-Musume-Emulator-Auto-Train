"""
Scenario system for supporting multiple game scenarios.

This module provides a base scenario class and scenario implementations
for different game modes (e.g., URA, new scenario).
"""

from core.scenarios.base_scenario import BaseScenario
from core.scenarios.scenario_manager import get_scenario, load_scenario

__all__ = ['BaseScenario', 'get_scenario', 'load_scenario']

