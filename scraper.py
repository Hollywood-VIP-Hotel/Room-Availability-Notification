import os
import time
import requests
from datetime import datetime, time as dtime
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

# Half-hour windows around target times (PT)
WINDOWS_PT = [
    (dtime(7, 45), dtime(8, 15)),
    (dtime(11, 45), dtime(12, 15)),
    (dtime(14, 45), dtime(15, 15)),
    (dtime(17, 45), dtime(18, 15)),
    (dtime(20, 45), dtime(21, 15)),
]

LAST_SENT_FILE = "/tmp/room_notify_last_window.txt"


# -------------------------------------------------------------
# Helper to check if now is inside a window
# -------------------------------------------------------------
def in_window(now):
    for start, end in WINDOWS_PT:
        if start <= now.timetz() <= end:
            return f"{start}-{end}"  # return window ID
    return None


# -------------------------------------------------------------
# Time gating logic
# -------------------------------------------------------------
pst_now = datetime.now(ZoneInfo("America/Los_Angeles"))
current_window = in_window(pst_now)

if not current_window:
    print(f"[INFO] Current PT time ({pst_now.time()}) is outside all send windows. Exiting.")
    exit()

# Check if this window has already sent
if os.path.exists(LAST_SENT_FILE):
    with open(LAST_SENT_FILE, "r") as f:
        last_sent_window = f.read().strip()
else:
    last_sent_window = ""

if last_sent_window == current_window:
    print(f"[INFO] Already sent notification for window {current_window}. Exiting.")
    exit()

print(f"[INFO] Inside allowed window: {current_window}")


# -------------------------------------------------------------
# Selenium setup
# -------------------------------------------------------------
options = Options()

options.add_argument("--disable-dev-shm-usage")
options.add_argument("--no-sandbox")
options.add_argument(
    "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

driver = webdriver.Chrome(options=options)
wait = WebDriverWait(driver, 30)


# -------------------------------------------------------------
# Load page
# -------------------------------------------------------------
try:
    print("[INFO] Loading page...")
    driver.get(URL)

    print("[INFO] Waiting for booking engine container (#eZ_BookingRooms)...")
    wait.until(EC.presence_of_element_located((By.ID, "eZ_BookingRooms")))

    print("[INFO] Waiting additional 3 seconds for JS scripts...")
    time.sleep(3)

except Exception as e:
    print("[ERROR] Could not load initial page or container:", e)
    driver.quit()
    exit(1)


# -------------------------------------------------------------
# Room scraping
# -------------------------------------------------------------
def get_stable_value(css_selector):
    print(f"[INFO] Checking for element {css_selector}...")

    try:
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, css_selector)))
    except:
        print(f"[WARN] Element {css_selector} not found — treating as 0")
        return 0

    stable_count = 0
    last_value = None

    print(f"[INFO] Waiting for stable numeric value in {css_selector}...")

    for _ in range(30):
        try:
            text = driver.find_element(By.CSS_SELECTOR, css_selector).text.strip()

            if text.isdigit():
                if last_value is None:
                    last_value = text
                elif text == last_value:
                    stable_count += 1
                    if stable_count >= 2:
                        print(f"[INFO] Stable value in {css_selector}: {text}")
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
# Extract availability
# -------------------------------------------------------------
num1 = get_stable_value("#leftroom_0")
num2 = get_stable_value("#leftroom_4")
num3 = get_stable_value("#leftroom_6")
total = num1 + num2 + num3

print(f"[SUCCESS] FINAL ROOM AVAILABILITY: {num1} + {num2} + {num3} = {total}")

driver.quit()


# -------------------------------------------------------------
# Send notification
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

        # mark window as sent
        with open(LAST_SENT_FILE, "w") as f:
            f.write(current_window)

    else:
        print(f"[ERROR] Webhook error {response.status_code}: {response.text}")

except Exception as e:
    print(f"[ERROR] Failed to send webhook: {e}")
