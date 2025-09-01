import threading
import time
import subprocess
import sys
import os
import json
import queue
import re
from datetime import datetime

class BotController:
    def __init__(self, main_window):
        self.main_window = main_window
        self.bot_running = False
        self.bot_thread = None
        self.status_update_thread = None
        self.log_monitor_thread = None
        self.bot_process = None  # Store process reference for termination
        
        # Queues for communication between threads
        self.status_queue = queue.Queue()
        self.log_queue = queue.Queue()
        
        # Bot status data
        self.current_status = {
            'year': 'Unknown Year',
            'energy': 0.0,
            'turn': 'Unknown',
            'mood': 'Unknown',
            'goal_met': False,
            'stats': {
                'spd': 0,
                'sta': 0,
                'pwr': 0,
                'guts': 0,
                'wit': 0
            }
        }
        
        # Status update interval
        self.status_update_interval = 1.0  # seconds
        
        # Start status update thread
        self.start_status_updates()
    
    def start_status_updates(self):
        """Start the status update thread"""
        self.status_update_thread = threading.Thread(target=self.status_update_loop, daemon=True)
        self.status_update_thread.start()
    
    def start_bot(self):
        """Start the bot automation"""
        if self.bot_running:
            return
        
        self.bot_running = True
        self.main_window.add_log("Starting Uma Musume Auto-Train Bot...", "info")
        
        # Start bot in separate thread
        self.bot_thread = threading.Thread(target=self.run_bot, daemon=True)
        self.bot_thread.start()
        
        # Start log monitoring thread
        self.log_monitor_thread = threading.Thread(target=self.monitor_bot_logs, daemon=True)
        self.log_monitor_thread.start()
    
    def stop_bot(self):
        """Stop the bot automation"""
        if not self.bot_running:
            return
        
        self.bot_running = False
        self.main_window.add_log("Stopping bot...", "warning")
        
        # Terminate the bot process if it's running
        if self.bot_process and hasattr(self.bot_process, 'poll'):
            try:
                self.main_window.add_log("Terminating bot process...", "info")
                self.bot_process.terminate()
                
                # Wait for process to terminate gracefully
                try:
                    self.bot_process.wait(timeout=5)
                    self.main_window.add_log("Bot process terminated gracefully", "success")
                except subprocess.TimeoutExpired:
                    # Force kill if it doesn't terminate gracefully
                    self.main_window.add_log("Force killing bot process...", "warning")
                    self.bot_process.kill()
                    self.bot_process.wait()
                    self.main_window.add_log("Bot process force killed", "warning")
                    
            except Exception as e:
                self.main_window.add_log(f"Error terminating bot process: {e}", "error")
            finally:
                self.bot_process = None
        
        # Wait for bot thread to finish
        if self.bot_thread and self.bot_thread.is_alive():
            self.bot_thread.join(timeout=2)
        
        if self.log_monitor_thread and self.log_monitor_thread.is_alive():
            self.log_monitor_thread.join(timeout=1)
            
        self.main_window.add_log("Bot stopped successfully", "success")
    
    def run_bot(self):
        """Run the bot automation"""
        try:
            self.main_window.add_log("Bot started successfully", "success")
            self.main_window.add_log("Checking ADB connection...", "info")
            
            # Check if main script exists
            if os.path.exists('main.py'):
                self.main_window.add_log("Found main.py, starting automation...", "info")
                
                try:
                    # Run the main ADB bot in a subprocess with unbuffered output
                    self.bot_process = subprocess.Popen(
                        [sys.executable, '-u', 'main.py'],  # -u for unbuffered output
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        text=True,
                        bufsize=0,  # Unbuffered
                        universal_newlines=True,
                        encoding='utf-8',  # Explicitly set UTF-8 encoding
                        errors='replace'   # Replace problematic characters instead of failing
                    )
                    
                    self.main_window.add_log("Bot process started successfully", "success")
                    
                    # Monitor the process output
                    while self.bot_running and self.bot_process and self.bot_process.poll() is None:
                        try:
                            output = self.bot_process.stdout.readline()
                            if output:
                                # Process the output for status updates and logging
                                self.process_bot_output(output.strip())
                            else:
                                # No output, but process might still be running
                                time.sleep(0.1)
                        except UnicodeDecodeError as e:
                            # Handle Unicode decoding errors gracefully
                            print(f"Unicode decode error in bot output: {e}")
                            try:
                                # Try to decode with error handling
                                if hasattr(output, 'decode'):
                                    decoded_output = output.decode('utf-8', errors='replace')
                                    self.process_bot_output(decoded_output.strip())
                            except Exception as decode_error:
                                print(f"Failed to decode output: {decode_error}")
                        except Exception as e:
                            self.main_window.add_log(f"Error reading bot output: {e}", "error")
                            break
                    
                    # Check if process finished
                    if self.bot_process and self.bot_process.poll() is not None:
                        self.main_window.add_log(f"Bot process finished with code: {self.bot_process.returncode}", "info")
                    else:
                        self.main_window.add_log("Bot process terminated", "warning")
                        
                except Exception as e:
                    self.main_window.add_log(f"Error running bot: {e}", "error")
                    # Clean up the process if it was created
                    if self.bot_process:
                        try:
                            self.bot_process.terminate()
                            self.bot_process = None
                        except:
                            pass
            else:
                self.main_window.add_log("main.py not found", "error")
                
        except Exception as e:
            self.main_window.add_log(f"Critical error in bot controller: {e}", "error")
        finally:
            # Clean up the process if it still exists
            if self.bot_process:
                try:
                    self.bot_process.terminate()
                    self.bot_process = None
                except:
                    pass
            self.bot_running = False
            self.main_window.add_log("Bot stopped", "warning")
    
    def process_bot_output(self, output):
        """Process bot output to extract status updates and logs"""
        if not output or not output.strip():
            return
        
        try:
            # Ensure output is properly encoded as a string
            if not isinstance(output, str):
                output = str(output)
            
            # Add to log queue for display
            self.log_queue.put(output)
            
            # Try to extract status information from the output
            self.extract_status_from_output(output)
        except Exception as e:
            # Log error but continue processing
            print(f"Error processing bot output: {e}")
            # Try to add the raw output to logs anyway
            try:
                self.log_queue.put(str(output))
            except:
                pass
    
    def extract_status_from_output(self, output):
        """Extract status information from bot output"""
        try:
            # Ensure output is a string and handle any encoding issues
            if not isinstance(output, str):
                output = str(output)
            
            # Extract year information
            year_match = re.search(r'Year:\s*(.+)', output)
            if year_match:
                year = year_match.group(1).strip()
                self.update_status('year', year)
            
            # Extract energy information
            energy_match = re.search(r'Energy:\s*([\d.]+)%', output)
            if energy_match:
                energy = float(energy_match.group(1))
                self.update_status('energy', energy)
            
            # Extract turn information
            turn_match = re.search(r'Turn:\s*(.+)', output)
            if turn_match:
                turn = turn_match.group(1).strip()
                self.update_status('turn', turn)
            
            # Extract mood information
            mood_match = re.search(r'Mood:\s*(.+)', output)
            if mood_match:
                mood = mood_match.group(1).strip()
                self.update_status('mood', mood)
            
            # Extract goal status
            goal_match = re.search(r'Status:\s*(.+)', output)
            if goal_match:
                goal_text = goal_match.group(1).strip()
                # Check if goal is met (criteria met)
                goal_met = "criteria met" in goal_text.lower() or "goal achieved" in goal_text.lower()
                self.update_status('goal_met', goal_met)
            
            # Extract stats
            stats_match = re.search(r'Current stats:\s*(.+)', output)
            if stats_match:
                stats_text = stats_match.group(1)
                stats = self.parse_stats_from_text(stats_text)
                if stats:
                    self.update_status('stats', stats, partial=True)
                    
        except Exception as e:
            # Don't log parsing errors to avoid spam, but print to console for debugging
            print(f"Error extracting status from output: {e}")
            pass
    
    def parse_stats_from_text(self, stats_text):
        """Parse stats from text like 'SPD: 244, STA: 176, PWR: 166, GUTS: 99, WIT: 126'"""
        try:
            if not stats_text or not isinstance(stats_text, str):
                return {}
            
            # Ensure the text is properly encoded
            stats_text = str(stats_text)
                
            stats = {}
            # Look for patterns like "spd: 123", "sta: 456", etc.
            for stat in ['spd', 'sta', 'pwr', 'guts', 'wit']:
                match = re.search(f'{stat}:\\s*(\\d+)', stats_text, re.IGNORECASE)
                if match:
                    stats[stat] = int(match.group(1))
            return stats
        except Exception as e:
            print(f"Error parsing stats from text: {e}")
            return {}
    
    def update_status(self, field, value, partial=False):
        """Update status field and queue for GUI update"""
        if field == 'stats':
            if partial:
                # Partial update - only update specific stats
                self.current_status['stats'].update(value)
            else:
                # Full update - replace all stats
                self.current_status['stats'] = value
        else:
            self.current_status[field] = value
        
        # Queue status update for GUI
        self.status_queue.put(self.current_status.copy())
    
    def status_update_loop(self):
        """Main status update loop that runs continuously"""
        while True:
            try:
                # Check for status updates
                try:
                    while not self.status_queue.empty():
                        status = self.status_queue.get_nowait()
                        # Update GUI status panel
                        self.main_window.root.after(0, self.update_gui_status, status)
                except queue.Empty:
                    pass
                
                # Check for log updates
                try:
                    while not self.log_queue.empty():
                        log_entry = self.log_queue.get_nowait()
                        # Add to GUI log panel
                        self.main_window.root.after(0, self.add_log_to_gui, log_entry)
                except queue.Empty:
                    pass
                
                time.sleep(self.status_update_interval)
                
            except Exception as e:
                # Log error but continue running
                print(f"Error in status update loop: {e}")
                time.sleep(1)
    
    def update_gui_status(self, status):
        """Update GUI status panel (called from main thread)"""
        try:
            if hasattr(self.main_window, 'status_panel'):
                self.main_window.status_panel.update_from_bot_data(status)
        except Exception as e:
            print(f"Error updating GUI status: {e}")
    
    def add_log_to_gui(self, log_entry):
        """Add log entry to GUI (called from main thread)"""
        try:
            if hasattr(self.main_window, 'log_panel'):
                # Determine log level based on content
                log_level = self.determine_log_level(log_entry)
                self.main_window.log_panel.add_log_entry(log_entry, log_level)
        except Exception as e:
            print(f"Error adding log to GUI: {e}")
    
    def determine_log_level(self, log_entry):
        """Determine log level based on log entry content"""
        try:
            if not log_entry or not isinstance(log_entry, str):
                return 'info'
                
            log_lower = log_entry.lower()
            
            if any(word in log_lower for word in ['error', 'failed', 'exception']):
                return 'error'
            elif any(word in log_lower for word in ['warning', 'warn']):
                return 'warning'
            elif any(word in log_lower for word in ['success', 'completed', 'found']):
                return 'success'
            elif any(word in log_lower for word in ['debug']):
                return 'debug'
            else:
                return 'info'
        except Exception:
            return 'info'
    
    def monitor_bot_logs(self):
        """Monitor bot logs for real-time updates"""
        while self.bot_running:
            try:
                # This thread is now handled by the main status update loop
                time.sleep(0.1)
            except Exception as e:
                print(f"Error in log monitor: {e}")
                break
    
    def get_current_status(self):
        """Get current bot status"""
        try:
            return self.current_status.copy()
        except Exception:
            return {}
    
    def is_bot_running(self):
        """Check if bot is currently running"""
        return self.bot_running
