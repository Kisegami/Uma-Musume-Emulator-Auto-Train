"""
Base scenario class that defines the interface for all scenario implementations.

All scenario-specific implementations should inherit from this class and
override methods that need different behavior for their scenario.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Tuple
from PIL import Image


class BaseScenario(ABC):
    """
    Base class for game scenario implementations.
    
    This class defines the interface that all scenarios must implement.
    Scenarios can override methods to provide scenario-specific behavior
    while inheriting common functionality.
    """
    
    def __init__(self, name: str):
        """
        Initialize the scenario.
        
        Args:
            name: Name of the scenario (e.g., 'ura', 'new_scenario')
        """
        self.name = name
        self._constants = None
        self._load_constants()
    
    @abstractmethod
    def _load_constants(self):
        """
        Load scenario-specific constants (regions, asset paths, etc.).
        This should populate self._constants with scenario-specific values.
        """
        pass
    
    def get_constant(self, key: str, default: Any = None) -> Any:
        """
        Get a scenario-specific constant.
        
        Args:
            key: Constant name
            default: Default value if not found
            
        Returns:
            The constant value or default
        """
        if self._constants is None:
            return default
        return self._constants.get(key, default)
    
    def get_asset_path(self, asset_type: str, asset_name: str) -> str:
        """
        Get the path to an asset file for this scenario.
        
        Args:
            asset_type: Type of asset (e.g., 'buttons', 'icons', 'ui')
            asset_name: Name of the asset file
            
        Returns:
            Path to the asset file
        """
        # Default: assets/{asset_type}/{asset_name}
        # Override in subclasses if assets are in different locations
        return f"assets/{asset_type}/{asset_name}"
    
    # ========== State Detection Methods ==========
    # These can be overridden if regions or detection logic differ
    
    def check_turn(self, screenshot: Optional[Image.Image] = None):
        """Check current turn. Can be overridden for different regions/logic."""
        from core.state import check_turn
        return check_turn(screenshot)
    
    def check_mood(self, screenshot: Optional[Image.Image] = None):
        """Check current mood. Can be overridden for different regions/logic."""
        from core.state import check_mood
        return check_mood(screenshot)
    
    def check_current_year(self, screenshot: Optional[Image.Image] = None):
        """Check current year. Can be overridden for different regions/logic."""
        from core.state import check_current_year
        return check_current_year(screenshot)
    
    def check_criteria(self, screenshot: Optional[Image.Image] = None):
        """Check criteria status. Can be overridden for different regions/logic."""
        from core.state import check_criteria
        return check_criteria(screenshot)
    
    def check_goal_name(self, screenshot: Optional[Image.Image] = None):
        """Check goal name. Can be overridden for different regions/logic."""
        from core.state import check_goal_name
        return check_goal_name(screenshot)
    
    def check_current_stats(self, screenshot: Optional[Image.Image] = None):
        """Check current stats. Can be overridden for different regions/logic."""
        from core.state import check_current_stats
        return check_current_stats(screenshot)
    
    def check_energy_bar(self, screenshot: Optional[Image.Image] = None):
        """Check energy bar. Can be overridden for different regions/logic."""
        from core.state import check_energy_bar
        return check_energy_bar(screenshot)
    
    def check_skill_points(self, screenshot: Optional[Image.Image] = None):
        """Check skill points. Can be overridden for different regions/logic."""
        from core.state import check_skill_points
        return check_skill_points(screenshot)
    
    # ========== Training Methods ==========
    # These can be overridden if training detection/logic differs
    
    def go_to_training(self):
        """Go to training screen. Can be overridden for different button paths."""
        from core.training_handling import go_to_training
        return go_to_training()
    
    def check_training(self):
        """Check training options. Can be overridden for different detection logic."""
        from core.training_handling import check_training
        return check_training()
    
    def do_train(self, train_type: str):
        """Perform training. Can be overridden for different coordinates/logic."""
        from core.training_handling import do_train
        return do_train(train_type)
    
    def check_support_card(self, screenshot: Optional[Image.Image] = None):
        """Check support cards. Can be overridden for different regions/logic."""
        from core.training_handling import check_support_card
        return check_support_card(screenshot)
    
    def check_failure(self, screenshot: Optional[Image.Image] = None, train_type: str = None):
        """Check failure rate. Can be overridden for different regions/logic."""
        from core.training_handling import check_failure
        return check_failure(screenshot, train_type)
    
    def check_hint(self, screenshot: Optional[Image.Image] = None):
        """Check for hint. Can be overridden for different regions/logic."""
        from core.training_handling import check_hint
        return check_hint(screenshot)
    
    def choose_best_training(self, training_results: Dict, config: Dict, current_stats: Dict):
        """Choose best training. Can be overridden for different logic."""
        from core.training_handling import choose_best_training
        return choose_best_training(training_results, config, current_stats)
    
    def calculate_training_score(self, support_detail: Dict, hint_found: bool, training_type: str):
        """Calculate training score. Can be overridden for different scoring."""
        from core.training_handling import calculate_training_score
        return calculate_training_score(support_detail, hint_found, training_type)
    
    # ========== Event Methods ==========
    # These typically don't need overriding (reusable across scenarios)
    
    def count_event_choices(self, screenshot: Optional[Image.Image] = None):
        """Count event choices. Usually reusable across scenarios."""
        from core.event_handling import count_event_choices
        return count_event_choices(screenshot)
    
    def handle_event_choice(self):
        """Handle event choice. Usually reusable across scenarios."""
        from core.event_handling import handle_event_choice
        return handle_event_choice()
    
    def click_event_choice(self, choice_number: int, choice_locations: list):
        """Click event choice. Usually reusable across scenarios."""
        from core.event_handling import click_event_choice
        return click_event_choice(choice_number, choice_locations)
    
    # ========== Race Methods ==========
    # These can be overridden if race handling differs
    
    def find_and_do_race(self):
        """Find and execute a race. Can be overridden for different logic."""
        from core.races_handling import find_and_do_race
        return find_and_do_race()
    
    def race_day(self):
        """Handle race day. Can be overridden for different logic."""
        from core.races_handling import race_day
        return race_day()
    
    # ========== Skill Methods ==========
    # These typically don't need overriding (reusable across scenarios)
    
    def check_skill_points_cap(self, screenshot: Optional[Image.Image] = None):
        """Check skill points cap. Usually reusable across scenarios."""
        from core.state import check_skill_points_cap
        return check_skill_points_cap(screenshot)
    
    # ========== Execute/Career Methods ==========
    # These can be overridden if main loop logic differs
    
    def do_rest(self):
        """Perform rest action. Can be overridden for different button paths."""
        from core.execute import do_rest
        return do_rest()
    
    def do_recreation(self):
        """Perform recreation action. Can be overridden for different button paths."""
        from core.execute import do_recreation
        return do_recreation()
    
    def career_lobby(self):
        """Main career lobby loop. Can be overridden for different logic."""
        from core.execute import career_lobby
        return career_lobby()
    
    def check_goal_criteria(self, criteria_data: Dict, year: str, turn: Any):
        """Check goal criteria. Can be overridden for different logic."""
        from core.execute import check_goal_criteria
        return check_goal_criteria(criteria_data, year, turn)
    
    # ========== Utility Methods ==========
    
    def is_pre_debut_year(self, year: str) -> bool:
        """Check if year is pre-debut. Can be overridden for different logic."""
        from core.races_handling import is_pre_debut_year
        return is_pre_debut_year(year)
    
    def is_racing_available(self, year: str) -> bool:
        """Check if racing is available. Can be overridden for different logic."""
        from core.races_handling import is_racing_available
        return is_racing_available(year)
    
    # ========== New Method Support ==========
    # Subclasses can add completely new methods here that don't exist in base
    # These will be available through the scenario instance
    
    def has_method(self, method_name: str) -> bool:
        """
        Check if scenario has a specific method (for new scenario-specific methods).
        
        Args:
            method_name: Name of the method to check
            
        Returns:
            True if method exists, False otherwise
        """
        return hasattr(self, method_name) and callable(getattr(self, method_name))
    
    def call_method(self, method_name: str, *args, **kwargs):
        """
        Call a method by name (useful for dynamic method calls).
        
        Args:
            method_name: Name of the method to call
            *args: Positional arguments
            **kwargs: Keyword arguments
            
        Returns:
            Result of method call, or None if method doesn't exist
        """
        if self.has_method(method_name):
            method = getattr(self, method_name)
            return method(*args, **kwargs)
        return None

