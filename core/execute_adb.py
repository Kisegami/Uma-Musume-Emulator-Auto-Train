import time

from core.logic import all_training_unsafe, is_at_stat_cap_limits
from core.screens.career_adb import do_infirmary, do_recreation, do_rest, needs_infirmary
from core.screens.claw_machine_adb import do_claw_machine
from core.screens.race_adb import RETRY_RACE, check_strategy_before_race, do_race, is_g1_racing_available, is_racing_available, race_day
from core.screens.training_adb import check_training, do_train, go_to_training
from utils.adb_recognizer import match_template
from utils.adb_input import tap
from utils.adb_screenshot import take_screenshot
from utils.constants_phone import (
    MOOD_LIST
)
from core.config import Config
from core.templates_adb import BACK_BUTTON_TEMPLATE, CANCEL_BUTTON_TEMPLATE, CLAW_BUTTON_TEMPLATE, EVENT_CHOICE_1_TEMPLATE, INSPIRATION_BUTTON_TEMPLATE, NEXT_2_BUTTON_TEMPLATE, NEXT_BUTTON_TEMPLATE, OK_BUTTON_TEMPLATE, RACE_BUTTON_TEMPLATE, RACE_URA_TEMPLATE, TAZUNA_HINT_TEMPLATE, TRY_AGAIN_BUTTON_TEMPLATE, VIEW_RESULTS_BUTTON_TEMPLATE

# Import ADB state and logic modules
from core.state_adb import check_current_stats, check_turn, check_mood, check_current_year, check_criteria, check_skill_points_cap, check_goal_name_with_g1_requirement, check_energy_bar, choose_best_training, is_pre_debut_year

# Import event handling functions
from core.event_handling import click, debug_print, handle_event_choice, click_event_choice

config = Config.load()

def career_lobby():
    """Main career lobby loop"""
    # Load configuration
    MINIMUM_MOOD = config["minimum_mood"]
    PRIORITIZE_G1_RACE = config["prioritize_g1_race"]

    # Global state
    bought_skills = {}

    # Program start
    while True:
        debug_print("\n[DEBUG] ===== Starting new loop iteration =====")
        
        # Batch UI check - take one screenshot and check multiple elements
        debug_print("[DEBUG] Performing batch UI element check...")
        screenshot = take_screenshot()
        
        # Check claw machine first (highest priority)
        debug_print("[DEBUG] Checking for claw machine...")
        if (match := img_matches(screenshot, CLAW_BUTTON_TEMPLATE, confidence=0.8)):
            do_claw_machine(screenshot)
            continue
        
        # Check OK button
        debug_print("[DEBUG] Checking for OK button...")
        if (match := img_matches(screenshot, OK_BUTTON_TEMPLATE, confidence=0.7)):
            print("[INFO] Selecting OK.")
            tap_button(match)

        # Check view results button
        debug_print("[DEBUG] Checking for view results button...")
        if (match := img_matches(screenshot, VIEW_RESULTS_BUTTON_TEMPLATE, confidence=0.6)):
            # Check and ensure strategy matches config before race
            if not check_strategy_before_race():
                debug_print("[DEBUG] Failed to ensure correct strategy, proceeding anyway...")
            print("[INFO] Selecting view results.")
            tap_button(match)
            time.sleep(0.5)
            for i in range(3):
                debug_print(f"[DEBUG] Clicking view results {i + 1}/3")
                tap_button(match)
                time.sleep(0.01)
            debug_print("[DEBUG] Race preparation complete")

        # Check try again button
        debug_print("[DEBUG] Checking for try again button...")
        if (match := img_matches(screenshot, TRY_AGAIN_BUTTON_TEMPLATE, confidence=0.6)):
            if not RETRY_RACE:
                print("[INFO] retry_race is disabled. Stopping automation.")
                raise SystemExit(0)
            print("[INFO] Selecting try again.")
            tap_button(match)
        
        # Check for events
        debug_print("[DEBUG] Checking for events...")
        try:
            event_choice_region = (6, 450, 126, 1776)
            event_matches = match_template(screenshot, EVENT_CHOICE_1_TEMPLATE, confidence=0.8, region=event_choice_region)
            
            if event_matches:
                print("[INFO] Event detected, analyzing choices...")
                choice_number, success, choice_locations = handle_event_choice(screenshot)
                if success:
                    click_success = click_event_choice(choice_number, choice_locations)
                    if click_success:
                        print(f"[INFO] Successfully selected choice {choice_number}")
                        time.sleep(0.5)
                        continue
                    else:
                        print("[WARNING] Failed to click event choice, falling back to top choice")
                        # Fallback using existing match
                        x, y, w, h = event_matches[0]
                        center = (x + w//2, y + h//2)
                        tap(center[0], center[1])
                        continue
                else:
                    # If no choice locations were returned, skip clicking and continue loop
                    if not choice_locations:
                        debug_print("[DEBUG] Skipping event click due to no visible choices after stabilization")
                        continue
                    print("[WARNING] Event analysis failed, falling back to top choice")
                    # Fallback using existing match
                    x, y, w, h = event_matches[0]
                    center = (x + w//2, y + h//2)
                    tap(center[0], center[1])
                    continue
            else:
                debug_print("[DEBUG] No events found")
        except Exception as e:
            print(f"[ERROR] Event handling error: {e}")

        # Check inspiration button
        debug_print("[DEBUG] Checking for inspiration...")
        if (match := img_matches(screenshot, INSPIRATION_BUTTON_TEMPLATE, confidence=0.5)):
            print("[INFO] Inspiration found.")
            tap_button(match)

        # Check next button
        debug_print("[DEBUG] Checking for next button...")
        if (match := img_matches(screenshot, NEXT_BUTTON_TEMPLATE, confidence=0.8)):
            print("[INFO] Selecting next.")
            tap_button(match)

        # Check next button 2
        debug_print("[DEBUG] Checking for next button 2...")
        if (match := img_matches(screenshot, NEXT_2_BUTTON_TEMPLATE, confidence=0.9)):
            print("[INFO] Selecting next 2.")
            tap_button(match)

        # Check cancel button
        debug_print("[DEBUG] Checking for cancel button...")
        if (match := img_matches(screenshot, CANCEL_BUTTON_TEMPLATE, confidence=0.6)):
            print("[INFO] Selecting cancel.")
            tap_button(match)

        # Check if current menu is in career lobby
        debug_print("[DEBUG] Checking if in career lobby...")
        if not img_matches(screenshot, TAZUNA_HINT_TEMPLATE, confidence=0.8):
            print("[INFO] Should be in career lobby.")
            continue

        debug_print("[DEBUG] Confirmed in career lobby")

        # Check if there is debuff status
        debug_print("[DEBUG] Checking for debuff status...")
        if needs_infirmary(screenshot):
            do_infirmary(screenshot)
            continue

        # Get current state
        debug_print("[DEBUG] Getting current game state...")
        mood = check_mood(screenshot)
        mood_index = MOOD_LIST.index(mood)
        minimum_mood = MOOD_LIST.index(MINIMUM_MOOD)
        turn = check_turn(screenshot)
        year = check_current_year(screenshot)
        goal_data = check_goal_name_with_g1_requirement(screenshot)
        criteria_text = check_criteria(screenshot)
        
        print("\n=======================================================================================\n")
        print(f"Year: {year}")
        print(f"Mood: {mood}")
        print(f"Turn: {turn}")
        print(f"Goal Name: {goal_data['text']}")
        print(f"Status: {criteria_text}")
        print(f"G1 Race Requirement: {goal_data['requires_g1_races']}")
        debug_print(f"[DEBUG] Mood index: {mood_index}, Minimum mood index: {minimum_mood}")
        
        # Check energy bar before proceeding with training decisions
        debug_print("[DEBUG] Checking energy bar...")
        energy_percentage = check_energy_bar(screenshot)
        min_energy = config.get("min_energy", 30)
        
        print(f"Energy: {energy_percentage:.1f}% (Minimum: {min_energy}%)")
        
        # Check if goals criteria are NOT met AND it is not Pre-Debut AND turn is less than 10
        # Prioritize racing when criteria are not met to help achieve goals
        debug_print("[DEBUG] Checking goal criteria...")
        goal_analysis = check_goal_criteria({"text": criteria_text, "requires_g1_races": goal_data['requires_g1_races']}, year, turn)
        
        if goal_analysis["should_prioritize_racing"]:
            race_found = do_race(year, prioritize_g1=goal_analysis["should_prioritize_g1_races"])
            if goal_analysis["should_prioritize_g1_races"]:
                print(f"Decision: Criteria not met - Prioritizing G1 races to meet goals")
                if race_found:
                    print("Race Result: Found G1 Race")
                    continue
                else:
                    print("Race Result: No G1 Race Found")
                    # If there is no G1 race found, go back and do training instead
                    click(BACK_BUTTON_TEMPLATE, text="[INFO] G1 race not found. Proceeding to training.")
                    time.sleep(0.5)
            else:
                print(f"Decision: Criteria not met - Prioritizing normal races to meet goals")
                if race_found:
                    print("Race Result: Found Race")
                    continue
                else:
                    print("Race Result: No Race Found")
                    # If there is no race found, go back and do training instead
                    click(BACK_BUTTON_TEMPLATE, text="[INFO] Race not found. Proceeding to training.")
                    time.sleep(0.5)
        else:
            print("Decision: Criteria met or conditions not suitable for racing")
            debug_print(f"[DEBUG] Racing not prioritized - Criteria met: {goal_analysis['criteria_met']}, Pre-debut: {goal_analysis['is_pre_debut']}, Turn < 10: {goal_analysis['turn_less_than_10']}")
        
        print("")

        # URA SCENARIO
        debug_print("[DEBUG] Checking for URA scenario...")
        if year == "Finale Season" and turn == "Race Day":
            print("[INFO] URA Finale")
            
            # Check skill points cap before URA race day (if enabled)
            enable_skill_check = config.get("enable_skill_point_check", True)
            
            if enable_skill_check:
                print("[INFO] URA Finale Race Day - Checking skill points cap...")
                check_skill_points_cap(screenshot, bought_skills)
            
            # URA race logic would go here
            debug_print("[DEBUG] Starting URA race...")
            if click(RACE_URA_TEMPLATE, minSearch=10):
                time.sleep(0.5)
                # Click race button 2 times after entering race menu
                for i in range(2):
                    if click(RACE_BUTTON_TEMPLATE, minSearch=2):
                        debug_print(f"[DEBUG] Successfully clicked race button {i+1}/2")
                        time.sleep(1)
                    else:
                        debug_print(f"[DEBUG] Race button not found on attempt {i+1}/2")
            continue
        else:
            debug_print("[DEBUG] Not URA scenario")

        # If calendar is race day, do race
        debug_print("[DEBUG] Checking for race day...")
        if turn == "Race Day" and year != "Finale Season":
            print("[INFO] Race Day.")
            race_day(screenshot, bought_skills)
            continue
        else:
            debug_print("[DEBUG] Not race day")

        # Mood check
        debug_print("[DEBUG] Checking mood...")
        if mood_index < minimum_mood:
            # Check if energy is too high (>90%) before doing recreation
            if energy_percentage > 90:
                debug_print(f"[DEBUG] Mood too low ({mood_index} < {minimum_mood}) but energy too high ({energy_percentage:.1f}% > 90%), skipping recreation")
                print(f"[INFO] Mood is low but energy is too high ({energy_percentage:.1f}% > 90%), skipping recreation")
            else:
                debug_print(f"[DEBUG] Mood too low ({mood_index} < {minimum_mood}), doing recreation")
                print("[INFO] Mood is low, trying recreation to increase mood")
                do_recreation(screenshot)
                continue
        else:
            debug_print(f"[DEBUG] Mood is good ({mood_index} >= {minimum_mood})")

        # If Prioritize G1 Race is true, check G1 race every turn
        debug_print(f"[DEBUG] Checking G1 race priority: {PRIORITIZE_G1_RACE}")
        if PRIORITIZE_G1_RACE and is_racing_available(year) and is_g1_racing_available(year):
            print("G1 Race Check: Looking for G1 race...")
            g1_race_found = do_race(year, PRIORITIZE_G1_RACE)
            if g1_race_found:
                print("G1 Race Result: Found G1 Race")
                continue
            else:
                print("G1 Race Result: No G1 Race Found")
                # If there is no G1 race, go back and do training instead
                click(BACK_BUTTON_TEMPLATE, text="[INFO] G1 race not found. Proceeding to training.")
                time.sleep(0.5)
        else:
            debug_print("[DEBUG] G1 race priority disabled or conditions not met")
            debug_print(f"[DEBUG] Is racing available: {is_racing_available(year)}")
            debug_print(f"[DEBUG] Is G1 racing available: {is_g1_racing_available(year)}")
        
        # Check training button
        debug_print("[DEBUG] Going to training...")
        # Check energy before proceeding with training
        if energy_percentage < min_energy:
            print(f"[INFO] Energy too low ({energy_percentage:.1f}% < {min_energy}%), skipping training and going to rest")
            do_rest(screenshot)
            continue
        
        best_training = None
        current_stats = check_current_stats(screenshot)
        results_training = None
        if not is_at_stat_cap_limits(current_stats):
            if not go_to_training():
                print("[INFO] Training button is not found.")
                continue

            # Last, do training
            debug_print("[DEBUG] Analyzing training options...")
            time.sleep(0.5)
            results_training = check_training()
            
            debug_print("[DEBUG] Deciding best training action using scoring algorithm...")
            best_training = choose_best_training(screenshot, results_training, config)  
        
        if best_training:
            debug_print(f"[DEBUG] Scoring algorithm selected: {best_training.upper()} training")
            print(f"[INFO] Selected {best_training.upper()} training based on scoring algorithm")

            do_train(best_training)
        else:
            debug_print("[DEBUG] No suitable training found based on scoring criteria")
            print("[INFO] No suitable training found based on scoring criteria.")

            if not is_at_stat_cap_limits(current_stats):
                debug_print("[DEBUG] Going back from training screen...")
                click(BACK_BUTTON_TEMPLATE)
            
            # Check if we should prioritize racing when no good training is available
            do_race_when_bad_training = config.get("do_race_when_bad_training", True)
            
            if do_race_when_bad_training:
                # Check if all training options have failure rates above maximum
                if results_training:
                    max_failure = config.get('maximum_failure', 15)
                    debug_print(f"[DEBUG] Checking if all training options have failure rate > {max_failure}%")
                    debug_print(f"[DEBUG] Training results: {[(k, v['failure']) for k, v in results_training.items()]}")

                if results_training and all_training_unsafe(results_training, max_failure):
                    debug_print(f"[DEBUG] All training options have failure rate > {max_failure}%")
                    print(f"[INFO] All training options have failure rate > {max_failure}%. Skipping race and choosing to rest.")
                    do_rest(screenshot)
                else:
                    # Check if racing is available (no races in July/August)
                    if not is_racing_available(year):
                        debug_print("[DEBUG] Racing not available (summer break)")
                        print("[INFO] July/August detected. No races available during summer break. Choosing to rest.")
                        do_rest(screenshot)
                    else:
                        print("[INFO] Prioritizing race due to insufficient training scores.")
                        print("Training Race Check: Looking for race due to insufficient training scores...")

                        if not is_g1_racing_available(year):
                            do_rest(screenshot)
                            continue

                        if do_race(year, PRIORITIZE_G1_RACE):
                            print("Training Race Result: Found Race")
                            continue
                        else:
                            print("Training Race Result: No Race Found")
                            # If no race found, go back and rest
                            click(BACK_BUTTON_TEMPLATE, text="[INFO] Race not found. Proceeding to rest.")
                            time.sleep(0.5)
                            do_rest(screenshot)
                            continue
            else:
                print("[INFO] Race prioritization disabled. Choosing to rest.")
                do_rest(screenshot)
        
        debug_print("[DEBUG] Waiting before next iteration...")
        time.sleep(0.1)
        
def img_matches(screenshot, template, confidence):
    matches = match_template(screenshot, template, confidence=confidence)
    return matches[0] if matches else None
        
def tap_button(match):
    x, y, w, h = match
    center = (x + w//2, y + h//2)
    debug_print(f"[DEBUG] Clicking next_btn.png at position {center}")
    tap(center[0], center[1])

def check_goal_criteria(criteria_data, year, turn):
    """
    Check if goal criteria are met and determine if racing should be prioritized.
    
    Args:
        criteria_data (dict): The criteria data from OCR with text and G1 race requirements
        year (str): Current year text
        turn (str/int): Current turn number or text
    
    Returns:
        dict: Dictionary containing criteria analysis and decision
    """
    # Extract criteria text and G1 race requirements
    criteria_text = criteria_data.get("text", "")
    requires_g1_races = criteria_data.get("requires_g1_races", False)
    
    # Check if goals criteria are met
    criteria_met = (criteria_text.split(" ")[0] == "criteria" or 
                    "criteria met" in criteria_text.lower() or 
                    "goal achieved" in criteria_text.lower())
    
    # Check if it's pre-debut year
    is_pre_debut = is_pre_debut_year(year)
    
    # Check if turn is a number before comparing
    turn_is_number = isinstance(turn, int) or (isinstance(turn, str) and turn.isdigit())
    turn_less_than_10 = turn < 10 if turn_is_number else False
    
    # Determine if racing should be prioritized (when criteria not met, not pre-debut, turn < 10)
    should_prioritize_racing = not criteria_met and not is_pre_debut and turn_less_than_10
    
    # Determine if G1 races should be prioritized (when racing should be prioritized AND G1 races are required)
    should_prioritize_g1_races = should_prioritize_racing and requires_g1_races
    
    debug_print(f"[DEBUG] Year: '{year}', Criteria met: {criteria_met}, Pre-debut: {is_pre_debut}, Turn < 10: {turn_less_than_10}")
    debug_print(f"[DEBUG] G1 races required: {requires_g1_races}, Should prioritize G1: {should_prioritize_g1_races}")
    
    return {
        "criteria_met": criteria_met,
        "is_pre_debut": is_pre_debut,
        "turn_less_than_10": turn_less_than_10,
        "should_prioritize_racing": should_prioritize_racing,
        "requires_g1_races": requires_g1_races,
        "should_prioritize_g1_races": should_prioritize_g1_races
    } 