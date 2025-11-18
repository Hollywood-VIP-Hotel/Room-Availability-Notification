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

# Half-hour windows centered on these times (Pacific Time)
TARGET_HOURS_PT = [8, 12, 15, 18, 21]   # 8am, 12pm, 3pm, 6pm, 9pm


# -------------------------------------------------------------
# Time gating (Pacific Time)
# -------------------------------------------------------------
pst_now = datetime.now(ZoneInfo("America/Los_Angeles"))
current_hour = pst_now.hour
current_min = pst_now.minute

# We only continue if the time is within ±15 minutes of a target hour
in_window = False
for hour in TARGET_HOURS_PT:
    if current_hour == hour and current_min <= 15:
        in_window = True
    if current_hour == hour - 1 and current_min >= 45:
        in_window = True

if not in_window:
    print(f"[INFO] Current PT time {current_hour}:{current_min:02d} is outside allowed window. Exiting.")
    exit()


# -------------------------------------------------------------
# Selenium setup
#   IMPORTANT:
#   - We DO NOT run headless.
#   - GitHub uses Xvfb virtual display via xvfb-run in workflow.
# -------------------------------------------------------------
options = Options()

options.add_argument("--disable-dev-shm-usage")
options.add_argument("--no-sandbox")

# IMPORTANT — real Chrome desktop user-agent
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
    Extracts a stable numeric availability value.
    If the element never loads (missing room type), return 0 instead of failing.
    """

    print(f"[INFO] Checking for element {css_selector}...")

    # Try to wait for the element to appear
    try:
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, css_selector)))
    except:
        print(f"[WARN] Element {css_selector} not found — treating as 0")
        return 0

    stable_count = 0
    last_value = None

    print(f"[INFO] Waiting for stable numeric value in {css_selector}...")

    for _ in range(30):  # ~30 seconds max
        try:
            text = driver.find_element(By.CSS_SELECTOR, css_selector).text.strip()

            if text.isdigit():
                if last_value is None:
                    last_value = text

                elif text == last_value:
                    stable_count += 1
                    if stable_count >= 2:
                        print(f"[INFO] Stable value detected in {css_selector}: {text}")
                        return int(text)

                else:
                    stable_count = 0
                    last_value = text

        except:
            pass

        time.sleep(1)

    print(f"[WARN] Value did not stabilize for {css_selector}. Using last known: {last_value or 0}")
    return int(last_value or 0)


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
