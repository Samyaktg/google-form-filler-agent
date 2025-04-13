"""
Configuration file for the Google Form Filler application.
"""

import os

# Application settings
MAX_RESPONSES_PER_USER = 15
MAX_RESPONSES_PER_FORM = 50
USER_DB_PATH = "user_database.json"
USAGE_LOG_PATH = "usage_log.json"

# API keys
GEMINI_API_KEY = "AIzaSyCC93mbMLR_mjh0N6yX33LA8Oy9XKoMnGE"  # Replace with environment variable in production

# Form generation settings
AGE_GROUPS = [
    "Under 18",
    "18-24",
    "25-34", 
    "35-44",
    "45-54",
    "55-64",
    "65+"
]

GENDER_OPTIONS = [
    "Male",
    "Female", 
    "Non-binary/third gender",
    "Prefer not to say"
]

COUNTRIES = [
    "United States", "Canada", "United Kingdom", "Australia", 
    "India", "Germany", "France", "Japan", "China",
    "Brazil", "Mexico", "South Africa", "Other"
]

# WebDriver settings
WEBDRIVER_WAIT_TIME = 20
WEBDRIVER_IMPLICIT_WAIT = 5
