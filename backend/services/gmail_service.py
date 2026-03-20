import os
import base64
import pickle
from datetime import datetime, timedelta
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from dotenv import load_dotenv

load_dotenv()

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
CREDENTIALS_PATH = os.path.join(BACKEND_DIR, '..', 'credentials.json')
TOKEN_PATH = os.path.join(BACKEND_DIR, '..', 'token.pickle')


def get_gmail_service():

    creds = None

    if os.path.exists(TOKEN_PATH):
        with open(TOKEN_PATH, 'rb') as token:
            creds = pickle.load(token)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                CREDENTIALS_PATH, SCOPES
            )
            creds = flow.run_local_server(port=0)

        with open(TOKEN_PATH, 'wb') as token:
            pickle.dump(creds, token)

    return build('gmail', 'v1', credentials=creds)


def search_statement_emails(service, email_sender: str, days_back: int = 45):

    after_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y/%m/%d')

    query = f'from:{email_sender} after:{after_date} has:attachment'

    try:
        result = service.users().messages().list(
            userId='me',
            q=query,
            maxResults=5   
        ).execute()

        messages = result.get('messages', [])
        print(f"Found {len(messages)} emails from {email_sender}")
        return messages

    except Exception as e:
        print(f"Error searching emails from {email_sender}: {str(e)}")
        return []


def get_email_details(service, message_id: str):

    try:
        message = service.users().messages().get(
            userId='me',
            id=message_id,
            format='full'
        ).execute()

        headers = message['payload'].get('headers', [])
        subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
        date_str = next((h['value'] for h in headers if h['name'] == 'Date'), '')

        return {
            'id': message_id,
            'subject': subject,
            'date': date_str,
            'payload': message['payload']
        }

    except Exception as e:
        print(f"Error getting email details: {str(e)}")
        return None


def download_pdf_attachment(service, message_id: str, save_path: str):

    try:
        message = service.users().messages().get(
            userId='me',
            id=message_id,
            format='full'
        ).execute()

        parts = get_email_parts(message['payload'])

        for part in parts:
            filename = part.get('filename', '')
            mime_type = part.get('mimeType', '')

            if filename.endswith('.pdf') or 'pdf' in mime_type.lower():
                if 'data' in part.get('body', {}):
                    data = part['body']['data']
                else:
                    attachment_id = part['body']['attachmentId']
                    attachment = service.users().messages().attachments().get(
                        userId='me',
                        messageId=message_id,
                        id=attachment_id
                    ).execute()
                    data = attachment['data']

                pdf_data = base64.urlsafe_b64decode(data)

                os.makedirs(os.path.dirname(save_path), exist_ok=True)
                with open(save_path, 'wb') as f:
                    f.write(pdf_data)

                print(f"Downloaded PDF: {filename} → {save_path}")
                return save_path

        print(f"No PDF attachment found in email {message_id}")
        return None

    except Exception as e:
        print(f"Error downloading attachment: {str(e)}")
        return None


def get_email_parts(payload):
    parts = []

    if 'parts' in payload:
        for part in payload['parts']:
            parts.extend(get_email_parts(part))
    else:
        parts.append(payload)

    return parts