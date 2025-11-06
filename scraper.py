import os
from datetime import datetime
from zoneinfo import ZoneInfo
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

# --- Configuration ---
URL = "https://live.ipms247.com/booking/book-rooms-hollywoodviphotel"
TARGET_HOURS_PT = [15, 18, 21]  # 3pm, 6pm, 9pm PST
FROM_EMAIL = "cherrytop3000@gmail.com"
TO_EMAILS = ['3104866003@tmomail.net', 'cherrytop3000@gmail.com']  # can be a list

# --- Check current PST hour ---
pst_now = datetime.now(ZoneInfo("America/Los_Angeles"))
current_hour = pst_now.hour

if current_hour not in TARGET_HOURS_PT:
    print(f"Current PT hour ({current_hour}) is not a target hour. Exiting.")
    exit()

# --- Scrape the numbers ---
options = Options()
options.add_argument("--headless=new")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
driver = webdriver.Chrome(options=options)

try:
    print("Loading page...")
    driver.get(URL)
    driver.implicitly_wait(5)  # wait for page to load / JS to render

    # Update these selectors to match the numbers on the page
    num1 = int(driver.find_element(By.CSS_SELECTOR, "#leftroom_0").text.strip())
    num2 = int(driver.find_element(By.CSS_SELECTOR, "#leftroom_4").text.strip())
    total = num1 + num2
    print(f"Scraped values: {num1}, {num2} | Total: {total}")

finally:
    driver.quit()

# --- Send email ---
message = Mail(
    from_email=FROM_EMAIL,
    to_emails=TO_EMAILS,
    subject="",  # empty if you want no subject
    html_content=f"<strong>{total} rooms available</strong>"
)

try:
    sg = SendGridAPIClient(os.environ.get("SENDGRID_API_KEY"))
    response = sg.send(message)
    print("Email sent successfully, status code:", response.status_code)
except Exception as e:
    print("Error sending email:", e)
