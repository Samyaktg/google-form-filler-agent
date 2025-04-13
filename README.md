# AI Google Form Filler

A Streamlit-based application that automates Google Form responses using AI-generated content.

## Features

- Uses Gemini AI to generate realistic form responses
- Handles multiple types of Google Form elements:
  - Text fields
  - Multiple choice questions
  - Checkboxes
  - Dropdown menus
  - Linear scales
  - Grid/matrix questions
  - Date and time fields
- User-friendly Streamlit interface
- Limits usage to prevent abuse (max 15 responses per day per user)
- Adapts responses to target audience specifications

## Setup

1. Clone this repository
2. Install the required packages:
   ```
   pip install -r requirements.txt
   ```
3. Make sure you have a compatible browser installed (Microsoft Edge)
4. Update the `config.py` file with your Gemini API key
5. Run the Streamlit app:
   ```
   streamlit run app.py
   ```

## Usage

1. Enter a Google Form URL
2. Provide audience details:
   - Target audience description
   - Age groups
   - Gender preferences
   - Countries
   - Form objective
3. Select the number of responses to generate (1-15)
4. Click "Generate and Submit Responses"
5. Monitor the progress as the application:
   - Extracts the form structure
   - Generates appropriate AI responses
   - Fills and submits the form

## Limitations

- Currently works best with Microsoft Edge
- Maximum 15 responses per user per day
- Some complex form elements may not be fully supported
- Captchas and other anti-bot measures will prevent successful submissions

## Disclaimer

This tool is meant for educational and testing purposes only. Do not use it to submit fraudulent or spam responses to forms. Automated form submission may violate the terms of service of the form provider.
