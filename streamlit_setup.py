"""
Optional script to set up the environment for Streamlit deployment.
This script is executed during the deployment process.
"""

import os
import subprocess
import sys

def setup_chrome_in_streamlit():
    """Install Chrome in Streamlit Cloud if needed"""
    # Check if we're in a Streamlit environment
    if "STREAMLIT_SHARING" in os.environ or "STREAMLIT_CLOUD" in os.environ:
        print("Setting up Chrome for Streamlit Cloud...")
        
        try:
            # Install Chrome using shell=True for pipe operations
            subprocess.check_call("apt-get update", shell=True)
            subprocess.check_call("apt-get install -y wget gnupg unzip", shell=True)
            subprocess.check_call("wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add -", shell=True)
            subprocess.check_call("echo 'deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main' >> /etc/apt/sources.list.d/google-chrome.list", shell=True)
            subprocess.check_call("apt-get update", shell=True)
            subprocess.check_call("apt-get install -y google-chrome-stable", shell=True)
            
            # Install ChromeDriver
            subprocess.check_call("apt-get install -yqq unzip", shell=True)
            subprocess.check_call("LATEST_DRIVER=$(curl -sS chromedriver.storage.googleapis.com/LATEST_RELEASE) && wget -O /tmp/chromedriver.zip http://chromedriver.storage.googleapis.com/${LATEST_DRIVER}/chromedriver_linux64.zip", shell=True)
            subprocess.check_call("unzip /tmp/chromedriver.zip chromedriver -d /usr/local/bin/", shell=True)
            subprocess.check_call("chmod +x /usr/local/bin/chromedriver", shell=True)
            
            print("Chrome setup completed successfully!")
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"Error setting up Chrome: {e}")
            return False
    
    return True  # Not in Streamlit Cloud, no setup needed

if __name__ == "__main__":
    setup_chrome_in_streamlit()
