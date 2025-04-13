"""
User tracking module for the Google Form Filler.
Tracks usage limits per user/IP address.
"""

import json
import os
import time
from datetime import datetime, timedelta
from config import USER_DB_PATH, USAGE_LOG_PATH, MAX_RESPONSES_PER_USER, MAX_RESPONSES_PER_FORM

class UserTracker:
    def __init__(self):
        """Initialize the user tracker with database paths"""
        self.user_db_path = USER_DB_PATH if 'USER_DB_PATH' in globals() else "user_database.json"
        self.usage_log_path = USAGE_LOG_PATH if 'USAGE_LOG_PATH' in globals() else "usage_log.json"
        self._load_data()
    
    def _load_data(self):
        """Load user data from JSON files or initialize if not exists"""
        # Load user database
        if os.path.exists(self.user_db_path):
            try:
                with open(self.user_db_path, 'r') as f:
                    self.user_data = json.load(f)
            except json.JSONDecodeError:
                self.user_data = {}
        else:
            self.user_data = {}
        
        # Load usage logs
        if os.path.exists(self.usage_log_path):
            try:
                with open(self.usage_log_path, 'r') as f:
                    self.usage_logs = json.load(f)
            except json.JSONDecodeError:
                self.usage_logs = []
        else:
            self.usage_logs = []
    
    def _save_data(self):
        """Save user data to JSON files"""
        # Make sure directory exists
        os.makedirs(os.path.dirname(self.user_db_path), exist_ok=True)
        os.makedirs(os.path.dirname(self.usage_log_path), exist_ok=True)
        
        # Save user database
        with open(self.user_db_path, 'w') as f:
            json.dump(self.user_data, f, indent=2)
        
        # Save usage logs
        with open(self.usage_log_path, 'w') as f:
            json.dump(self.usage_logs, f, indent=2)
    
    def get_user_key(self, ip, user_agent):
        """Create a unique key for the user based on IP and user agent"""
        return f"{ip}_{user_agent[:20]}"
    
    def get_today_date(self):
        """Get today's date in YYYY-MM-DD format"""
        return datetime.now().strftime("%Y-%m-%d")
    
    def get_remaining_submissions(self, ip, user_agent):
        """Get the number of remaining submissions for a user today"""
        user_key = self.get_user_key(ip, user_agent)
        today = self.get_today_date()
        
        # Initialize user if not exists
        if user_key not in self.user_data:
            self.user_data[user_key] = {
                "last_activity": today,
                "daily_submissions": {}
            }
        
        # Reset counter if it's a new day
        if today not in self.user_data[user_key]["daily_submissions"]:
            self.user_data[user_key]["daily_submissions"][today] = 0
        
        # Calculate remaining submissions
        used_today = self.user_data[user_key]["daily_submissions"][today]
        max_responses = MAX_RESPONSES_PER_USER if 'MAX_RESPONSES_PER_USER' in globals() else 15
        remaining = max_responses - used_today
        
        return max(0, remaining)
    
    def record_usage(self, ip, user_agent, form_url, requested, successful):
        """Record form submission usage"""
        user_key = self.get_user_key(ip, user_agent)
        today = self.get_today_date()
        
        # Update user data
        if user_key not in self.user_data:
            self.user_data[user_key] = {
                "last_activity": today,
                "daily_submissions": {}
            }
        
        if today not in self.user_data[user_key]["daily_submissions"]:
            self.user_data[user_key]["daily_submissions"][today] = 0
        
        # Increment submission count
        self.user_data[user_key]["daily_submissions"][today] += successful
        self.user_data[user_key]["last_activity"] = today
        
        # Add to usage log
        log_entry = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "ip": ip,
            "user_agent": user_agent,
            "form_url": form_url,
            "requested": requested,
            "successful": successful
        }
        self.usage_logs.append(log_entry)
        
        # Save data
        self._save_data()
        
        return self.get_remaining_submissions(ip, user_agent)
