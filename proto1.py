import os
import time
import json
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.common.keys import Keys
# --- Start Edge WebDriver Imports ---
from webdriver_manager.microsoft import EdgeChromiumDriverManager
from selenium.webdriver.edge.service import Service as EdgeService
from selenium.webdriver.edge.options import Options as EdgeOptions
# --- End Edge WebDriver Imports ---

import google.generativeai as genai
from bs4 import BeautifulSoup # Using BS4 alongside Selenium for easier parsing sometimes

# --- Configuration ---
# IMPORTANT: Set your Gemini API Key securely. Using environment variables is recommended.
# Example: Set an environment variable named GOOGLE_API_KEY with your key.
# If you don't use environment variables, replace os.getenv("GOOGLE_API_KEY")
# with your actual API key string (e.g., "YOUR_API_KEY_HERE").
# Be cautious about committing keys directly into version control.

# --- Corrected API Key Retrieval ---
# Retrieve the API key from the environment variable named "GOOGLE_API_KEY"
API_KEY = "GEMINI_API_KEY"

# If you are not using environment variables and want to hardcode the key (less secure):
# API_KEY = "YOUR_AIzaSyCC93mbMLR_mjh0N6yX33LA8Oy9XKoMnGE_KEY_HERE" # Replace with your actual key

if not API_KEY:
    print("Error: API key not available.")
    model = None  # Ensure model is None if API key is missing
else:
    try:
        genai.configure(api_key=API_KEY)
        model_name = 'gemini-2.0-flash'  # Make sure this model name is correct
        model = genai.GenerativeModel(model_name)
        print(f"Gemini model '{model_name}' configured.")  # Updated print statement
    except Exception as e:
        print(f"Error configuring Gemini: {e}")
        model = None # Ensure model is None if configuration fails

# Add this utility function at the top level for consistent header formatting
def print_header(message, level=1):
    """Print a formatted header message with different emphasis levels."""
    if level == 1:   # Major section header
        separator = "=" * 80
        print(f"\n{separator}")
        print(f"  {message}")
        print(f"{separator}")
    elif level == 2: # Sub-section header
        separator = "-" * 60
        print(f"\n{separator}")
        print(f"  {message}")
        print(f"{separator}")
    elif level == 3: # Important status/error
        print(f"\n>>> {message} <<<")
    else:            # Regular header
        print(f"\n--- {message} ---")

# Selenium WebDriver setup
def setup_driver():
    """Sets up the Selenium WebDriver."""
    try:
        # Use Edge specific options and service
        options = EdgeOptions()
        options.add_argument("--headless")  # Run in background without opening a browser window
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--window-size=1920,1080")  # Set a standard window size
        options.add_argument("--disable-extensions")  # Disable extensions
        options.add_argument("--disable-notifications")  # Disable notifications
        options.add_argument("--disable-popup-blocking")  # Disable popup blocking
        # Use a generic user agent or an Edge-specific one if needed
        options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36 Edg/91.0.864.59") # Example Edge UA

        service = EdgeService(EdgeChromiumDriverManager().install())
        driver = webdriver.Edge(service=service, options=options)
        print("Edge WebDriver setup successful (running in headless mode).")
        return driver
    except Exception as e:
        print(f"Error setting up WebDriver: {e}")
        return None

# --- Form Parsing ---
def extract_form_structure(driver, form_url):
    """
    Navigates to the form and extracts questions and input types using Selenium.
    Returns a list of dictionaries, each representing a question.
    """
    print(f"Attempting to load form: {form_url}")
    try:
        driver.get(form_url)
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'form[action*="formResponse"]'))
        )
        print("Form page loaded.")
        time.sleep(2) # Allow dynamic elements to potentially load

        soup = BeautifulSoup(driver.page_source, 'html.parser')
        form_elements = []

        question_items = soup.select('div[role="listitem"]')
        print(f"Found {len(question_items)} potential question items.")

        if not question_items:
             question_items = soup.select('div[jscontroller][data-params]')
             print(f"Fallback: Found {len(question_items)} potential question items using data-params.")


        for item in question_items:
            question_text_element = item.select_one('div[role="heading"]')
            question_text = question_text_element.get_text(strip=True) if question_text_element else "Unknown Question"

            input_type = "unknown"
            options = []
            aria_label = question_text  # Default to question text instead of input placeholder

            # Check for required marker
            required = "*" in question_text
            # Remove asterisk from question text for cleaner display
            clean_question = question_text.replace('*', '').strip()

            # Check for text inputs first
            text_input = item.select_one('input[type="text"], input[type="email"], input[type="url"], input[type="number"], textarea')
            if text_input:
                input_type = "text"
                # Only use aria-label if it's not a generic placeholder like "Your answer"
                input_label = text_input.get('aria-label', '').strip()
                if input_label and input_label != "Your answer":
                    aria_label = input_label
                else:
                    aria_label = clean_question  # Use question text when placeholder is generic
            
            # Check for date input
            elif item.select_one('input[type="date"], input[placeholder*="Date"]'):
                input_type = "date"
                aria_label = clean_question
            
            # Check for time input
            elif item.select_one('input[type="time"], input[placeholder*="Time"]'):
                input_type = "time"
                aria_label = clean_question
            
            # Check for file upload
            elif item.select('div[data-params*="uploadType"]'):
                input_type = "file_upload"
                aria_label = clean_question
            
            # Check for grid questions
            elif item.select('div[role="grid"], table.freebirdFormviewerViewItemsGridTable'):
                # Determine if it's a checkbox grid or radio button grid
                if item.select('div[role="checkbox"]'):
                    input_type = "checkbox_grid"
                else:
                    input_type = "grid"
                
                # Extract rows and columns
                rows = []
                cols = []
                
                # Try different selectors to catch all possible grid layouts
                row_elements = item.select('div[role="row"] th, tr th:first-child, div.freebirdFormviewerViewItemsGridRowGroup')
                col_elements = item.select('div[role="columnheader"], tr th:not(:first-child), div.freebirdFormviewerViewItemsGridCell[role="heading"]')
                
                # If traditional selectors fail, try more specific Google Forms selectors
                if not row_elements:
                    row_elements = item.select('div.freebirdFormviewerViewItemsGridRow')
                if not col_elements:
                    col_elements = item.select('div.freebirdFormviewerViewItemsGridColumnHeader')
                
                for row in row_elements:
                    row_text = row.get_text(strip=True)
                    if row_text:
                        rows.append(row_text)
                
                for col in col_elements:
                    col_text = col.get_text(strip=True)
                    if col_text:
                        cols.append(col_text)
                
                options = {"rows": rows, "columns": cols}
                aria_label = clean_question
                
                # If we couldn't extract rows/columns properly, use JavaScript
                if not rows or not cols:
                    try:
                        js_code = """
                        var result = {rows: [], columns: []};
                        var gridContainer = document.querySelector('.freebirdFormviewerViewItemsGridScrollContainer');
                        if (gridContainer) {
                            // Get row headers
                            var rowHeaders = gridContainer.querySelectorAll('.freebirdFormviewerViewItemsGridRowHeader');
                            rowHeaders.forEach(function(header) {
                                result.rows.push(header.textContent.trim());
                            });
                            
                            // Get column headers
                            var colHeaders = gridContainer.querySelectorAll('.freebirdFormviewerViewItemsGridColumnHeader');
                            colHeaders.forEach(function(header) {
                                result.columns.push(header.textContent.trim());
                            });
                        }
                        return result;
                        """
                        grid_data = driver.execute_script(js_code)
                        if grid_data['rows']:
                            rows = grid_data['rows']
                        if grid_data['columns']:
                            cols = grid_data['columns']
                        options = {"rows": rows, "columns": cols}
                        print(f"  Extracted grid data via JavaScript: {len(rows)} rows, {len(cols)} columns")
                    except Exception as e:
                        print(f"  Error extracting grid via JavaScript: {e}")

            # Check for radio buttons (multiple choice)
            elif item.select('div[role="radiogroup"]'):
                scale_labels = item.select('label span')
                scale_values = [lbl.get_text(strip=True) for lbl in scale_labels if lbl.get_text(strip=True)]
                
                # Enhanced linear scale detection
                is_numeric_scale = any(lbl.get_text(strip=True).isdigit() for lbl in scale_labels)
                is_linear_scale = (
                    is_numeric_scale or 
                    item.select('div[aria-label*="stars"], div[aria-label*="rating"], div[aria-label*="scale"]') or
                    item.select('div[jsname="RRJqzb"]') or  # Google Forms rating component
                    item.select('div[jsname="NfjK7"], div[jsname="jq1lEb"]')  # "Less"/"More" labels
                )

                if is_linear_scale:
                    input_type = "linear_scale"
                    options = scale_values
                    
                    # Capture endpoint labels (Like "Less" and "More")
                    endpoint_labels = {}
                    less_label = item.select_one('div[jsname="NfjK7"]')
                    more_label = item.select_one('div[jsname="jq1lEb"]')
                    
                    if less_label:
                        endpoint_labels["start"] = less_label.get_text(strip=True)
                    if more_label:
                        endpoint_labels["end"] = more_label.get_text(strip=True)
                    
                    # If endpoint labels exist, add them to options
                    if endpoint_labels:
                        print(f"  Detected scale with labeled endpoints: {endpoint_labels}")
                    
                    # Extract actual data-value attributes when available
                    data_values = []
                    radio_buttons = item.select('div[role="radio"]')
                    for button in radio_buttons:
                        data_val = button.get('data-value')
                        if data_val:
                            data_values.append(data_val)
                    
                    if data_values:
                        options = data_values
                        print(f"  Using data-value attributes for scale: {options}")
                    # If we have radio buttons but no text labels or data-values
                    elif not options and radio_buttons:
                        options = [str(i+1) for i in range(len(radio_buttons))]
                        print(f"  Inferred {len(options)} numeric options from radio buttons")
                    
                    # Store endpoint labels for better response generation
                    if endpoint_labels:
                        if not isinstance(options, dict):
                            options = {"values": options, "labels": endpoint_labels}
                        else:
                            options["labels"] = endpoint_labels
                    
                    aria_label = clean_question

            elif item.select('div[role="group"]'):
                if item.select('div[role="checkbox"]'):
                    input_type = "checkbox"
                    option_elements = item.select('div[role="checkbox"] span')
                    options = [opt.get_text(strip=True) for opt in option_elements if opt.get_text(strip=True)]
                    aria_label = clean_question

            elif item.select_one('div[role="listbox"]'):
                input_type = "dropdown"
                option_elements = item.select('div[role="option"] span')
                options = [opt.get_text(strip=True) for opt in option_elements if opt.get_text(strip=True)]
                aria_label = clean_question

            if input_type != "unknown":
                 form_elements.append({
                     "question": clean_question,
                     "type": input_type,
                     "options": options,
                     "identifier": aria_label,
                     "required": required
                 })
                 print(f"  Extracted: '{clean_question}' (Type: {input_type}, Required: {required}, Options: {options if options else 'N/A'})")
            else:
                 print(f"  Skipped item, could not determine input type for: '{clean_question}'")

        if not form_elements:
            print("Warning: Could not extract any form questions. The structure might be unexpected.")
            print("Trying Selenium-based element finding...")
            try:
                question_containers = driver.find_elements(By.XPATH, '//div[contains(@class, "Qr7Oae")]/div/div/div[contains(@class, "freebirdFormviewerComponentsQuestionBaseRoot")]')
                if not question_containers:
                    question_containers = driver.find_elements(By.CSS_SELECTOR, 'div[role="listitem"]')

                print(f"Found {len(question_containers)} potential containers via Selenium.")

                for container in question_containers:
                    try:
                        q_text = container.find_element(By.CSS_SELECTOR, 'div[role="heading"]').text.strip()
                        q_type = "unknown"
                        q_options = []
                        q_identifier = q_text

                        if container.find_elements(By.CSS_SELECTOR, 'input[type="text"], textarea'):
                            q_type = "text"
                            try:
                                q_identifier = container.find_element(By.CSS_SELECTOR, 'input[type="text"], textarea').get_attribute('aria-label') or q_text
                            except NoSuchElementException:
                                q_identifier = q_text
                        elif container.find_elements(By.CSS_SELECTOR, 'div[role="radiogroup"]'):
                            q_type = "multiple_choice"
                            opts = container.find_elements(By.CSS_SELECTOR, 'div[role="radio"] span')
                            q_options = [o.text.strip() for o in opts if o.text.strip()]
                        elif container.find_elements(By.CSS_SELECTOR, 'div[role="checkbox"]'):
                             q_type = "checkbox"
                             opts = container.find_elements(By.CSS_SELECTOR, 'div[role="checkbox"] span')
                             q_options = [o.text.strip() for o in opts if o.text.strip()]
                        elif container.find_elements(By.CSS_SELECTOR, 'div[role="listbox"]'):
                            q_type = "dropdown"
                        elif container.find_elements(By.CSS_SELECTOR, 'div[role="radiogroup"][aria-labelledby]'):
                            scale_opts = container.find_elements(By.CSS_SELECTOR, 'label span')
                            if any(lbl.text.strip().isdigit() for lbl in scale_opts):
                                q_type = "linear_scale"
                                q_options = [lbl.text.strip() for lbl in scale_opts if lbl.text.strip()]

                        if q_type != "unknown":
                            form_elements.append({
                                "question": q_text,
                                "type": q_type,
                                "options": q_options,
                                "identifier": q_identifier.strip() if q_identifier else q_text
                            })
                            print(f"  Extracted via Selenium: '{q_text}' (Type: {q_type}, Options: {q_options if q_options else 'N/A'})")
                        else:
                            print(f"  Skipped Selenium item, could not determine input type for: '{q_text}'")

                    except NoSuchElementException:
                        print("  Skipped a container, couldn't find expected elements within it.")
                        continue
                    except Exception as e:
                        print(f"  Error processing a container: {e}")
                        continue

            except Exception as e:
                print(f"Error during Selenium-based extraction: {e}")

        print("\n--- DETECTED FORM STRUCTURE ---")
        for i, elem in enumerate(form_elements):
            print(f"Question {i+1}: '{elem['question']}' (Type: {elem['type']})")
            if elem['options']:
                print(f"  Options: {elem['options']}")
            print(f"  Identifier: '{elem['identifier']}'")
        print("----------------------------\n")

        return form_elements

    except TimeoutException:
        print(f"Error: Timed out waiting for form elements to load at {form_url}")
        return None
    except Exception as e:
        print(f"Error extracting form structure: {e}")
        return None

def fill_multiple_choice(driver, xpath_base, answer, q_identifier, options=None):
    """
    Selects the specified answer for a multiple-choice question.
    
    Args:
        driver: The Selenium WebDriver instance
        xpath_base: Base XPath to locate the question container
        answer: The answer text to select
        q_identifier: The question identifier for logging
        options: Available options for the question
        
    Returns:
        bool: True if successfully selected, False otherwise
    """
    print(f"  Handling multiple choice for '{q_identifier}' with answer: '{answer}'")
    
    try:
        # Direct approach - try to find the option with matching text and click it
        option_xpath = f"{xpath_base}//div[@role='radio']//span[contains(normalize-space(), '{answer}')]/ancestor::div[@role='radio']"
        
        try:
            option_element = WebDriverWait(driver, 3).until(
                EC.element_to_be_clickable((By.XPATH, option_xpath))
            )
            driver.execute_script("arguments[0].click();", option_element)
            print(f"  Selected option with text: '{answer}'")
            return True
        except (TimeoutException, NoSuchElementException):
            print(f"  Could not find option with exact text: '{answer}'")
            
            # Fallback 1: Fuzzy match against available options if provided
            if options:
                best_match = None
                best_score = 0
                
                for option in options:
                    # Simple matching score - can be improved
                    if answer.lower() in option.lower() or option.lower() in answer.lower():
                        score = len(set(answer.lower()) & set(option.lower()))
                        if score > best_score:
                            best_score = score
                            best_match = option
                
                if best_match:
                    fuzzy_xpath = f"{xpath_base}//div[@role='radio']//span[contains(normalize-space(), '{best_match}')]/ancestor::div[@role='radio']"
                    try:
                        fuzzy_element = WebDriverWait(driver, 3).until(
                            EC.element_to_be_clickable((By.XPATH, fuzzy_xpath))
                        )
                        driver.execute_script("arguments[0].click();", fuzzy_element)
                        print(f"  Selected best matching option: '{best_match}'")
                        return True
                    except (TimeoutException, NoSuchElementException):
                        print(f"  Could not find fuzzy matched option: '{best_match}'")
            
            # Fallback 2: Get all radio buttons and click the first one
            try:
                all_options = driver.find_elements(By.XPATH, f"{xpath_base}//div[@role='radio']")
                if all_options:
                    # Just click the first one as a last resort
                    driver.execute_script("arguments[0].click();", all_options[0])
                    print(f"  Selected first available option as fallback")
                    return True
            except Exception as e:
                print(f"  Failed to select any option: {e}")
                
        return False
    except Exception as e:
        print(f"  Error in multiple choice handling: {e}")
        return False

def enhance_linear_scale_support(driver, xpath_base, answer, q_identifier, q_options=None):
    """Enhanced approach for linear scale/rating questions with endpoint labels support"""
    print(f"  Handling linear scale/rating with answer: {answer}")
    
    # Extract endpoint labels if available
    endpoint_labels = {}
    if isinstance(q_options, dict) and "labels" in q_options:
        endpoint_labels = q_options.get("labels", {})
        scale_values = q_options.get("values", [])
    else:
        scale_values = q_options if isinstance(q_options, list) else []
    
    # Normalize the answer to a numeric value
    try:
        # First try direct conversion to integer
        num_answer = int(answer)
        print(f"  Input answer '{answer}' is already numeric: {num_answer}")
    except (ValueError, TypeError):
        num_answer = 0
        # Check if answer matches endpoint labels
        if endpoint_labels:
            lower_answer = answer.lower()
            start_label = endpoint_labels.get("start", "").lower()
            end_label = endpoint_labels.get("end", "").lower()
            
            if start_label and start_label in lower_answer:
                num_answer = 1  # First option
                print(f"  Mapped endpoint label '{start_label}' to value 1")
            elif end_label and end_label in lower_answer:
                # Map to the last option
                if scale_values and all(str(v).isdigit() for v in scale_values):
                    num_answer = max(int(v) for v in scale_values)
                else:
                    # Assume 5-point scale as fallback
                    num_answer = 5
                print(f"  Mapped endpoint label '{end_label}' to value {num_answer}")
            else:
                # Try to map text ratings to numbers
                rating_map = {
                    "very low": 1, "low": 1, "never": 1, "less": 1, "least": 1, "poor": 1,
                    "below average": 2, "rarely": 2, "seldom": 2, "fair": 2,
                    "average": 3, "moderate": 3, "sometimes": 3, "occasionally": 3, "neutral": 3,
                    "above average": 4, "often": 4, "good": 4, "frequently": 4, 
                    "very high": 5, "high": 5, "always": 5, "most": 5, "more": 5, "excellent": 5
                }
                
                for text, num in rating_map.items():
                    if text in lower_answer:
                        num_answer = num
                        print(f"  Mapped text '{answer}' to numeric value {num}")
                        break
    
    # Direct approach using data-value attribute
    try:
        # Find all radio buttons with their data-values
        radio_elements = driver.find_elements(By.XPATH, f"{xpath_base}//div[@role='radio']")
        
        if radio_elements:
            print(f"  Found {len(radio_elements)} radio buttons")
            
            # Try to map using data-value attribute
            if num_answer > 0 and num_answer <= len(radio_elements):
                # Try to find button with matching data-value
                for button in radio_elements:
                    data_value = button.get_attribute("data-value")
                    if data_value and int(data_value) == num_answer:
                        driver.execute_script("arguments[0].click();", button)
                        print(f"  Selected option with data-value={num_answer}")
                        return True
                
                # If we didn't find by data-value, use position (0-based index)
                idx = num_answer - 1
                driver.execute_script("arguments[0].click();", radio_elements[idx])
                print(f"  Selected option at position {idx+1}")
                return True
            else:
                # If no valid numeric answer, use middle value as default
                middle_idx = len(radio_elements) // 2
                driver.execute_script("arguments[0].click();", radio_elements[middle_idx])
                print(f"  Selected middle option (position {middle_idx+1}) as fallback")
                return True
                
        return False
    except Exception as e:
        print(f"  Error in direct data-value approach: {e}")
        
        # Traditional approach as fallback
        js_code = f"""
        var found = false;
        var radioButtons = document.querySelectorAll('{xpath_base} div[role="radio"]');
        
        if (radioButtons.length > 0) {{
            var targetIndex = {num_answer - 1};
            // If we have a valid target index, use it
            if (targetIndex >= 0 && targetIndex < radioButtons.length) {{
                radioButtons[targetIndex].click();
                found = true;
            }} else {{
                // Otherwise click the middle option
                var middleIndex = Math.floor(radioButtons.length / 2);
                radioButtons[middleIndex].click();
                found = true;
            }}
        }}
        return found;
        """
        
        if driver.execute_script(js_code):
            print("  Selected linear scale option via JavaScript")
            return True
        
        return False

def fill_form(driver, form_url, form_structure, answers):
    """Fills and submits the Google Form using Selenium."""
    print_header("FORM FILLING STARTED", 1)
    start_time = time.time()
    
    try:
        print(f"Loading form: {form_url}")
        driver.get(form_url)
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'form[action*="formResponse"]'))
        )
        print(f"Form loaded in {time.time() - start_time:.2f} seconds")
        time.sleep(1)

        for question_data in form_structure:
            question_start_time = time.time()
            q_identifier = question_data["identifier"]
            q_type = question_data["type"]

            if q_identifier not in answers:
                print_header(f"Missing answer for: '{q_identifier}'", 3)
                continue

            answer = answers[q_identifier]
            if answer is None or (isinstance(answer, (str, list)) and not answer and q_type != "text"):
                 print_header(f"Empty answer for: '{q_identifier}'", 3)
                 continue

            print_header(f"Processing question: '{q_identifier}'", 2)
            print(f"Type: {q_type}, Answer: '{answer}'")

            try:
                escaped_identifier = q_identifier.replace('"', '\\"')
                xpath_safe_identifier = escaped_identifier.replace("*", "\\*").replace("[", "\\[").replace("]", "\\]")
                clean_identifier = escaped_identifier.replace("*", "").strip()
                
                xpath_base = (
                    f'//div[@role="listitem" or contains(@class, "Qr7Oae") or contains(@class, "freebirdFormviewerComponentsQuestion")]'
                    f'[.//div[@role="heading"][contains(normalize-space(), "{clean_identifier}")] '
                    f'or (.//span[contains(text(), "{clean_identifier}") and not(ancestor::div[contains(@class, "quantumWizTextinputPaperinputMainContent")])]'
                    f'or .//input[@aria-label="{escaped_identifier}"] '
                    f'or .//textarea[@aria-label="{escaped_identifier}"])]'
                )
                
                print(f"  Looking for question with clean identifier: '{clean_identifier}'")

                if q_type == "text":
                    element_xpath = f"({xpath_base}//input[@type='text' or @type='email' or @type='url' or @type='number'] | {xpath_base}//textarea)[1]"
                    try:
                        element = WebDriverWait(driver, 5).until(
                            EC.visibility_of_element_located((By.XPATH, element_xpath))
                        )
                    except TimeoutException:
                        print(f"  First attempt failed. Trying fallback approach...")
                        fallback_xpath = f"//div[contains(., '{clean_identifier}')]//input[@type='text'] | //div[contains(., '{clean_identifier}')]//textarea"
                        element = WebDriverWait(driver, 5).until(
                            EC.visibility_of_element_located((By.XPATH, fallback_xpath))
                        )
                        print(f"  Found input element using fallback approach")
                    
                    try:
                        element.click()
                        element.clear()
                        element.send_keys(answer)
                        print(f"  Filled text field with: '{answer[:50]}...' (via send_keys)")
                    except Exception as e1:
                        print(f"  First attempt failed: {e1}")
                        try:
                            driver.execute_script("arguments[0].value = arguments[1];", element, answer)
                            driver.execute_script("arguments[0].dispatchEvent(new Event('input', { bubbles: true }));", element)
                            print(f"  Filled text field with: '{answer[:50]}...' (via value property)")
                        except Exception as e2:
                            print(f"  Second attempt failed: {e2}")
                            try:
                                for char in answer:
                                    element.send_keys(char)
                                    time.sleep(0.01)
                                print(f"  Filled text field with: '{answer[:50]}...' (character by character)")
                            except Exception as e3:
                                print(f"  All text input methods failed: {e3}")
                                raise

                elif q_type == "linear_scale":
                    # Pass the question options to the enhanced function
                    result = enhance_linear_scale_support(driver, xpath_base, answer, q_identifier, question_data.get('options'))
                    if not result:
                        print(f"  WARNING: Failed to select linear scale option for '{q_identifier}'")
                        try:
                            # Last attempt - click directly on any radio button in this question
                            radio_buttons = driver.find_elements(By.XPATH, f"{xpath_base}//div[@role='radio']")
                            if radio_buttons:
                                middle_idx = len(radio_buttons) // 2  # Choose middle option as safest
                                driver.execute_script("arguments[0].click();", radio_buttons[middle_idx])
                                print(f"  Selected option via direct selector as last resort")
                                time.sleep(0.5)  # Give it time to register
                        except Exception as e:
                            print(f"  Final attempt failed: {e}")

                elif q_type == "multiple_choice":
                    # Improve multiple_choice handling too, in case some linear scales are classified wrong
                    try:
                        # First try: Use our standard multiple choice handler
                        result = fill_multiple_choice(driver, xpath_base, answer, q_identifier, question_data.get('options'))
                        
                        # If it failed and options look numerical, try the linear scale approach as fallback
                        if not result and question_data.get('options') and any(opt.isdigit() for opt in question_data.get('options')):
                            print("  First attempt failed. Options look numerical, trying linear scale approach...")
                            result = enhance_linear_scale_support(driver, xpath_base, answer, q_identifier)
                            
                        if not result:
                            # Last resort: Just click any radio button
                            radios = driver.find_elements(By.XPATH, f"{xpath_base}//div[@role='radio']")
                            if radios:
                                driver.execute_script("arguments[0].click();", radios[0])
                                print(f"  Selected first radio button as last resort")
                                time.sleep(0.5)  # Give it time to register
                    except Exception as e:
                        print(f"  Error in multiple choice handling: {e}")

                print(f"Question completed in {time.time() - question_start_time:.2f} seconds")
                time.sleep(0.5)

            except TimeoutException:
                print_header(f"TIMEOUT on question: '{q_identifier}'", 3)
                print(f"Error: Timed out trying to find or interact with element for question: '{q_identifier}'. It might not be visible, the identifier might be incorrect, or the page structure is unexpected.")
            except NoSuchElementException:
                print_header(f"ELEMENT NOT FOUND: '{q_identifier}'", 3)
                print(f"Error: Could not find element for question: '{q_identifier}'. The form structure might have changed or the identifier is wrong.")
            except Exception as e:
                print_header(f"ERROR on question: '{q_identifier}'", 3)
                print(f"Error filling question '{q_identifier}': {e}")

        print_header("Searching for submit button", 2)
        submit_selectors = [
            '//div[@role="button"][.//span[normalize-space()="Submit"]]',
            '//button[@type="submit"][contains(normalize-space(), "Submit")]',
            '//div[@role="button"][contains(@jsname, "OCpkoe")]',
            'div[role="button"][jsname*="OCpkoe"]',
            'button[type="submit"]'
        ]
        submit_button = None
        
        print("Searching for submit button...")
        for i, selector in enumerate(submit_selectors):
             try:
                 finder = By.XPATH if selector.startswith("//") else By.CSS_SELECTOR
                 print(f"  Trying selector ({'XPath' if finder == By.XPATH else 'CSS'}) #{i+1}: {selector}")
                 submit_button = WebDriverWait(driver, 5).until(
                     EC.element_to_be_clickable((finder, selector))
                 )
                 print(f"Found submit button using selector #{i+1}.")
                 break
             except TimeoutException:
                 print(f"  Selector #{i+1} timed out.")
                 continue
             except NoSuchElementException:
                 print(f"  Selector #{i+1} not found.")
                 continue
             except Exception as e:
                 print(f"  Error with selector #{i+1}: {e}")
                 continue

        if submit_button:
            print_header("Submitting form", 2)
            try:
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", submit_button)
                time.sleep(0.5)
                driver.execute_script("arguments[0].click();", submit_button)
                print("Submit button clicked.")
                time.sleep(3)

                confirmation_texts = ["Your response has been recorded", "Submission successful"]
                page_text = driver.find_element(By.TAG_NAME, 'body').text
                if any(conf_text in page_text for conf_text in confirmation_texts):
                    print("Form submission confirmed.")
                    return True
                else:
                     error_elements = driver.find_elements(By.XPATH, '//div[@role="alert" or contains(@id, "error") or contains(@class, "error")]')
                     if error_elements:
                         print("Error: Form submission failed. Found validation errors:")
                         for error in error_elements:
                             error_text = error.text.strip()
                             if error_text:
                                 print(f"  - {error_text}")
                         return False
                     else:
                         print("Warning: Form submitted, but confirmation message not found and no validation errors detected. Assuming success.")
                         return True

            except Exception as e:
                print(f"Error clicking submit button or checking confirmation: {e}")
                return False
        else:
            print_header("SUBMIT BUTTON NOT FOUND", 3)
            print("Error: Could not find the submit button after trying all selectors.")
            return False

    except TimeoutException:
        print_header("FORM LOAD TIMEOUT", 3)
        print(f"Error: Timed out waiting for form page elements during filling: {form_url}")
        return False
    except Exception as e:
        print_header("UNEXPECTED ERROR", 3)
        print(f"An unexpected error occurred during form filling: {e}")
        return False
    finally:
        total_time = time.time() - start_time
        print_header(f"Form filling completed in {total_time:.2f} seconds", 2)

def generate_responses(form_structure, target_audience, variation_index):
    """
    Generates responses for the form using the Gemini API.
    Adds slight variation based on the variation_index.
    """
    if not model:
        print("Error: Gemini model not configured.")
        return None
    if not form_structure:
        print("Error: Cannot generate responses, form structure is empty.")
        return None

    variations = [
        "Focus on practical aspects.",
        "Emphasize cost-consciousness.",
        "Be slightly more enthusiastic.",
        "Be slightly more critical/analytical.",
        "Consider the perspective of a newcomer to the topic.",
        "Consider the perspective of an experienced user.",
    ]
    persona_variation = f"Persona Variation {variation_index+1}: {variations[variation_index % len(variations)]}"

    prompt = f"""
    You are an AI assistant tasked with filling out a Google Form.
    Your target audience is: {target_audience}.
    {persona_variation}

    Here is the EXACT structure of the form with the EXACT field identifiers that must be used:
    {json.dumps(form_structure, indent=2)}

    IMPORTANT INSTRUCTIONS:
    1. Generate ONLY answers for the fields shown above
    2. DO NOT add any fields not listed above
    3. For multiple choice questions, ONLY use EXACTLY one of the provided options
    4. For checkbox questions, ONLY use options from the provided list
    5. Match identifier text EXACTLY as given
    6. For linear_scale questions, ALWAYS use a NUMERIC value that matches one of the available options
    7. If a linear scale has options 1-5, you MUST answer with a number (1, 2, 3, 4, or 5), not words like "more" or "less"
    8. NEVER use text like "High" or "Low" for numeric rating scales - use the actual number

    Please provide answers in JSON format where the key is the 'identifier' from the form structure.

    Guidelines for answers:
    - For "text" type: Provide a relevant string answer
    - For "multiple_choice": Choose EXACTLY ONE option from the available options list
    - For "checkbox": Choose from the available options list only (1-3 options)
    - For "dropdown": Choose EXACTLY ONE option from the available list
    - For "linear_scale": ONLY use a NUMBER from the available options (e.g. 1, 2, 3, 4 or 5)
    - For "date" type: Provide a date in YYYY-MM-DD format
    - For "time" type: Provide a time in HH:MM format
    - For "grid" type: Provide a dictionary where keys are row names and values are column selections
    - For "checkbox_grid" type: Provide a dictionary where keys are row names and values are lists of column selections

    CRITICAL: For questions with a numeric scale (like 1-5), your answer MUST be one of these numbers, not text like "high" or "low".

    IMPORTANT: ONLY include fields that are in the form structure above.
    """

    print(f"\n--- Generating Response {variation_index + 1} ---")
    print(f"Target Audience: {target_audience}")
    print(f"Persona Variation: {persona_variation}")

    try:
        response = model.generate_content(prompt)
        response_text = response.text.strip()
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]
        response_text = response_text.strip()

        try:
            answers = json.loads(response_text)
            print("Generated Answers (JSON):")
            print(json.dumps(answers, indent=2))
            if not isinstance(answers, dict):
                print("Error: Gemini response is not a valid JSON dictionary.")
                return None

            form_identifiers = {q["identifier"] for q in form_structure}
            generated_keys = set(answers.keys())

            missing_keys = form_identifiers - generated_keys
            extra_keys = generated_keys - form_identifiers

            if missing_keys:
                print(f"Warning: Gemini response missing answers for identifiers: {missing_keys}")
            if extra_keys:
                print(f"Warning: Gemini response included unexpected identifiers: {extra_keys}")

            # Add validation for rating scales before returning answers
            if isinstance(answers, dict):
                for q in form_structure:
                    if q["type"] == "linear_scale" and q["identifier"] in answers:
                        answer = answers[q["identifier"]]
                        if not str(answer).isdigit():
                            print(f"Warning: Non-numeric value '{answer}' for linear scale question '{q['identifier']}'")
                            
                            # Extract the scale range
                            scale_options = q.get("options", [])
                            if isinstance(scale_options, dict) and "values" in scale_options:
                                scale_options = scale_options["values"]
                            
                            # Get numeric values from the scale if they exist
                            numeric_options = []
                            for opt in scale_options:
                                if str(opt).isdigit():
                                    numeric_options.append(int(opt))
                            
                            if numeric_options:
                                # Use the middle value as a reasonable default
                                numeric_options.sort()
                                default_value = numeric_options[len(numeric_options) // 2]
                                answers[q["identifier"]] = str(default_value)
                                print(f"  Converted to numeric value: {default_value}")
                            else:
                                # Assume a 1-5 scale as a fallback and pick the middle
                                answers[q["identifier"]] = "3"
                                print(f"  Assumed 1-5 scale and set default value: 3")
                                
            return answers
        except json.JSONDecodeError as json_err:
            print(f"Error: Could not decode JSON response from Gemini: {json_err}")
            print(f"Received text: {response_text}")
            return None

    except Exception as e:
        print(f"Error generating responses from Gemini: {e}")
        if "API key not valid" in str(e):
            print("Please ensure your GOOGLE_API_KEY is correct and valid.")
        try:
            if response and response.prompt_feedback:
                 print(f"Prompt Feedback: {response.prompt_feedback}")
        except Exception:
             pass

        return None

# --- Main Execution ---
def main():
    print_header("AI GOOGLE FORM FILLER", 1)
    print("Disclaimer: Use responsibly and ethically. Automating form submissions may violate terms of service.")

    form_url = input("Enter the Google Form link: ")
    target_audience = input("Enter the target audience description: ")
    try:
        num_responses = int(input("Enter the number of responses to generate: "))
        if num_responses <= 0:
            print("Number of responses must be positive.")
            return
    except ValueError:
        print("Invalid number. Please enter an integer.")
        return

    if not API_KEY or not model:
        print("Exiting due to missing API key or Gemini model configuration error.")
        return

    driver = setup_driver()
    if not driver:
        print("Exiting due to WebDriver setup failure.")
        return

    form_structure = None

    try:
        print_header("Starting Response Generation and Submission", 1)
        successful_submissions = 0
        for i in range(num_responses):
            print_header(f"Processing Submission {i + 1} of {num_responses}", 2)

            print("Extracting form structure...")
            form_structure = extract_form_structure(driver, form_url)
            if not form_structure:
                print(f"Could not extract form structure for submission {i + 1}. Skipping.")
                time.sleep(5)
                continue

            answers = generate_responses(form_structure, target_audience, i)
            if not answers:
                print(f"Failed to generate answers for submission {i + 1}. Skipping.")
                time.sleep(5)
                continue

            if fill_form(driver, form_url, form_structure, answers):
                successful_submissions += 1
                print(f"Submission {i + 1} completed successfully.")
            else:
                print(f"Submission {i + 1} failed.")
                time.sleep(10)

            wait_time = 5
            print(f"Waiting for {wait_time} seconds before next submission...")
            time.sleep(wait_time)

        print_header("Finished", 1)
        print(f"Successfully submitted {successful_submissions} out of {num_responses} requested responses.")

    except KeyboardInterrupt:
         print_header("Process interrupted by user", 3)
    except Exception as e:
         print_header("Unexpected error in main loop", 3)
         print(f"\nAn unexpected error occurred in the main loop: {e}")
    finally:
        if driver:
            driver.quit()
            print("WebDriver closed.")

if __name__ == "__main__":
    main()