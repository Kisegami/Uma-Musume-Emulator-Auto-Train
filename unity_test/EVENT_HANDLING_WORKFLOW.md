# Event Handling Workflow Documentation

## Overview

The `event_handling.py` module handles the complete workflow of detecting and selecting event choices in the Uma Musume game. This document explains the workflow step-by-step.

## Main Workflow: `handle_event_choice()`

The main entry point is the `handle_event_choice()` function, which performs the following steps:

### Step 1: Wait and Validate (1.5 seconds)
- Waits 1.5 seconds for the event screen to stabilize
- Re-validates that event choices are visible using `count_event_choices()`
- If no choices are found, returns early with fallback

### Step 2: Extract Event Name via OCR
- Captures the event name region (`EVENT_REGION = (168, 347, 825, 434)`)
- Uses OCR to extract the event name text
- If extraction fails, saves a debug image and either stops (if configured) or falls back to top choice

### Step 3: Handle Hardcoded Events
- **Tutorial event**: Always chooses the 2nd choice
- **"A Team at Last" event**: Always chooses the bottom (last) choice

### Step 4: Search Event Database
- First attempts **exact match** search in all databases:
  - `support_card.json`
  - `uma_data.json`
  - `ura_finale.json`
- If no exact match, falls back to **fuzzy search**:
  - Prioritizes events starting with OCR text
  - Then events where OCR text is a complete word
  - Finally substring matches (if OCR text >= 5 characters)

### Step 5: Count Event Choices
- Uses template matching to find all event choice icons
- Searches in region: `(6, 450, 126, 1776)` - left side of screen
- Filters matches by brightness (threshold: 160.0) to avoid dim/false positives
- Returns count and locations of all bright choice icons

### Step 6: Load and Analyze Options
- Loads event priorities from `event_priority.json`
- Analyzes each option based on:
  - **Good choices**: Rewards that match priority list
  - **Bad choices**: Rewards that should be avoided
- Determines recommendation:
  - Prefers options with good choices and NO bad choices
  - If all options have bad choices, picks based on highest priority good choice
  - Falls back to option with fewest bad choices

### Step 7: Map Option to Choice Number
- Maps the recommended option name to a choice number:
  - 2 options: "top" → 1, "bottom" → 2
  - 3 options: "top" → 1, "middle" → 2, "bottom" → 3
  - 4+ options: Looks for "Option 1", "Option 2", etc.
- Validates choice number doesn't exceed available choices

### Step 8: Return Result
- Returns: `(choice_number, success, choice_locations)`
- `choice_number`: The recommended choice (1, 2, 3, etc.)
- `success`: Whether the analysis was successful
- `choice_locations`: List of detected choice locations for clicking

## Supporting Functions

### `count_event_choices()`
- Uses template matching with `event_choice_1.png`
- Searches in the event choice region
- Filters by brightness to avoid false positives
- Returns count and locations of bright choices

### `search_events_exact(event_name)`
- Searches all event databases for exact name match
- Returns event data with options from all matching sources

### `search_events_fuzzy(event_name)`
- Performs fuzzy matching with priority:
  1. Events starting with OCR text
  2. Events where OCR text is a complete word
  3. Substring matches (if >= 5 chars)
- Returns best matches in priority order

### `analyze_event_options(options, priorities)`
- Analyzes each option against good/bad choice lists
- Returns recommendation with reasoning

### `click_event_choice(choice_number, choice_locations)`
- Clicks on the specified choice using pre-found locations
- Falls back to searching if locations not provided

## Error Handling

- **OCR Failure**: Saves debug image, optionally stops bot (configurable)
- **No Choices Found**: Returns early with fallback
- **Event Not in Database**: Defaults to first choice
- **Invalid Choice Number**: Falls back to first choice
- **General Errors**: Logs error and falls back to top choice

## Configuration

- `stop_on_event_detection_failure` in `config.json`: Whether to stop bot on OCR failure
- `event_priority.json`: Defines good and bad choices for analysis

## Test File

The test file `test_event_handling_workflow.py` provides:
- Multiple screenshot captures on event choices screen
- Step-by-step workflow testing
- Screenshot overlays showing detected regions and choices
- Detailed statistics and analysis
- Performance metrics

Run the test:
```bash
python -m unity_test.test_event_handling_workflow
```

Or with custom iterations:
```bash
python -m unity_test.test_event_handling_workflow --iterations 20
```

