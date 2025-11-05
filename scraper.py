import requests
from bs4 import BeautifulSoup
import os
from datetime import datetime
from zoneinfo import ZoneInfo  # Handles PST/PDT automatically

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from twilio.rest import Client

# Target PT hours
TARGET_HOURS_PT = [15, 18, 21]  # 3 PM, 6 PM, 9 PM

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
        from_email='your_email@example.com',
        to_emails='recipient@example.com',
        subject='Room Availability Notification',
        plain_text_content=f'{total} rooms available'
    )
    sg.send(message)

def send_sms(total):
    client = Client(os.environ['TWILIO_SID'], os.environ['TWILIO_AUTH_TOKEN'])
    client.messages.create(
        body=f"The total is {total}",
        from_=os.environ['TWILIO_PHONE'],
        to=os.environ['RECIPIENT_PHONE']
    )

if __name__ == "__main__":
    now_pt = datetime.now(ZoneInfo("America/Los_Angeles"))

    if now_pt.hour not in TARGET_HOURS_PT:
        print(f"Current PT hour ({now_pt.hour}) is not a target hour. Exiting.")
        exit(0)

    total = scrape_numbers()
    send_email(total)
    # send_sms(total)  # Uncomment if SMS is needed
    print(f"Run executed at PT {now_pt.hour}:00, total={total}")
