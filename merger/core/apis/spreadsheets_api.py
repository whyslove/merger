from __future__ import print_function

import os.path
import pickle
import logging
from datetime import datetime, timedelta

from aiohttp import ClientSession
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow

logger = logging.getLogger('merger_logger')

SCOPES = 'https://www.googleapis.com/auth/spreadsheets.readonly'
"""
Setting up calendar
"""
creds = None
TOKEN_PATH = '/merger/creds/tokenSheets.pickle'
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
HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {creds.token}"
}


def sheets_refresh_token():
    logger.info("Recreating google creds")
    creds_generate()
    HEADERS["Authorization"] = f"Bearer {creds.token}"


async def get_data(sheet_id: str, range: str) -> list:
    logger.info(
        f'Getting data from datasheet with id {sheet_id} with range {range}')

    async with ClientSession() as session:
        resp = await session.get(f'https://sheets.googleapis.com/v4/spreadsheets/{sheet_id}/values/{range}',
                                 headers=HEADERS,
                                 ssl=False)
        async with resp:
            json = await resp.json()

        return json.get('values', [])
