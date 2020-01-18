from __future__ import print_function
import datetime
import pickle
import os.path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import json
from datetime import datetime, timedelta

from nvrAPI.models import nvr_db_context, Room

from threading import RLock
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