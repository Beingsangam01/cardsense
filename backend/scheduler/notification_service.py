import os
import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

load_dotenv()

CALLMEBOT_PHONE = os.getenv("CALLMEBOT_PHONE")
CALLMEBOT_APIKEY = os.getenv("CALLMEBOT_APIKEY")
GMAIL_ADDRESS = os.getenv("GMAIL_ADDRESS")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")


# def send_whatsapp(message: str):
#     if not CALLMEBOT_PHONE or not CALLMEBOT_APIKEY:
#         print("WhatsApp not configured — skipping")
#         return False

#     try:
#         url = "https://api.callmebot.com/whatsapp.php"
#         params = {
#             "phone": CALLMEBOT_PHONE,
#             "text": message,
#             "apikey": CALLMEBOT_APIKEY
#         }
#         response = requests.get(url, params=params, timeout=10)
#         if response.status_code == 200:
#             print("WhatsApp message sent successfully")
#             return True
#         else:
#             print(f"WhatsApp failed: {response.text}")
#             return False
#     except Exception as e:
#         print(f"WhatsApp error: {str(e)}")
#         return False


def send_email(subject: str, body: str):
    if not GMAIL_ADDRESS or not GMAIL_APP_PASSWORD:
        print("Email not configured — skipping")
        return False

    try:
        msg = MIMEMultipart()
        msg['From'] = GMAIL_ADDRESS
        msg['To'] = GMAIL_ADDRESS        
        msg['Subject'] = f"CardSense: {subject}"

        msg.attach(MIMEText(body, 'plain'))

        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
            server.send_message(msg)

        print(f"Email sent: {subject}")
        return True

    except Exception as e:
        print(f"Email error: {str(e)}")
        return False
        