import sys
import io
import os
import time
import traceback
import json
import pyautogui
import re
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from dotenv import load_dotenv, find_dotenv

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

# Load environmen variables from .env file
dotenv_path = find_dotenv()
load_dotenv(dotenv_path)

# Get  and password from environment variables
#username = os.getenv('NAME')
#password = os.getenv('PASSWORD')

# Force reload environment variables
#os.environ['USERNAME'] = username
#os.environ['PASSWORD'] = password


subject_mapping = {
    #Krav Fag
    "kemB": "Kemi",
    "samfC": "Samfundsfag",
    "engB": "Engelsk",
    "bioC": "Biologi",
    "fysB": "Fysik",
    "stud.akt": "Studieaktivitet",
    "and.uv.": "Studieaktivitet",
    "kitC": "KIT",
    "matA": "Matematik",
    "matB": "Matematik",
    "teknoB": "Teknologi",
    "daA": "Dansk",

    #HTX
    "KemA": "Kemi",
    "teknoA": "Teknologi",
    "engA": "Engelsk",
    "bioB": "Biologi",
    "kitA": "KIT",
    "fysA": "Fysik",
    "idehiB": "Idehistorie",

    #Valgfag HTX
    "VprogrC": "Programmering",
    "VprogrB": "Programmering",
    "VfilosC": "Filosofi",
    "VpsykC": "Psykologi",
    "Vdes&arC": "Design & Arkitektur",
    "Vdes&arB": "Design & Arkitektur",
    "VdesignB": "Design",
    "VdesignC": "Design",
    "VkemiA": "Kemi",
    "VengA1": "Engelsk",
    "VengA2": "Engelsk",
    "TproctA2": "Proces Teknologi",
    "TproctA1": "Proces Teknologi",
    "TmasktA1": "Maskine Teknologi",
    "TmasktA2": "Maskine Teknologi",
    "VmatA": "Matematik",
    "VidrætB": "Idræt",
    "VidrætC": "Idræt",
    "VsamfB": "Samfundsfag",
    "VmusikC": "Musik",
    "VteknA": "Teknologi",
    "VfysA": "Fysik",
    "TeltA2": "EL",
    "TeltA1": "EL",
    "TbygtA": "Bygge Teknologi",
    "TtekstA2": "Tekstil Teknologi",
    "TtekstA1": "Tekstil Teknologi",
    }

def setup_driver():
    opts = webdriver.ChromeOptions()
    # Headless in containers:
    #opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    # (Optional) make it a bit more robust in CI:
    opts.add_argument("--window-size=1280,800")
    opts.add_argument("--remote-debugging-port=9222")

    # IMPORTANT: do NOT pass a Service(path=...) on Render.
    # Let Selenium Manager fetch Chrome for Testing + matching driver.
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=opts)
    return driver

def login(driver, wait, username: str, password: str):
    driver.get("https://ludus.sde.dk/samllogin")

    try:
        # Wait for the main page to load
        wait.until(EC.presence_of_element_located((By.CLASS_NAME, "mainapp")))
        
        # Click "ADLogin"
        button1 = wait.until(EC.element_to_be_clickable((By.XPATH, "//div[@role='button' and .//span[text()='ADLogin']]")))
        button1.click()

        # Click "Active Directory"
        button2 = wait.until(EC.element_to_be_clickable((By.XPATH, "//span[@class='largeTextNoWrap indentNonCollapsible' and text()='Active Directory']")))
        button2.click()

        # Try to find the standard login form
        username_field = wait.until(EC.presence_of_element_located((By.ID, "userNameInput")))
        password_field = wait.until(EC.presence_of_element_located((By.ID, "passwordInput")))
        
        # If found, proceed with the standard login method
        username_field.send_keys(username)
        password_field.send_keys(password)
        button3 = wait.until(EC.presence_of_element_located((By.ID, "submitButton")))
        button3.click()
        print("Standard login form detected and filled.")

    except:
        print("Standard login form not found. Checking for popup authentication...")

        # Wait briefly to allow the popup to appear
        time.sleep(0.5)

        # Use PyAutoGUI to interact with the Windows authentication popup
        pyautogui.write(username)
        pyautogui.press("tab")
        pyautogui.write(password)
        pyautogui.press("enter")

        print("Popup login handled successfully.")

def calculate_dates(week_number):
    today = datetime.now()
    start_of_week = today - timedelta(days=today.weekday())  # Monday of current week
    start_of_week += timedelta(weeks=week_number - 1)
    days_of_week = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    date_mapping = {day: (start_of_week + timedelta(days=i)).strftime("%Y-%m-%d") for i, day in enumerate(days_of_week)}
    return date_mapping

def extract_messages(driver, wait):
    try:
        table_rows = wait.until(
            EC.visibility_of_all_elements_located(
                (By.XPATH, "//div[@class='v-scrollable v-table-body-wrapper v-table-body']//tr[contains(@class, 'v-table-row')]")
            )
        )
        messages = []
        for index, row in enumerate(table_rows):
            try:
                # Extract date and initials from the row before clicking
                date_element = row.find_element(By.XPATH, ".//td[@class='v-table-cell-content' and contains(@style, 'width: 86px')]//div[@class='v-table-cell-wrapper']")
                initials_element = row.find_element(By.XPATH, ".//td[@class='v-table-cell-content' and contains(@style, 'width: 63px')]//div[@class='v-table-cell-wrapper']")

                message_date = date_element.text.strip() if date_element else None
                raw_initials = initials_element.text.strip() if initials_element else None
                message_initials_email = f"{raw_initials}@otg.dk" if raw_initials else None

                # Click the row to view the full content
                wait.until(EC.element_to_be_clickable(row)).click()
                content_container = wait.until(EC.presence_of_element_located((By.CLASS_NAME, "v-panel-content-light")))
                time.sleep(0.25)
                text_elements = content_container.find_elements(By.XPATH, ".//div[contains(@class, 'v-label')]")
                panel_text = "\n".join([element.text for element in text_elements if element.text.strip()])

                messages.append({
                    "index": index + 1,
                    "time": message_date,
                    "initials": raw_initials,  # Save raw initials
                    "email": message_initials_email,  # Save email version of initials
                    "content": panel_text
                })

                # Uncomment the next line if you want to print each message for debugging
                # print(f"Message {index + 1}: {panel_text}")

            except Exception as e:
                print(f"Failed to extract content for row {index + 1}: {e}")

        save_json("messages_output.json", messages)

    except Exception as e:
        print(f"Failed to extract messages: {e}")

def navigate_to_schedule(driver, wait):
    try:
        #pyautogui.press("esc")
        wait.until(EC.presence_of_element_located((By.CLASS_NAME, "v-absolutelayout-wrapper-ugeskema-skemabrik-element")))
        print("Navigated to schedule successfully.")
    except Exception as e:
        print(f"Failed to navigate to schedule: {e}")
        save_debug_page(driver, "debug_schedule_page.html")

def extract_schedule(driver, wait, max_pages=15):
    all_schedules = {}

    for page in range(max_pages):
        try:
            # Calculate the start of the week (Monday) for the current page
            today = datetime.now()
            start_of_week = today - timedelta(days=today.weekday()) + timedelta(weeks=page)
            actual_week_number = start_of_week.isocalendar()[1]
            days_of_week = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
            date_mapping = {
                day: (start_of_week + timedelta(days=i)).strftime("%Y-%m-%d")
                for i, day in enumerate(days_of_week)
            }

            schedule_by_date = {date: [] for date in date_mapping.values()}

            # Fetch all schedule blocks on the current page
            schedule_blocks = wait.until(EC.presence_of_all_elements_located(
                (By.XPATH, "//div[contains(@class, 'v-absolutelayout-wrapper')]")
            ))

            for block_index, block in enumerate(schedule_blocks):
                try:
                    # Determine the day based on the left percentage in the style attribute
                    style = block.get_attribute("style")
                    left_value = style.split("left: ")[1].split("%")[0].strip()
                    left_percentage = float(left_value)

                    day_ranges = {
                        "Monday": (0, 20),
                        "Tuesday": (20, 40),
                        "Wednesday": (40, 60),
                        "Thursday": (60, 80),
                        "Friday": (80, 100),
                    }

                    day_name = "Unknown Day"
                    for name, (low, high) in day_ranges.items():
                        if low <= left_percentage < high:
                            day_name = name
                            break

                    date = date_mapping.get(day_name, "Unknown Date")

                    if "ugeskema-tyrkis-element" in block.get_attribute("class"):
                        try:
                            title_element = block.find_elements(By.XPATH, ".//b")
                            title = title_element[0].text.strip() if title_element else "Ukendt eksamen"

                            # Use JS to reliably get text content even if .text fails
                            time_elements = block.find_elements(By.XPATH, ".//div[contains(@class, 'v-label-small') and (contains(text(), '-') or contains(text(), '–'))]")
                            time_text = None
                            if time_elements:
                                time_text = driver.execute_script("return arguments[0].textContent;", time_elements[0]).strip()

                            # Use regex to extract valid time
                            start_time = end_time = None
                            if time_text:
                                match = re.search(r"(\d{2}:\d{2})\s*[-–]\s*(\d{2}:\d{2})", time_text)
                                if match:
                                    start_time = f"{match.group(1)}:00"
                                    end_time = f"{match.group(2)}:00"

                            room_elements = block.find_elements(By.XPATH, ".//div[contains(text(), 'MU')]")
                            rooms = [el.text.strip() for el in room_elements if el.text.strip()] if room_elements else []

                            schedule_by_date[date].append({
                                "subject": "Eksamen",
                                "title": title,
                                "start_time": start_time,
                                "end_time": end_time,
                                "rooms": rooms,
                                "type": "exam"
                            })

                            continue
                        except Exception as e:
                            print(f"Failed to process exam block {block_index + 1}: {e}")
                            continue
                        
                        

                    # Check if block is a special event block like "Undervisningsfri"
                    if "ugeskema-begivenhed-element" in block.get_attribute("class"):
                        try:
                            # Extract the title (e.g., "Undervisningsfri", "Forberedelse", etc.)
                            title_element = block.find_element(By.XPATH, ".//span[@class='v-button-caption']")
                            title = title_element.text.strip()

                            # Extract the time string (e.g., "08:00 - 09:45")
                            time_element = block.find_element(By.XPATH, ".//div[contains(@class, 'v-label-small') and contains(text(), '-')]")
                            time_str = time_element.text.strip()

                            # Parse time string into start and end
                            start_time = end_time = None
                            match = re.search(r"(\d{2}:\d{2})\s*[-–]\s*(\d{2}:\d{2})", time_str)
                            if match:
                                start_time = f"{match.group(1)}:00"
                                end_time = f"{match.group(2)}:00"

                            schedule_by_date[date].append({
                                "subject": title,
                                "start_time": start_time,
                                "end_time": end_time,
                                "room": None,
                                "teacher_initials": None,
                                "notes": None,
                            })

                            continue  # Skip further processing for this block
                        except Exception as e:
                            print(f"Failed to process special event block {block_index + 1}: {e}")
                            continue

                    # Process a regular schedule block
                    raw_subject = block.find_element(By.CLASS_NAME, "v-label-text-ellipsis").text.strip() \
                        if block.find_elements(By.CLASS_NAME, "v-label-text-ellipsis") else None
                    if not raw_subject:
                        continue

                    short_subject = raw_subject.split(" ")[-1]
                    subject = subject_mapping.get(short_subject, short_subject)

                    time_text = block.find_element(By.XPATH, ".//div[contains(@class, 'v-label-small') and contains(text(), '-')]").text.strip()

                    # Split "08:00 - 09:45" → "08:00", "09:45"
                    try:
                        start_raw, end_raw = [t.strip() for t in time_text.split("-")]
                        # Add :00 to match SQL 'time' format
                        start_time = f"{start_raw}:00" if len(start_raw) == 5 else start_raw
                        end_time = f"{end_raw}:00" if len(end_raw) == 5 else end_raw
                    except Exception:
                        print(f"Failed to parse time string '{time_text}'")
                        start_time = None
                        end_time = None

                    room = block.find_element(By.XPATH, ".//div[contains(@class, 'v-label-small') and contains(text(), 'MU')]").text.strip() \
                        if block.find_elements(By.XPATH, ".//div[contains(@class, 'v-label-small') and contains(text(), 'MU')]") else None
                    initials = block.find_element(By.XPATH, ".//div[contains(@class, 'v-label-small')]/u").text.strip() \
                        if block.find_elements(By.XPATH, ".//div[contains(@class, 'v-label-small')]/u") else None

                    # Check for any notes
                    notes = None
                    try:
                        notes_button = block.find_element(By.XPATH, ".//div[@role='button' and contains(@class, 'v-button-link') and .//img[contains(@src, 'note.gif')]]")
                        notes_button.click()

                        # Wait for the notes UI to open and extract text
                        notes_container = wait.until(EC.presence_of_element_located((By.CLASS_NAME, "v-panel-content")))
                        notes_text = notes_container.find_element(By.CLASS_NAME, "v-label").text.strip()
                        notes = notes_text

                        # Close the notes UI
                        driver.find_element(By.XPATH, "//div[@role='button' and contains(@class, 'v-window-closebox')]").click()
                    except Exception:
                        print(f"Block {block_index + 1}: No notes found for subject {subject}.")

                    schedule_by_date[date].append({
                        "subject": subject,
                        "start_time": start_time,
                        "end_time": end_time,
                        "room": room,
                        "teacher_initials": initials,
                        "notes": notes,
                    })

                except Exception as e:
                    print(f"Failed to process block {block_index + 1} on page {page + 1}: {e}")

            # If no entries were added for this week, skip saving it and go to the next
            if not any(schedule_by_date.values()):
                print(f"Week {actual_week_number} appears to be empty. Skipping...")
                if page < max_pages - 1:
                    try:
                        next_button = wait.until(EC.element_to_be_clickable(
                            (By.XPATH, "//div[@role='button' and contains(@class, 'v-button-link') and .//img[contains(@src, 'arrow-right.png')]]")
                        ))
                        next_button.click()
                        wait.until(EC.staleness_of(schedule_blocks[0]))
                        continue  # Skip saving and continue to the next week
                    except Exception as e:
                        print(f"Failed to click next for empty week {actual_week_number}: {e}")
                        break
                else:
                    break
            else: 
                all_schedules[f"Week {actual_week_number}"] = {k: v for k, v in schedule_by_date.items() if v}

            # Navigate to the next page if applicable
            if page < max_pages - 1:
                try:
                    next_button = wait.until(EC.element_to_be_clickable(
                        (By.XPATH, "//div[@role='button' and contains(@class, 'v-button-link') and .//img[contains(@src, 'arrow-right.png')]]")
                    ))
                    next_button.click()
                    wait.until(EC.staleness_of(schedule_blocks[0]))
                except Exception as e:
                    print(f"Failed to click the next button on page {page + 1}: {e}")
                    break
        except Exception as e:
            print(f"Failed to extract schedule on page {page + 1}: {e}")
            break

    # Wrap extracted schedule in the required format for "1 B"
    formatted_schedule = {
        "classes": {
            "2 B": {
                "schedule": all_schedules  # The extracted schedules are now stored inside "1 B"
            }
        }
    }

    # Save the structured JSON output
    with open("schedule_output.json", "w", encoding="utf-8") as file:
        json.dump(formatted_schedule, file, ensure_ascii=False, indent=4)

def get_day_from_style(style):
    left_value = style.split("left: ")[1].split(";")[0].strip()
    left_percentage = float(left_value.strip('%'))
    day_mapping = {
        0: "Monday",
        20: "Tuesday",
        40: "Wednesday",
        60: "Thursday",
        80: "Friday"
    }
    return day_mapping.get(left_percentage, "Unknown Day")

def extract_schedule_details(block):
    raw_subject = block.find_element(By.CLASS_NAME, "v-label-text-ellipsis").text.strip()
    short_subject = raw_subject.split(" ")[-1]
    subject = subject_mapping.get(short_subject, short_subject)
    time_element = block.find_element(By.XPATH, ".//div[contains(@class, 'v-label-small') and contains(text(), '-')]")
    time = time_element.text.strip()
    room_element = block.find_element(By.XPATH, ".//div[contains(@class, 'v-label-small') and contains(text(), 'MU')]")
    room = room_element.text.strip()
    initials_element = block.find_element(By.XPATH, ".//div[contains(@class, 'v-label-small')]/u")
    initials = initials_element.text.strip()
    return subject, time, room, initials

def click_next_button(driver, wait, schedule_blocks):
    try:
        next_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//div[@role='button' and contains(@class, 'v-button-link') and .//img[contains(@src, 'arrow-right.png')]]")))
        next_button.click()
        wait.until(EC.staleness_of(schedule_blocks[0]))
        print("Clicked the next button.")
        return True
    except Exception as e:
        print(f"Failed to click the next button: {e}")
        return False

def save_json(filename, data):
    with open(filename, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=4)

def save_debug_page(driver, filename):
    with open(filename, "w", encoding="utf-8") as f:
        f.write(driver.page_source)

def main():
    try:
        driver = setup_driver()
        wait = WebDriverWait(driver, 20)
        login(driver, wait)
        extract_messages(driver, wait)
        navigate_to_schedule(driver, wait)
        extract_schedule(driver, wait)
    except Exception as e:
        print("An error occurred:")
        traceback.print_exc()
    finally:
        driver.quit()

if __name__ == "__main__":
    main()