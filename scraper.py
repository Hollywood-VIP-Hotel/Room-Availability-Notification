import os
import requests
from datetime import datetime
from zoneinfo import ZoneInfo
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

# --- Configuration ---
URL = "https://live.ipms247.com/booking/book-rooms-hollywoodviphotel"
TARGET_HOURS_PT = [15, 18, 21]  # 3pm, 6pm, 9pm PT
FROM_EMAIL = "Mailgun Sandbox <postmaster@YOUR_SANDBOX_DOMAIN.mailgun.org>"  # replace with yours
TO_EMAILS = ["recipient1@example.com", "recipient2@example.com"]

# --- Time check for PST/PDT ---
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

    num1 = int(driver.find_element(By.CSS_SELECTOR, "#leftroom_0").text.strip())
    num2 = int(driver.find_element(By.CSS_SELECTOR, "#rightroom_0").text.strip())
    total = num1 + num2
    print(f"Scraped values: {num1}, {num2} | Total: {total}")

finally:
    driver.quit()

# --- Send email via Mailgun ---
MAILGUN_API_KEY = os.environ.get("MAILGUN_API_KEY")
MAILGUN_DOMAIN = os.environ.get("MAILGUN_DOMAIN")  # e.g. sandbox12345.mailgun.org or your own domain

if not MAILGUN_API_KEY or not MAILGUN_DOMAIN:
    print("Mailgun credentials missing. Exiting.")
    exit(1)

subject = f"Hollywood VIP Hotel Rooms — {total} available"
html_content = f"""
<h2>Room Availability Update</h2>
<p><strong>Total rooms available:</strong> {total}</p>
<p>Scraped at {pst_now.strftime('%Y-%m-%d %I:%M %p %Z')}</p>
"""

try:
    response = requests.post(
        f"https://api.mailgun.net/v3/{MAILGUN_DOMAIN}/messages",
        auth=("api", MAILGUN_API_KEY),
        data={
            "from": FROM_EMAIL,
            "to": TO_EMAILS,
            "subject": subject,
            "html": html_content,
        },
    )
    if response.status_code == 200:
        print("Email sent successfully.")
    else:
        print(f"Mailgun responded with {response.status_code}: {response.text}")
except Exception as e:
    print("Error sending email:", e)
