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
TARGET_HOURS_PT = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23]

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
# -------------------------------------------------------------
options = Options()
options.add_argument("--headless=new")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")

driver = webdriver.Chrome(options=options)
wait = WebDriverWait(driver, 30)


try:
    print("[INFO] Loading page...")
    driver.get(URL)

    # ---------------------------------------------------------
    # Wait for the booking engine root container
    # ---------------------------------------------------------
    print("[INFO] Waiting for booking engine container...")
    wait.until(EC.presence_of_element_located((By.ID, "eZ_BookingRooms")))

    # ---------------------------------------------------------
    # Helper: wait for value stabilization
    # ---------------------------------------------------------
    def get_stable_value(css_selector):
        """
        Waits for the room availability number to:
        - exist
        - be numeric
        - stabilize (same value twice in a row)
        """
        print(f"[INFO] Waiting for stable value in {css_selector}...")

        # Step 1: wait for element
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, css_selector)))

        # Step 2: wait for it to become numeric
        def is_numeric(driver):
            try:
                t = driver.find_element(By.CSS_SELECTOR, css_selector).text.strip()
                return t.isdigit()
            except:
                return False

        wait.until(is_numeric)

        # Step 3: wait for stabilization — most important fix
        stable_count = 0
        last_value = None

        for _ in range(20):  # up to ~20 seconds
            try:
                text = driver.find_element(By.CSS_SELECTOR, css_selector).text.strip()
                if text.isdigit():
                    if text == last_value:
                        stable_count += 1
                        if stable_count >= 2:  # stable two consecutive reads
                            print(f"[INFO] Stable value detected for {css_selector}: {text}")
                            return int(text)
                    else:
                        stable_count = 0
                        last_value = text
                time.sleep(1)
            except:
                time.sleep(1)

        # Fallback if not stabilized (rare)
        print(f"[WARN] Could not detect full stabilization. Using last seen value: {last_value}")
        return int(last_value)


    # ---------------------------------------------------------
    # Extract FINAL correct values
    # ---------------------------------------------------------
    num1 = get_stable_value("#leftroom_0")
    num2 = get_stable_value("#leftroom_4")
    total = num1 + num2

    print(f"[SUCCESS] FINAL ROOM AVAILABILITY: {num1} + {num2} = {total}")

finally:
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
        print("[SUCCESS] Notification sent!")
    else:
        print(f"[ERROR] Webhook error {response.status_code}: {response.text}")

except Exception as e:
    print(f"[ERROR] Failed to send webhook: {e}")
