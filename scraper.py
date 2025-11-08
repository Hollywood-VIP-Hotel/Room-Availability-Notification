import os
import requests
from datetime import datetime
from zoneinfo import ZoneInfo

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


# --- Configuration ---
URL = "https://live.ipms247.com/booking/book-rooms-hollywoodviphotel"
TARGET_HOURS_PT = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23]

RECIPIENTS = ["cherrytop3000@gmail.com"]

# --- PST/PDT Time Check ---
pst_now = datetime.now(ZoneInfo("America/Los_Angeles"))
current_hour = pst_now.hour

if current_hour not in TARGET_HOURS_PT:
    print(f"Current PT hour ({current_hour}) is not a target hour. Exiting.")
    exit()


# --- Selenium Setup ---
options = Options()
options.add_argument("--headless=new")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")

driver = webdriver.Chrome(options=options)

try:
    print("Loading page...")
    driver.get(URL)

    wait = WebDriverWait(driver, 20)

    # Wait for the two room elements to appear
    elem1 = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "#leftroom_0")))
    elem2 = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "#leftroom_4")))

    # Wait until both texts are numeric (no placeholders)
    def wait_for_number(element):
        WebDriverWait(driver, 20).until(lambda d: element.text.strip().isdigit())

    wait_for_number(elem1)
    wait_for_number(elem2)

    # Extract numbers
    num1 = int(elem1.text.strip())
    num2 = int(elem2.text.strip())
    total = num1 + num2

    print(f"Final scraped numbers: leftroom_0={num1}, leftroom_4={num2}, total={total}")

finally:
    driver.quit()


# --- Send notification to Make.com webhook ---
message = f"{total} rooms available"
payload = {"value1": message}

webhook_url = os.environ.get("MAKE_WEBHOOK_URL")

if not webhook_url:
    print("Missing MAKE_WEBHOOK_URL environment variable.")
    exit(1)

print("Sending to webhook:", webhook_url)

try:
    response = requests.post(webhook_url, json=payload, timeout=10)

    if response.status_code in (200, 202):
        print("Notification sent to Make webhook successfully!")
    else:
        print(f"Make webhook returned {response.status_code}: {response.text}")

except Exception as e:
    print("Error sending to webhook:", e)
