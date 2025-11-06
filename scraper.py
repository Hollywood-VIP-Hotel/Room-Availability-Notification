import os
import requests
from datetime import datetime
from zoneinfo import ZoneInfo
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

# --------------------------
# Configuration
# --------------------------

# Hours you want to send notifications (PST)
TARGET_HOURS_PT = [15, 18, 21]  # 3pm, 6pm, 9pm PST

# Dynamic date for today
today = datetime.now(ZoneInfo("America/Los_Angeles")).strftime("%m-%d-%Y")

# Payload for POST request (dynamic checkin/ArrvalDt)
PAYLOAD = {
    "checkin": today,
    "gridcolumn": "1",
    "adults": "1",
    "child": "0",
    "nonights": "1",
    "ShowSelectedNights": "true",
    "DefaultSelectedNights": "1",
    "calendarDateFormat": "mm-dd-yy",
    "rooms": "1",
    "ArrvalDt": today,
    "HotelId": "15343",
    "isLogin": "lf",
    "selectedLang": "",
    "modifysearch": "false",
    "layoutView": "2",
    "ShowMinNightsMatchedRatePlan": "false",
    "LayoutTheme": "2",
    "w_showadult": "false",
    "w_showchild_bb": "false",
    "ShowMoreLessOpt": "",
    "w_showchild": "true",
    "ischeckavailabilityclicked": "0"
}

POST_URL = "https://live.ipms247.com/booking/rmdetails"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

# SendGrid configuration
SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
FROM_EMAIL = "cherrytop3000@gmail.com"
TO_EMAILS = ['3104866003@tmomail.net', 'cherrytop3000@gmail.com']

# --------------------------
# Functions
# --------------------------

def scrape_numbers():
    response = requests.post(POST_URL, data=PAYLOAD, headers=HEADERS)
    data = response.json()
    
    # Replace these keys with the actual JSON keys for your numbers
    num1 = float(data["leftroom_0"])
    num2 = float(data["leftroom_4"])
    
    return num1 + num2

def send_email(total):
    message = Mail(
        from_email=FROM_EMAIL,
        to_emails=TO_EMAILS,
        subject="",  # No subject
        plain_text_content=f"{total} rooms available"
    )
    try:
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        sg.send(message)
        print("Email sent successfully!")
    except Exception as e:
        print(f"Error sending email: {e}")

# --------------------------
# Main Execution
# --------------------------

now_pt = datetime.now(ZoneInfo("America/Los_Angeles"))
current_hour = now_pt.hour

print(f"Testing mode — forcing run at {current_hour} PT")
total = scrape_numbers()
send_email(total)
