# Normal Event Detection and Handling Workflow

This document explains the complete workflow of how events are detected and handled during normal bot operation.

## Overview

The event handling system runs continuously in the main game loop (`career_lobby()` in `core_unity/execute.py`). It checks for events on every loop iteration and processes them automatically.

## Complete Workflow

### Step 1: Main Loop - Screenshot and Event Detection

**Location**: `core_unity/execute.py` → `career_lobby()` function

```python
# Main loop runs continuously
while True:
    # Take screenshot
    screenshot = take_screenshot()
    
    # Check for events using template matching
    event_choice_region = (6, 450, 126, 1776)  # Left side of screen
    event_matches = match_template(
        screenshot, 
        "assets/icons/event_choice_1.png", 
        confidence=0.7, 
        region=event_choice_region
    )
```

**What happens:**
- Takes a screenshot of the current game state
- Searches for event choice icons in the left side of the screen (region: x=6, y=450, width=126, height=1776)
- Uses template matching with `event_choice_1.png` at 70% confidence
- If matches found → Event detected, proceed to Step 2
- If no matches → Continue loop, check other UI elements

**Time**: ~50-100ms (screenshot + template matching)

---

### Step 2: Event Analysis - `handle_event_choice()`

**Location**: `core_unity/event_handling.py` → `handle_event_choice()` function

When events are detected, the bot calls `handle_event_choice()` which performs:

#### 2.1: Wait for Stabilization (1500ms)
```python
time.sleep(1.5)  # Wait for event screen to fully appear
```
**Purpose**: Ensures the event screen is fully loaded and stable before OCR
**Time**: 1500ms (fixed delay)

#### 2.2: Re-validate Event Choices
```python
recheck_count, recheck_locations = count_event_choices()
```
**Purpose**: Confirms event choices are still visible after delay
- If count = 0 → Skip analysis, return early
- If count > 0 → Continue with analysis
**Time**: ~50-100ms

#### 2.3: Extract Event Name via OCR
```python
event_image = capture_region(EVENT_REGION)  # (168, 347, 825, 434)
event_name = extract_event_name_text(event_image)
```
**Purpose**: Reads the event name from the screen using OCR
- Captures the event name region
- Extracts text using OCR
- If extraction fails → Save debug image, fallback to top choice
**Time**: ~100-200ms (capture + OCR)

#### 2.4: Handle Hardcoded Events
```python
if "Tutorial" in event_name:
    return 2, True, choice_locations  # Always choose 2nd choice
    
if "A Team at Last" in event_name:
    return last_choice, True, choice_locations  # Always choose last choice
```
**Purpose**: Special handling for specific events
**Time**: <1ms

#### 2.5: Search Event Database
```python
found_events = search_events_exact(event_name)
if not found_events:
    found_events = search_events_fuzzy(event_name)
```
**Purpose**: Find event in database to get available options
- First tries exact match in all databases (support_card.json, uma_data.json, ura_finale.json)
- If no exact match, tries fuzzy search (partial matches)
**Time**: ~10-50ms (depends on database size)

#### 2.6: Count Event Choices on Screen
```python
choices_found, choice_locations = count_event_choices()
```
**Purpose**: Count how many choices are visible (1, 2, 3, etc.)
- Uses template matching with brightness filtering
- Returns count and locations for clicking
**Time**: ~50-100ms

#### 2.7: Load Priorities and Analyze Options
```python
priorities = load_event_priorities()  # From event_priority.json
analysis = analyze_event_options(options, priorities)
```
**Purpose**: Determine which choice is best based on:
- Good choices (rewards to prefer)
- Bad choices (rewards to avoid)
- Priority order
**Time**: ~0.2-1ms

#### 2.8: Map Option to Choice Number
```python
# Map "Top Option" → 1, "Bottom Option" → 2, etc.
choice_number = map_option_to_choice(recommended_option, choices_found)
```
**Purpose**: Convert option name to actual choice number (1, 2, 3...)
**Time**: <1ms

#### 2.9: Return Result
```python
return choice_number, success, choice_locations
```
**Returns**:
- `choice_number`: Which choice to select (1, 2, 3, etc.)
- `success`: Whether analysis was successful
- `choice_locations`: Pre-found locations for clicking

**Total Time for Step 2**: ~1763ms
- Sleep delay: 1500ms
- Actual processing: ~263ms

---

### Step 3: Click Event Choice

**Location**: `core_unity/execute.py` → After `handle_event_choice()` returns

```python
if success:
    click_success = click_event_choice(choice_number, choice_locations)
    if click_success:
        log_info(f"Successfully selected choice {choice_number}")
        time.sleep(0.5)  # Wait for event to process
        continue  # Continue main loop
```

**What happens**:
1. Uses pre-found `choice_locations` from Step 2
2. Calculates center point of the chosen choice
3. Taps on that location
4. Waits 0.5 seconds for event to process
5. Continues main loop

**Time**: ~500ms (click + wait)

**Fallback behavior**:
- If `success = False` → Click top choice (first match)
- If `choice_locations` is empty → Skip clicking, continue loop
- If click fails → Fallback to top choice

---

## Complete Timeline

For a typical event:

```
Main Loop Iteration:
├─ Screenshot:                    ~50ms
├─ Template matching:              ~50ms
└─ Event detected? → Yes
   ├─ handle_event_choice():
   │  ├─ Sleep (stabilization):   1500ms
   │  ├─ Re-validate choices:     ~50ms
   │  ├─ Extract event name:      ~150ms
   │  ├─ Search database:         ~30ms
   │  ├─ Count choices:           ~50ms
   │  ├─ Analyze options:         ~1ms
   │  └─ Total:                   ~1781ms
   ├─ click_event_choice():        ~10ms
   └─ Wait for processing:        500ms

Total: ~2391ms (~2.4 seconds per event)
```

**Breakdown**:
- **Sleep delay**: 1500ms (63% of total time)
- **Actual processing**: ~291ms (12% of total time)
- **Wait after click**: 500ms (21% of total time)
- **Other overhead**: ~100ms (4% of total time)

---

## Error Handling

### OCR Failure
- Saves debug image: `debug_event_detection_failure_[timestamp].png`
- If `stop_on_event_detection_failure = true` in config → Bot stops
- Otherwise → Falls back to top choice

### No Choices Found
- If choices disappear after delay → Skip clicking, continue loop
- Logs warning message

### Event Not in Database
- Logs "Unknown event"
- Defaults to first choice (top choice)

### Click Failure
- Falls back to clicking first detected event icon
- Continues main loop

---

## Key Files

1. **Main Loop**: `core_unity/execute.py` (lines 221-314)
   - Event detection via template matching
   - Calls `handle_event_choice()`
   - Handles clicking and fallbacks

2. **Event Handling**: `core_unity/event_handling.py`
   - `handle_event_choice()`: Main analysis function
   - `count_event_choices()`: Count and locate choices
   - `click_event_choice()`: Click on specific choice
   - `search_events_exact()` / `search_events_fuzzy()`: Database search
   - `analyze_event_options()`: Option analysis

3. **Configuration**:
   - `event_priority.json`: Good/bad choice definitions
   - `assets/events/support_card.json`: Event database
   - `assets/events/uma_data.json`: Character event database
   - `assets/events/ura_finale.json`: Ura finale events

---

## Performance Optimization Opportunities

1. **Reduce sleep delay**: Currently 1500ms, could potentially be reduced if screen stabilizes faster
2. **Cache database**: Event databases are already cached after first load
3. **Parallel processing**: Could potentially do OCR and database search in parallel (but minimal benefit)
4. **Skip re-validation**: If confident event is stable, could skip the re-check

**Current bottleneck**: The 1.5 second sleep delay (63% of total time) is intentional for reliability.

