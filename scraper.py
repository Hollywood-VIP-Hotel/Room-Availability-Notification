import os
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

# Notify only at 3pm, 6pm, 9pm PT
TARGET_HOURS_PT = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23]

# -------------------------------------------------------------
# Time gating (PST/PDT)
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
wait = WebDriverWait(driver, 30)  # generous wait


try:
    print("[INFO] Loading page...")
    driver.get(URL)

    # ---------------------------------------------------------
    # 1. Wait for booking engine container to appear
    # ---------------------------------------------------------
    print("[INFO] Waiting for booking engine DOM root...")
    wait.until(EC.presence_of_element_located((By.ID, "eZ_BookingRooms")))

    # ---------------------------------------------------------
    # 2. Helper: wait for a room element to contain the final value
    # ---------------------------------------------------------
    def wait_final_value(css_selector):
        """
        Waits until:
        - The element exists
        - The text is numeric
        - The numeric value is < 20 (real inventory values)
        """
        print(f"[INFO] Waiting for final value in {css_selector}...")

        def valid_value(driver):
            try:
                text = driver.find_element(By.CSS_SELECTOR, css_selector).text.strip()
                if text.isdigit() and 0 <= int(text) < 20:
                    return text
                return False
            except:
                return False

        return wait.until(valid_value)

    # ---------------------------------------------------------
    # 3. Get final, correct numbers
    # ---------------------------------------------------------
    num1 = int(wait_final_value("#leftroom_0"))
    num2 = int(wait_final_value("#leftroom_4"))
    total = num1 + num2

    print(f"[SUCCESS] Scraped room numbers: {num1} + {num2} = {total}")

finally:
    driver.quit()


# -------------------------------------------------------------
# Send notification to Make.com webhook
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
        print("[SUCCESS] Notification delivered to Make.com webhook!")
    else:
        print(f"[ERROR] Webhook returned {response.status_code}: {response.text}")

except Exception as e:
    print(f"[ERROR] Failed to send to webhook: {e}")
