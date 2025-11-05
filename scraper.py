import requests
from bs4 import BeautifulSoup
import os
from datetime import datetime
from zoneinfo import ZoneInfo  # Handles PST/PDT automatically

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

# Target PT hours
now_utc = datetime.utcnow()
now_pt = now_utc.replace(tzinfo=ZoneInfo("UTC")).astimezone(ZoneInfo("America/Los_Angeles"))

print("DEBUG: UTC hour =", now_utc.hour, "PT hour =", now_pt.hour)

# Force script to run for testing
TARGET_HOURS_PT = [now_pt.hour]

def scrape_numbers():
    url = "https://live.ipms247.com/booking/book-rooms-hollywoodviphotel"  # Replace with your target URL
    r = requests.get(url)
    soup = BeautifulSoup(r.text, 'html.parser')

    # Example: find two numbers using CSS selectors
    num1 = float(soup.select_one('#leftroom_0').text.strip())
    num2 = float(soup.select_one('#leftroom_4').text.strip())

    return num1 + num2

def send_email(total):
    sg = SendGridAPIClient(os.environ['SENDGRID_API_KEY'])
    message = Mail(
        from_email='cherrytop3000@gmail.com',  # Replace with your verified SendGrid sender email
        to_emails=['3104866003@tmomail.net', 'cherrytop3000@gmail.com'],     # Replace with your recipient email
        subject='',
        plain_text_content=f'{total} rooms available'
    )
    response = sg.send(message)
    print(f"Email sent! Status code: {response.status_code}")

if __name__ == "__main__":
    now_pt = datetime.now(ZoneInfo("America/Los_Angeles"))

    if now_pt.hour not in TARGET_HOURS_PT:
        print(f"Current PT hour ({now_pt.hour}) is not a target hour. Exiting.")
        exit(0)

    total = scrape_numbers()
    send_email(total)
    print(f"Run executed at PT {now_pt.hour}:00, total={total}")
