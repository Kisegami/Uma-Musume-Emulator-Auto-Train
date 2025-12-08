#!/usr/bin/env python3
"""
Configuration File Checker

This module handles checking for required configuration files and creating them
from example files if they don't exist.
"""

import os
import json
import shutil
from pathlib import Path
from copy import deepcopy


class ConfigChecker:
    """Handles configuration file checking and creation"""
    
    def __init__(self, root_dir="."):
        self.root_dir = Path(root_dir)
        self.required_configs = {
            "config.json": "config.example.json",
            "event_priority.json": "event_priority.example.json", 
            "training_score.json": "training_score.example.json",
            "training_score_unity.json": "training_score_unity.example.json",
            "custom_races.json": "custom_races.example.json",
            "skills.json": "skills.example.json"
        }
    
    def deep_merge(self, existing_dict, example_dict):
        """Deep merge example_dict into existing_dict, only adding missing keys"""
        merged = deepcopy(existing_dict)
        
        for key, example_value in example_dict.items():
            if key not in merged:
                # Key doesn't exist in existing, add it from example
                merged[key] = deepcopy(example_value)
            elif isinstance(merged[key], dict) and isinstance(example_value, dict):
                # Both are dicts, recursively merge
                merged[key] = self.deep_merge(merged[key], example_value)
            # If key exists and is not a dict, keep existing value
        
        return merged
    
    def merge_missing_keys(self, config_file, example_file):
        """Merge missing keys from example file into existing config file"""
        config_path = self.root_dir / config_file
        example_path = self.root_dir / example_file
        
        if not config_path.exists() or not example_path.exists():
            return False
        
        try:
            # Load existing config
            with open(config_path, 'r', encoding='utf-8') as f:
                existing_config = json.load(f)
            
            # Load example config
            with open(example_path, 'r', encoding='utf-8') as f:
                example_config = json.load(f)
            
            # Merge missing keys
            merged_config = self.deep_merge(existing_config, example_config)
            
            # Check if anything changed
            if merged_config != existing_config:
                # Save merged config
                with open(config_path, 'w', encoding='utf-8') as f:
                    json.dump(merged_config, f, indent=2, ensure_ascii=False)
                return True
            
            return False
        except Exception as e:
            print(f"Error merging {config_file}: {e}")
            return False
    
    def check_and_create_configs(self):
        """Check for required config files and create them if missing, or merge missing keys"""
        results = {
            "created": [],
            "updated": [],
            "existing": [],
            "errors": []
        }
        
        for config_file, example_file in self.required_configs.items():
            config_path = self.root_dir / config_file
            example_path = self.root_dir / example_file
            
            if config_path.exists():
                # File exists, check if we need to merge missing keys
                if example_path.exists():
                    if self.merge_missing_keys(config_file, example_file):
                        results["updated"].append(config_file)
                        print(f"✓ Updated {config_file} with missing keys from {example_file}")
                    else:
                        results["existing"].append(config_file)
                else:
                    results["existing"].append(config_file)
                continue
                
            if not example_path.exists():
                results["errors"].append(f"Example file {example_file} not found")
                continue
                
            try:
                # Create config file from example
                shutil.copy2(example_path, config_path)
                results["created"].append(config_file)
                print(f"✓ Created {config_file} from {example_file}")
            except Exception as e:
                results["errors"].append(f"Failed to create {config_file}: {e}")
        
        return results
    
    def validate_config_files(self):
        """Validate that all config files have valid JSON structure"""
        validation_results = {
            "valid": [],
            "invalid": [],
            "errors": []
        }
        
        # Include training_score_unity.json in validation
        all_configs = list(self.required_configs.keys())
        
        for config_file in all_configs:
            config_path = self.root_dir / config_file
            
            if not config_path.exists():
                validation_results["errors"].append(f"{config_file} does not exist")
                continue
                
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    json.load(f)  # This will raise an error if JSON is invalid
                validation_results["valid"].append(config_file)
            except json.JSONDecodeError as e:
                validation_results["invalid"].append(f"{config_file}: {e}")
            except Exception as e:
                validation_results["errors"].append(f"{config_file}: {e}")
        
        return validation_results
    
    def get_status_summary(self):
        """Get a summary of configuration file status"""
        check_results = self.check_and_create_configs()
        validation_results = self.validate_config_files()
        
        summary = {
            "total_required": len(self.required_configs),
            "existing": len(check_results["existing"]),
            "created": len(check_results["created"]),
            "updated": len(check_results["updated"]),
            "errors": len(check_results["errors"]),
            "valid": len(validation_results["valid"]),
            "invalid": len(validation_results["invalid"]),
            "details": {
                "check_results": check_results,
                "validation_results": validation_results
            }
        }
        
        return summary


def check_configs_from_gui():
    """Convenience function to check configs from GUI launcher"""
    checker = ConfigChecker()
    return checker.get_status_summary()


if __name__ == "__main__":
    # Test the config checker
    checker = ConfigChecker()
    summary = checker.get_status_summary()
    print("Configuration Status Summary:")
    print(f"Total required: {summary['total_required']}")
    print(f"Existing: {summary['existing']}")
    print(f"Created: {summary['created']}")
    print(f"Errors: {summary['errors']}")
    print(f"Valid: {summary['valid']}")
    print(f"Invalid: {summary['invalid']}")


