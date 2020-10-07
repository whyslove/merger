from __future__ import print_function

import os.path
import pickle
import logging
from datetime import datetime, timedelta

from aiohttp import ClientSession
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow

logger = logging.getLogger('merger_logger')


SCOPES = 'https://www.googleapis.com/auth/calendar'
"""
Setting up calendar
"""
creds = None
TOKEN_PATH = '/merger/creds/tokenCalendar.pickle'
CREDS_PATH = '/merger/creds/credentials.json'


def creds_generate():
    global creds
    if os.path.exists(TOKEN_PATH):
        with open(TOKEN_PATH, 'rb') as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                CREDS_PATH, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_PATH, 'wb') as token:
            pickle.dump(creds, token)


creds_generate()
API_URL = 'https://www.googleapis.com/calendar/v3'
HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {creds.token}"
}


def calendar_refresh_token():
    logger.info("Recreating google calendar creds")
    creds_generate()
    HEADERS["Authorization"] = f"Bearer {creds.token}"


async def add_attachments(calendar_id: str, event_id: str, files_ids: list, event_name: str) -> str:
    """
    Adds url of drive file 'file_id' to calendar event 'event_id'
    """
    logger.info(
        f'Adding attachments to calendar with id {calendar_id}, event with id {event_id}, event name is {event_name}')

    async with ClientSession() as session:
        resp = await session.get(f'{API_URL}/calendars/{calendar_id}/events/{event_id}',
                                 headers=HEADERS, ssl=False)
        async with resp:
            event = await resp.json()

        changes = {
            "attachments": [
                {
                    "fileUrl": f'https://drive.google.com/a/auditory.ru/file/d/{file}/view?usp=drive_web',
                    "title": event_name,
                    "fileId": file,
                    "mimeType": "video/mp4",
                    'iconLink': 'https://drive-thirdparty.googleusercontent.com/16/type/video/mp4'
                } for file in files_ids
            ]
        }

        resp = await session.patch(f'{API_URL}/calendars/{calendar_id}/events/{event_id}',
                                   headers=HEADERS, ssl=False,
                                   json=changes, params={'supportsAttachments': 'true'})
        async with resp:
            pass

    logger.info(
        f'Added attachments to calendar with id {calendar_id}, event with id {event_id}')

    return event.get('description', '')
