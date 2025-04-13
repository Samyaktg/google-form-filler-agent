"""
Streamlit application for the Google Form Filler
"""

import streamlit as st
import time
import json
import os
import re
import sys
from datetime import datetime
from config import (
    AGE_GROUPS, GENDER_OPTIONS, COUNTRIES, 
    MAX_RESPONSES_PER_USER, MAX_RESPONSES_PER_FORM
)

# Import the form filler functionality
from proto1 import (
    setup_driver, extract_form_structure, 
    generate_responses, fill_form
)

# Set page config
st.set_page_config(
    page_title="AI Form Filler",
    page_icon="📝",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize user tracker
@st.cache_resource
def get_user_tracker():
    from user_tracker import UserTracker
    return UserTracker()

user_tracker = get_user_tracker()

# Get user's IP address (in production, you'd extract this from request headers)
def get_client_ip():
    # For local development, use a placeholder IP
    # In production, you'd get this from request headers
    return "127.0.0.1"

# Check remaining submissions
client_ip = get_client_ip()
user_agent = st.session_state.get("user_agent", "Unknown")
remaining_submissions = user_tracker.get_remaining_submissions(client_ip, user_agent)

# Header
st.title("🤖 AI Google Form Filler")
st.markdown("""
This application uses AI to generate and submit responses to Google Forms.
Please use responsibly and ethically. This tool is for educational purposes only.
""")

# Show usage limit information
st.sidebar.header("Usage Information")
st.sidebar.info(f"You have {remaining_submissions} out of {MAX_RESPONSES_PER_USER} daily submissions remaining.")

# Form URL input
form_url = st.text_input("Google Form URL", help="Enter the full URL of the Google Form")

# Form validation
url_pattern = re.compile(r'https://docs\.google\.com/forms/d/e/.*?/viewform')
if form_url and not url_pattern.match(form_url):
    st.warning("Please enter a valid Google Form URL (should start with https://docs.google.com/forms/)")

# Create columns for form inputs
col1, col2 = st.columns(2)

with col1:
    st.subheader("Target Audience")
    audience = st.text_area("Describe the target audience for this form", 
                            help="Who is intended to answer this form? (e.g., college students, professionals, parents)")
    
    age_group = st.multiselect("Age Group", options=AGE_GROUPS, 
                               default=["25-34", "35-44"], 
                               help="Select one or more target age groups")
    
    gender = st.multiselect("Gender", options=GENDER_OPTIONS, 
                            default=["Male", "Female"], 
                            help="Select one or more gender options")

with col2:
    country = st.multiselect("Country", options=COUNTRIES, 
                             default=["United States"], 
                             help="Select one or more countries")
    
    objective = st.text_area("Form Objective", 
                             help="What is the purpose of this form? (e.g., feedback, survey, registration)")
    
    num_responses = st.slider("Number of Responses", 
                              min_value=1, max_value=min(remaining_submissions, 15), 
                              value=min(3, remaining_submissions), 
                              help=f"Maximum {min(remaining_submissions, 15)} responses allowed")

# Submit button
if st.button("Generate and Submit Responses", disabled=remaining_submissions <= 0):
    if not form_url:
        st.error("Please enter a Google Form URL.")
    elif not audience:
        st.error("Please describe the target audience.")
    elif not age_group:
        st.error("Please select at least one age group.")
    elif not gender:
        st.error("Please select at least one gender option.")
    elif not country:
        st.error("Please select at least one country.")
    elif not objective:
        st.error("Please describe the form objective.")
    else:
        # Create a status bar
        status_bar = st.progress(0)
        status_text = st.empty()
        
        # Create a placeholder for the log output
        log_output = st.empty()
        
        # Store logs in a list for display
        logs = []
        
        def update_log(message):
            """Update log display with new message"""
            logs.append(f"{datetime.now().strftime('%H:%M:%S')} - {message}")
            log_output.code("\n".join(logs), language="bash")
        
        # Start the process
        update_log(f"Starting to process {form_url}")
        update_log(f"Preparing to generate {num_responses} responses")
        
        # Setup WebDriver for Streamlit environment
        update_log("Setting up WebDriver for Streamlit environment...")
        driver = setup_driver("chrome")  # Explicitly request Chrome
        
        if driver:
            try:
                # Combine audience information
                target_profile = f"A {', '.join(gender)} aged {', '.join(age_group)} from {', '.join(country)}. {audience} {objective}"
                update_log(f"Target profile: {target_profile}")
                
                successful_submissions = 0
                
                for i in range(num_responses):
                    # Update progress
                    progress = (i) / num_responses
                    status_bar.progress(progress)
                    status_text.text(f"Processing submission {i+1} of {num_responses}...")
                    
                    # Extract form structure
                    update_log(f"Extracting form structure for submission {i+1}...")
                    form_structure = extract_form_structure(driver, form_url)
                    
                    if not form_structure:
                        update_log("Failed to extract form structure. Skipping.")
                        continue
                    
                    # Generate responses
                    update_log(f"Generating responses for submission {i+1}...")
                    answers = generate_responses(form_structure, target_profile, i)
                    
                    if not answers:
                        update_log("Failed to generate answers. Skipping.")
                        continue
                    
                    # Fill form
                    update_log(f"Filling form for submission {i+1}...")
                    if fill_form(driver, form_url, form_structure, answers):
                        successful_submissions += 1
                        update_log(f"✅ Submission {i+1} completed successfully.")
                    else:
                        update_log(f"❌ Submission {i+1} failed.")
                    
                    # Add delay between submissions
                    if i < num_responses - 1:
                        wait_time = 5
                        update_log(f"Waiting {wait_time} seconds before next submission...")
                        time.sleep(wait_time)
                
                # Final update
                status_bar.progress(1.0)
                status_text.text(f"Completed {successful_submissions} out of {num_responses} submissions.")
                
                # Record the usage
                user_tracker.record_usage(client_ip, user_agent, form_url, num_responses, successful_submissions)
                
                # Update remaining submissions display
                remaining = user_tracker.get_remaining_submissions(client_ip, user_agent)
                st.sidebar.success(f"Updated: You have {remaining} submissions remaining today.")
                
                if successful_submissions > 0:
                    st.success(f"Successfully submitted {successful_submissions} out of {num_responses} responses!")
                else:
                    st.error("Failed to submit any responses. Check the logs for details.")
            
            except Exception as e:
                update_log(f"Error: {str(e)}")
                st.error(f"An error occurred: {str(e)}")
            finally:
                # Close the WebDriver
                update_log("Closing WebDriver...")
                driver.quit()
        else:
            st.error("Failed to set up WebDriver. Check if you have Microsoft Edge installed.")

# Footer
st.markdown("---")
st.markdown("""
**Disclaimer**: This tool is meant for educational and testing purposes only. 
Do not use it to submit fraudulent or spam responses to forms.
""")
