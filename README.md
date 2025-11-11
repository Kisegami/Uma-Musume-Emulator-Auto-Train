# Umamusume Auto Training Bot (Revamped)


An automated training bot for Umamusume that works with **Android emulators** using ADB (Android Debug Bridge).

**🎮 Platform:** Android Emulator (BlueStacks, LDPlayer, etc.)  
**📱 Resolution:** 1080x1920 (Portrait)  
**🔧 Technology:** ADB commands for screen capture and input

This ADB version provides the same intelligent training logic as the PC version but runs on Android emulators, offering better stability and easier setup.

## Features

### 🤖 ADB/Android Specific Features
- **ADB Integration**: Uses Android Debug Bridge for reliable screen capture and input
- **Emulator Optimized**: Designed specifically for Android emulators (BlueStacks, LDPlayer, etc.)
- **Portrait Layout**: Optimized for 1080x1920 portrait mode gameplay
- **Stable Performance**: More reliable than screen-based automation methods

### 🎯 Training & Racing Intelligence
- Automatically trains Uma with stat prioritization
- Keeps racing until fan count meets the goal, and always picks races with matching aptitude
- Checks mood and handles debuffs automatically
- Rest and recreation management
- Prioritizes G1 races if available for fan farming
- **Auto Skill Purchase**: Automatically purchases skills when skill points exceed cap
- Stat caps to prevent overtraining specific stats
- **Intelligent Event Choice Selection**: Automatically analyzes event options and selects the best choice based on configured priorities
- **Automated Claw Machine**: Automatically detects and handles claw machine mini-games with randomized timing (99% Failure rate bruh)
- **Energy Bar Detection**: Automatically monitors energy levels (adaptive even with max energy increasing events) and skips training when energy is too low
- **Advanced Training Scoring**: Uses support card bond levels, hints, and failure rates to calculate optimal training choices
- **Smart Race Strategy Management**: Automatically checks and adjusts race strategy before races
- **Automatic Race Retry**: Auto use clock to retry the race 

## Getting Started

### Requirements

#### Software Requirements
- [Python 3.10+](https://www.python.org/downloads/)
- [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) (for text recognition)
- [ADB (Android Debug Bridge)](https://developer.android.com/studio/command-line/adb) (for Android communication)

#### Android Emulator Requirements
- **Supported Emulators**: The test was done on Mumu Emulator 12, but you might be able to use others
- **Emulator Resolution**: 1080x1920 (Portrait mode)
- **ADB Debugging**: Must be enabled in emulator settings

### Setup

#### 1. Clone Repository

```bash
git clone https://github.com/isaiah-solo/Uma-Musume-Emulator-Auto-Train.git
cd Uma-Musume-Emulator-Auto-Train
```

#### 2. Install Python Dependencies

```bash
pip install -r requirements.txt
```

#### 3. Install Tesseract OCR

**Windows:**
1. Download and install from [UB-Mannheim's Tesseract installer](https://github.com/UB-Mannheim/tesseract/wiki)
2. Add Tesseract to your system PATH

#### 4. Setup ADB

1. Download [platform-tools](https://developer.android.com/studio/releases/platform-tools)
2. Extract and add to your system PATH

#### 5. Configure Android Emulator

1. **Install an Android emulator** (Mumu Emulator 12 recommended)
2. **Set resolution to 1080x1920** (portrait mode)
3. **Enable ADB debugging** in emulator settings
4. **Install Umamusume** in the emulator
5. **Test ADB connection**: `adb devices` (should show your emulator)


#### 6. Configuration Files Setup

**Important:** The bot uses configuration files that you can customize. To avoid conflicts when updating:

**Option A: Automatic Setup (Recommended)**
```bash
python setup_config.py
```

**Option B: Manual Setup**
```bash
copy config.example.json config.json
copy event_priority.example.json event_priority.json
copy training_score.example.json training_score.json
```

2. **Customize your copies** - these will be preserved when you pull updates
3. **Never commit your customized config files** - they're already in `.gitignore`

**Available Configuration Files:**
- `config.json` - Main bot settings (training priorities, ADB settings, etc.)
- `event_priority.json` - Event choice preferences (good vs bad choices)
- `training_score.json` - Training scoring rules and weights

#### 7. Configure ADB Settings (Interactive Setup)

Edit the `adb_config` section in your `config.json ` using the address you got from your Emulator:
```json
{
  "adb_config": {
    "device_address": "127.0.0.1:7555",
    "adb_path": "adb",
    "screenshot_timeout": 5,
    "input_delay": 0.5,
    "connection_timeout": 10
  }
}
```

#### 8. Configure local host ui

In a new  *Command Prompt* run
```cmd
cd "C:\Users\Path\Uma-Musume-Emulator-Auto-Train"
py -m pip install fastapi uvicorn "pydantic<3" pillow numpy
```
After its installed run the following command 

```cmd
py -m uvicorn web_config:app --host 127.0.0.1 --port 8000
```
Then go to "http://127.0.0.1:8000" on your browser, you can make change real time with the inputs and confirm by clicking "Save"


### BEFORE YOU START

Make sure these conditions are met:

#### 🖥️ Emulator Setup
- **Resolution**: Must be 1080x1920 (portrait mode)
- **ADB Connection**: `adb devices` shows your emulator
- **Game Installation**: Umamusume installed and working in emulator

#### 🎮 Game Setup  
- Your Uma must have already won the trophy for each race (the bot will skip the race)
- Turn off all confirmation pop-ups in game settings
- The game must be in the career lobby screen (the one with the Tazuna hint icon)

### Configuration

You can edit your configuration in `config.json`

```json
{
  "priority_stat": [
    "spd",
    "sta",
    "wit",
    "pwr",
    "guts"
  ],

  "minimum_mood": "GREAT",
  "maximum_failure": 15,
  
  "strategy": "PACE",
  "prioritize_g1_race": false,
  "retry_race": true,

  "skill_point_cap": 400,
  "skill_purchase": "auto",
  "skill_file": "skills_example.json",
  "enable_skill_point_check": true,

  "min_energy": 30,
  "min_score": 1.0,
  "min_wit_score": 1.0,
  "do_race_when_bad_training": true,

  "stat_caps": {
    "spd": 1100,
    "sta": 1100,
    "pwr": 600,
    "guts": 600,
    "wit": 600
  },

  "adb_config": {
    "device_address": "127.0.0.1:7555",
    "adb_path": "adb",
    "screenshot_timeout": 5,
    "input_delay": 0.5,
    "connection_timeout": 10
  },

  "debug_mode": false
}
```

#### Configuration Options

`priority_stat` (array of strings)
- Determines the training stat priority. The bot will focus on these stats in the given order of importance.
- Accepted values: `"spd"`, `"sta"`, `"pwr"`, `"guts"`, `"wit"`

`minimum_mood` (string)
- The lowest acceptable mood the bot will tolerate when deciding to train.
- Accepted values (case-sensitive): `"GREAT"`, `"GOOD"`, `"NORMAL"`, `"BAD"`, `"AWFUL"`
- **Example**: If set to `"NORMAL"`, the bot will train as long as the mood is `"NORMAL"` or better. If the mood drops below that, it'll go for recreation instead.

`maximum_failure` (integer)
- Sets the maximum acceptable failure chance (in percent) before skipping a training option.
- Example: 10 means the bot will avoid training with more than 10% failure risk.

`prioritize_g1_race` (boolean)
- If `true`, the bot will prioritize G1 races except during July and August (summer).
- Useful for fan farming.
- **Warning**: It will do G1 race no matter what

`retry_race` (boolean)
- Controls whether the bot automatically retries failed races,. **MAKE SURE YOUR HAVE MORE THAN 3 CLOCKS**
- **`true`**: Automatically retries failed races (recommended)
- **`false`**: Stops automation when a race fails
- **Default**: `true`
- **Note**: This feature helps maintain automation continuity during race failures

`strategy` (string) 
- Sets the preferred race strategy for the bot to use.
- **Accepted values**: `"FRONT"`, `"PACE"`, `"LATE"`, `"END"`
- **Default**: `"PACE"`
- **Note**: The bot automatically checks and adjusts race strategy before each race

`skill_point_cap` (integer) - 
- Maximum skill points before the bot automatically purchases skills or prompts you to spend them.
- The bot will pause on race days and either auto-purchase skills or show a prompt if skill points exceed this cap.

`skill_purchase` (string)
- Controls how skill points are handled when they exceed the cap.
- **`"auto"`**: Automatically enters skill shop, purchases optimal skills, and returns to lobby
- **`"manual"`**: Shows a prompt for manual skill purchasing
- **Default**: `"auto"`

`skill_file` (string)
- Specifies which skill configuration file to use for auto skill purchase.
- **Default**: `"skills.json"`
- **Example**: `"skills_oguri.json"` for Oguri Cap build
- **Multiple templates**: Create different skill files for different builds and switch between them

`enable_skill_point_check` (boolean) - 
- Enables/disables the skill point cap checking feature.

`do_race_when_bad_training` (boolean) - 
- If `true`, the bot will prioritize racing when no training meets the requirements (insufficient support cards, high failure rates, etc.).
- If `false`, the bot will skip support card requirements and train regardless of `min_support` setting (as long as failure rates are acceptable).
- Default: `true`

`min_energy` (integer)
- Minimum energy percentage required before attempting training.
- If energy drops below this threshold, the bot will skip training and go to rest instead.
- **Example**: Setting to 30 means training will only occur when energy is 30% or higher.
- **Default**: 30
- **Range**: 0-100 (percentage)

`min_score` (float)
- Minimum training score required for a training option to be considered.
- Training options with scores below this threshold will be skipped.
- **Default**: 1.0
- **Note**: Used in the advanced training scoring algorithm

`min_wit_score` (float)
- Minimum training score specifically required for WIT training.
- WIT training options with scores below this threshold will be skipped.
- **Default**: 1.0
- **Note**: Separate threshold for WIT training due to its unique requirements

`stat_caps` (object) - 
- Maximum values for each stat. The bot will skip training stats that have reached their cap.
- Prevents overtraining and allows focusing on other stats.

`debug_mode` (boolean) - 
- Controls whether debug messages and debug images are saved.
- Set to `false` for normal operation, `true` for troubleshooting.
- When `false`, significantly improves performance by reducing file I/O.

`adb_config` (object) - ADB-specific configuration:
- `device_address` (string) - Target device/emulator address (e.g., "127.0.0.1:7555" for emulator port 7555)
- `adb_path` (string) - Path to ADB executable (usually just "adb" if in PATH)
- `screenshot_timeout` (integer) - Maximum seconds to wait for screenshots (default: 5)
- `input_delay` (float) - Delay between input commands in seconds (default: 0.5)
- `connection_timeout` (integer) - Maximum seconds to wait for ADB connection (default: 10)

Make sure the values match exactly as expected, typos might cause errors.


### **Training Score Configuration**

The bot uses a configurable scoring system defined in `training_score.json`:

```json
{
  "scoring_rules": {
    "rainbow_support": {
      "description": "Same type support card with bond level >= 4",
      "points": 1.0
    },
    "not_rainbow_support_low": {
      "description": "Different type support with bond level < 4",
      "points": 0.7
    },
    "not_rainbow_support_high": {
      "description": "Diffrent type support with bond level >= 4 (no need to get more bond)",
      "points": 0.0
    },
    "hint": {
      "description": "Hint icon present",
      "points": 0.3
    }
  }
}
```
### Training Logic

The bot uses an advanced training logic system with intelligent scoring:

#### **Training Scoring Algorithm**
- **Support Card Analysis**: Evaluates support cards by type and bond level
- **Rainbow Training Detection**: Identifies and prioritizes rainbow training opportunities
- **Hint Bonus System**: Adds score bonuses for training hints
- **Failure Rate Integration**: Considers failure rates in final training decisions
- **Stat Cap Filtering**: Automatically excludes stats that have reached their caps

#### **Scoring Formula**
```
Training Score = Support Card Score + Hint Bonus
```

#### **Decision Making Process**
1. **Stat Cap Filtering**: Remove stats that have reached their configured caps
2. **Failure Rate Filtering**: Exclude options above `maximum_failure` threshold
3. **Score Threshold Filtering**: Apply `min_score` and `min_wit_score` requirements
4. **Scoring Evaluation**: Calculate scores for all eligible training options
5. **Tie-Breaking**: Use priority order from `priority_stat` configuration
6. **Final Selection**: Choose training with highest score


### **Skill Configuration**

The bot now includes a comprehensive skill management system controlled by a json file:

```json
{
    "skill_priority": [
        "Professor of Curvature",
        "Swinging Maestro",
        "Rushing Gale!",
        "Unrestrained",
        "Killer Tunes"
    ],
    "gold_skill_upgrades": {
        "Professor of Curvature": "Corner Adept",
        "Swinging Maestro": "Corner Recovery",
        "Rushing Gale!": "Straightaway Acceleration",
        "Unrestrained": "Final Push",
        "Killer Tunes": "Up-Tempo"
    }
}
```

#### Skill Priority Configuration

`skill_priority` (array of strings)
- **Order matters**: Skills listed first have higher priority
- **Gold skills or normal skills only**: List the gold skill or normal skill (the one with no upgrade) names (e.g., "Professor of Curvature") unless you only want to buy the base skill.

`gold_skill_upgrades` (object)
- Maps base skill names to their gold upgrade versions
- **Key**: Gold skill name (must match exactly with `skill_priority`)
- **Value**: Base skill name 
- The bot will purchase base skill if gold skill is not available

**Example**:`** "Professor of Curvature": "Corner Adept"`

### **Multiple Skill File Templates**

The bot now supports multiple skill configuration files, allowing you to create different skill builds and switch between them easily:

#### Creating Skill Templates

1. **Create different skill files** with descriptive names (Example: `skills_Oguri.json` )

2. **Switch between templates** by changing the `skill_file` setting in `config.json`:
   ```json
   {
     "skill_file": "skills_Oguri.json"
   }
   ```

#### Benefits of Multiple Templates

- **Build Variety**: Create different skill builds for different Uma
- **Easy Switching**: Change builds by editing one line in `config.json`
- **Template Sharing**: Share skill builds with other players
- **Testing**: Try different skill priorities without losing your main configuration
### Event Choice Configuration

The bot now includes intelligent event choice selection. You can configure which choices are considered "good" or "bad" in `event_priority.json`:

```json
{
  "Good_choices": [
    "Charming",
    "Fast Learner", 
    "Hot Topic",
    "Practice Perfect",
    "Energy +",
    "hint +",
    "Speed +",
    "Stamina +",
    "Yayoi Akikawa bond +",
    "Power +",
    "Wisdom +",
    "Skill points +",
    "Mood +",
    "bond +",
    "stat +",
    "stats +",
    "Guts +",
    "Japanese Oaks"
  ],
  "Bad_choices": [
    "Practice Poor",
    "Slacker",
    "Slow Metabolism", 
    "Mood -",
    "Gatekept"
  ]
}
```

#### Customizing Event Priorities

If you want to customize the event priorities beyond the default configuration, you can reference `all_unique_event_outcomes.json` which contains all possible event outcomes in the game until 08/2025. This file serves as a comprehensive reference for:

- **All possible stat gains** (Speed +10, Stamina +15, etc.)
- **All skill hints** (various skill names with hint bonuses)
- **All support card bond changes** (character names with bond +5/-5)
- **All conditions** (Charming, Hot Topic, Practice Perfect, etc.)
- **All energy changes** (Energy +10, Energy -15, etc.)
- **All mood changes** (Mood +1, Mood -1, etc.)

Use this file to discover new event outcomes you might want to add to your `Good_choices` or `Bad_choices` arrays in `event_priority.json`. For example, if you find a specific skill hint or support card bond change you want to prioritize, you can copy the exact text from `all_unique_event_outcomes.json` and add it to your configuration.

#### Event Choice Selection Logic

The bot automatically selects the best event choice based on your configured priorities:

1. **Priority Analysis**: Chooses options with the highest priority good choices first
2. **Tie-Breaking**: When multiple options have the same good choice:
   - Prefers options with fewer bad choices
   - If still tied, prefers options with more good choices
   - If still tied, defaults to the top choice
3. **Fallback**: For unknown events or analysis failures, defaults to the first choice

#### Event Priority Configuration

`Good_choices` (array of strings)
- List of positive effects that should be prioritized
- The bot will prefer choices containing these terms
- Order matters: earlier items have higher priority

`Bad_choices` (array of strings)
- List of negative effects to avoid
- The bot will prefer choices with fewer of these effects
- Used for tie-breaking when multiple options have the same good choices

### Start
#### 1. Start the Bot (Make sure you done the config)
```bash
python main_adb.py
```

#### 2. Stop the Bot
- Press `Ctrl + C` in your terminal to stop the bot
- Or close the terminal window

### Known Issues

#### 🤖 ADB/Android Specific
- Requires stable ADB connection (emulator must stay running)
- May need to restart if emulator restarts or ADB connection is lost
- Performance depends on emulator performance and host system resources

#### 🎮 Game Logic
- Some Uma that has special event/target goals (like Restricted Train Goldship). So please avoid using Goldship for training right now to keep your 12 billion yen safe.
- Tesseract OCR might misread failure chance (e.g., reads 33% as 3%) and proceeds with training anyway
- If you bring a friend support card (like Tazuna/Aoi Kiryuin) and do recreation, the bot can't decide whether to date with the friend support card or the Uma
- The bot will skip "3 consecutive races warning" prompt for now
