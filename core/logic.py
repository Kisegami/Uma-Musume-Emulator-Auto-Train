import json

with open("config.json", "r", encoding="utf-8") as file:
  config = json.load(file)

PRIORITY_STAT = config["priority_stat"]
MAX_FAILURE = config["maximum_failure"]
STAT_CAPS = config["stat_caps"]
DO_RACE_WHEN_BAD_TRAINING = config.get("do_race_when_bad_training", True)
MIN_CONFIDENCE = 0.5  # Minimum confidence threshold for training decisions (currently used for retry logic)

# Get priority stat from config
def get_stat_priority(stat_key: str) -> int:
  return PRIORITY_STAT.index(stat_key) if stat_key in PRIORITY_STAT else 999


# Check if all training options have failure rates above maximum
def all_training_unsafe(results, maximum_failure=None):
  if maximum_failure is None:
    maximum_failure = MAX_FAILURE
  for stat, data in results.items():
    if int(data["failure"]) <= maximum_failure:
      return False
  return True

def is_at_stat_cap_limits(current_stats):
  for stat, stat_value in current_stats.items():
    stat_cap = STAT_CAPS.get(stat, 1200)
    if stat_value < stat_cap:
      return False
  
  return True

def filter_by_stat_caps(results, current_stats):
  filtered = {}
  for stat, data in results.items():
    current_stat_value = current_stats.get(stat, 0)
    stat_cap = STAT_CAPS.get(stat, 1200)
    if current_stat_value < stat_cap:
      filtered[stat] = data
    else:
      print(f"[INFO] {stat.upper()} training filtered out: current {current_stat_value} >= cap {stat_cap}")
  
  return filtered
