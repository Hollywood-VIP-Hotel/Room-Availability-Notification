import os
import time
import requests
from datetime import datetime
from zoneinfo import ZoneInfo

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


# -------------------------------------------------------------
# Configuration
# -------------------------------------------------------------
URL = "https://live.ipms247.com/booking/book-rooms-hollywoodviphotel"

# Only send notifications at 3pm, 6pm, 9pm PT
TARGET_HOURS_PT = [15, 18, 21]


# -------------------------------------------------------------
# Time gating (Pacific Time)
# -------------------------------------------------------------
pst_now = datetime.now(ZoneInfo("America/Los_Angeles"))
current_hour = pst_now.hour

if current_hour not in TARGET_HOURS_PT:
    print(f"[INFO] Current PT hour ({current_hour}) is not a target hour. Exiting.")
    exit()


# -------------------------------------------------------------
# Selenium setup
#   IMPORTANT:
#   - We DO NOT run headless.
#   - GitHub uses Xvfb virtual display via xvfb-run in workflow.
# -------------------------------------------------------------
options = Options()

# DO NOT USE HEADLESS MODE — booking engine blocks it
# options.add_argument("--headless=new")

options.add_argument("--disable-dev-shm-usage")
options.add_argument("--no-sandbox")

# VERY IMPORTANT — use a real Chrome desktop user-agent
options.add_argument(
    "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

driver = webdriver.Chrome(options=options)
wait = WebDriverWait(driver, 30)


# -------------------------------------------------------------
# Load page and wait for booking engine root container
# -------------------------------------------------------------
try:
    print("[INFO] Loading page...")
    driver.get(URL)

    print("[INFO] Waiting for booking engine container (#eZ_BookingRooms)...")
    wait.until(EC.presence_of_element_located((By.ID, "eZ_BookingRooms")))

    # Give the booking engine time to finish JS initialization
    print("[INFO] Waiting additional 3 seconds for JS scripts...")
    time.sleep(3)

except Exception as e:
    print("[ERROR] Could not load initial page or container:", e)
    driver.quit()
    exit(1)


# -------------------------------------------------------------
# Wait for stable numeric values
# -------------------------------------------------------------
def get_stable_value(css_selector):
    """
    Extracts the FINAL room availability by:
    - Waiting for the span to exist
    - Waiting until it contains numbers
    - Waiting until the number stops changing (stabilizes)
    """
    print(f"[INFO] Waiting for element {css_selector} to appear...")
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, css_selector)))

    stable_count = 0
    last_value = None

    print(f"[INFO] Waiting for stable numeric value in {css_selector}...")

    for _ in range(30):  # up to ~30 seconds
        try:
            text = driver.find_element(By.CSS_SELECTOR, css_selector).text.strip()

            if text.isdigit():
                # First numeric value
                if last_value is None:
                    last_value = text
                # If it stops changing, we found the real value
                elif text == last_value:
                    stable_count += 1
                    if stable_count >= 2:  # stable for 2 seconds
                        print(f"[INFO] Stable value detected in {css_selector}: {text}")
                        return int(text)
                else:
                    # Reset stability counter
                    stable_count = 0
                    last_value = text

        except:
            pass

        time.sleep(1)

    # Fallback if never stabilized
    print(f"[WARN] Value did not stabilize for {css_selector}. Using last known: {last_value}")
    return int(last_value)


# -------------------------------------------------------------
# Extract FINAL room availability values
# -------------------------------------------------------------
num1 = get_stable_value("#leftroom_0")
num2 = get_stable_value("#leftroom_4")
num3 = get_stable_value("#leftroom_6")
total = num1 + num2 + num3

print(f"[SUCCESS] FINAL ROOM AVAILABILITY: {num1} + {num2} + {num3} = {total}")


# Close browser
driver.quit()


# -------------------------------------------------------------
# Send notification to Make webhook
# -------------------------------------------------------------
webhook_url = os.environ.get("MAKE_WEBHOOK_URL")

if not webhook_url:
    print("[ERROR] Missing MAKE_WEBHOOK_URL environment variable.")
    exit(1)

payload = {"value1": f"{total} rooms available"}

print("[INFO] Sending to Make webhook...")

try:
    response = requests.post(webhook_url, json=payload, timeout=15)

    if response.status_code in (200, 202):
        print("[SUCCESS] Notification sent to Make webhook!")
    else:
        print(f"[ERROR] Webhook error {response.status_code}: {response.text}")

except Exception as e:
    print(f"[ERROR] Failed to send webhook: {e}")
