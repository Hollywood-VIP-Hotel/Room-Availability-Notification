import os
import requests
from datetime import datetime
from zoneinfo import ZoneInfo
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

# --- Configuration ---
URL = "https://live.ipms247.com/booking/book-rooms-hollywoodviphotel"
TARGET_HOURS_PT = [15, 18, 21]

# --- Time check ---
pst_now = datetime.now(ZoneInfo("America/Los_Angeles"))
current_hour = pst_now.hour

if current_hour not in TARGET_HOURS_PT:
    print(f"Current PT hour ({current_hour}) is not a target hour. Exiting.")
    exit()

# --- Scrape numbers ---
options = Options()
options.add_argument("--headless=new")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")

driver = webdriver.Chrome(options=options)

try:
    print("Loading page...")
    driver.get(URL)
    driver.implicitly_wait(5)

    # your updated selectors
    num1 = int(driver.find_element(By.CSS_SELECTOR, "#leftroom_0").text.strip())
    num2 = int(driver.find_element(By.CSS_SELECTOR, "#leftroom_4").text.strip())
    total = num1 + num2

    print(f"Scraped values: {num1}, {num2} | Total: {total}")

finally:
    driver.quit()

# --- Send notification to Make.com webhook ---
message = f"{total} rooms available"

webhook_url = os.environ.get("MAKE_WEBHOOK_URL")
if not webhook_url:
    print("Missing MAKE_WEBHOOK_URL environment variable.")
    exit(1)

payload = {"value1": message}

try:
    response = requests.post(webhook_url, json=payload, timeout=10)

    if response.status_code in (200, 202):
        print("Notification sent to Make webhook!")
    else:
        print(f"Make webhook returned {response.status_code}: {response.text}")

except Exception as e:
    print("Error sending to webhook:", e)
