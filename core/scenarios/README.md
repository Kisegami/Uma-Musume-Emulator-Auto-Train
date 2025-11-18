# Scenario System

This directory contains the scenario system that allows supporting multiple game scenarios (e.g., URA, new scenario) while reusing common code.

## Structure

- `base_scenario.py` - Base class that defines the interface for all scenarios
- `scenario_manager.py` - Manager for loading and switching between scenarios
- `ura_scenario.py` - URA scenario implementation (default/old scenario)
- `new_scenario.py` - Template for implementing new scenarios

## How It Works

1. **Base Scenario Class**: Defines all methods that can be overridden by scenario-specific implementations
2. **Scenario Manager**: Loads the appropriate scenario based on config.json
3. **Scenario Implementations**: Override only methods that need different behavior

## Adding a New Scenario

### Step 1: Create Scenario File

Copy `new_scenario.py` and rename it (e.g., `my_scenario.py`):

```python
from core.scenarios.base_scenario import BaseScenario

class MyScenario(BaseScenario):
    def __init__(self):
        super().__init__("my_scenario")
    
    def _load_constants(self):
        # Define scenario-specific regions, coordinates, etc.
        self._constants = {
            "SUPPORT_CARD_ICON_REGION": (876, 253, 1080, 1171),
            # ... other constants
        }
    
    # Override methods that need different behavior
    def check_training(self):
        # New scenario-specific training detection logic
        pass
```

### Step 2: Register Scenario

Update `scenario_manager.py` to load your scenario:

```python
elif scenario_name == "my_scenario":
    from core.scenarios.my_scenario import MyScenario
    _current_scenario = MyScenario()
```

### Step 3: Configure

Add to `config.json`:

```json
{
  "scenario": "my_scenario"
}
```

## What Can Be Overridden

### State Detection (if regions differ)
- `check_turn()`, `check_mood()`, `check_current_year()`, etc.

### Training (if detection/logic differs)
- `check_training()`, `do_train()`, `check_failure()`, `check_support_card()`, etc.

### Races (if logic differs)
- `find_and_do_race()`, `race_day()`, etc.

### Main Loop (if logic differs)
- `career_lobby()`, `do_rest()`, `do_recreation()`, etc.

### Assets (if paths differ)
- Override `get_asset_path()` if assets are in different locations

## What Is Reusable

These methods typically work across scenarios and don't need overriding:
- Event handling: `handle_event_choice()`, `click_event_choice()`
- Skill purchase: `check_skill_points_cap()`
- Most utility functions

## Example: Overriding Training Coordinates

If the new scenario has different training button coordinates:

```python
def do_train(self, train_type: str):
    """New scenario has different training coordinates"""
    from utils.input import triple_click
    from core.training_handling import go_to_training
    
    if not go_to_training():
        return
    
    # New scenario-specific coordinates
    training_coords = {
        "spd": (200, 1600),  # Different from URA
        "sta": (400, 1600),
        # ... etc
    }
    
    if train_type in training_coords:
        x, y = training_coords[train_type]
        triple_click(x, y, interval=0.1)
```

## Example: Overriding Failure Detection Regions

If failure rate regions are different:

```python
def check_failure(self, screenshot, train_type):
    """New scenario has different failure rate regions"""
    # Get scenario-specific region
    region_key = f"FAILURE_REGION_{train_type.upper()}"
    region = self.get_constant(region_key)
    
    # Use region for detection
    # ... implement detection logic
```

## Adding New Methods (Not Overriding)

You can add completely new methods that don't exist in the base class:

```python
class MyScenario(BaseScenario):
    # ... existing methods ...
    
    def check_new_feature(self, screenshot):
        """New method specific to this scenario"""
        log_debug(f"[{self.name}] Checking new feature...")
        # Your detection logic
        return result
    
    def handle_new_ui_element(self, screenshot):
        """Handle new UI elements"""
        log_debug(f"[{self.name}] Handling new UI element...")
        # Your handling logic
        return success
```

### Using New Methods in execute.py

**Option 1: Check if method exists (works for all scenarios)**
```python
scenario = get_scenario()

if scenario.has_method("check_new_feature"):
    result = scenario.check_new_feature(screenshot)
    # Handle result
```

**Option 2: Scenario-specific check**
```python
scenario = get_scenario()

if scenario.name == "my_scenario":
    result = scenario.check_new_feature(screenshot)
    # Handle result
```

**Option 3: Dynamic call**
```python
scenario = get_scenario()
result = scenario.call_method("check_new_feature", screenshot)
```

## Best Practices

1. **Only override what's different**: Don't override methods that work the same
2. **Add new methods freely**: New scenario-specific methods are encouraged
3. **Use base methods when possible**: Call `super().method()` if you need base behavior plus additions
4. **Store constants in `_constants`**: Use `get_constant()` to access scenario-specific values
5. **Use asset paths**: Override `get_asset_path()` if assets are in different folders
6. **Test thoroughly**: Make sure your scenario works before committing

## Current Scenarios

- **ura** (default): Original URA scenario implementation
- **new_scenario**: Template for new scenarios (not functional, use as template)

