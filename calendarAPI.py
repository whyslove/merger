from __future__ import print_function

import os.path
import pickle
from threading import RLock

from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from datetime import datetime, timedelta

lock = RLock()

SCOPES = 'https://www.googleapis.com/auth/calendar'
"""
Setting up calendar
"""
creds = None
token_path = '.creds/tokenCalendar.pickle'
creds_path = '.creds/credentials.json'

if os.path.exists(token_path):
    with open(token_path, 'rb') as token:
        creds = pickle.load(token)
if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    else:
        flow = InstalledAppFlow.from_client_secrets_file(
            creds_path, SCOPES)
        creds = flow.run_local_server(port=0)
    with open(token_path, 'wb') as token:
        pickle.dump(creds, token)

calendar_service = build('calendar', 'v3', credentials=creds)


def add_attachment(calendar_id: str, event_id: str, file_id: str) -> None:
    """
    Adds url of drive file 'file_id' to calendar event 'event_id'
    """
    with lock:
        event = calendar_service.events().get(
            calendarId=calendar_id, eventId=event_id).execute()
        description = event.get('description', '') + \
            f"\nhttps://drive.google.com/a/auditory.ru/file/d/{file_id}/view?usp=drive_web"
        changes = {
            'description': description
        }
        calendar_service.events().patch(calendarId=calendar_id, eventId=event_id,
                                        body=changes,
                                        supportsAttachments=True).execute()


def get_events(calendar_id: str) -> dict:
    with lock:
        now = datetime.utcnow()
        time_min = now - timedelta(days=30)
        time_max = now + timedelta(days=30)
        events_result = calendar_service.events().list(calendarId=calendar_id,
                                                       timeMin=time_min.isoformat() + 'Z',
                                                       timeMax=time_max.isoformat() + 'Z',
                                                       singleEvents=True,
                                                       orderBy='startTime').execute()
        events = events_result['items']
        events = {event['id']: event for event in events}

        return events
