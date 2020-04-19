from __future__ import print_function

import os.path
import pickle

from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = 'https://www.googleapis.com/auth/spreadsheets.readonly'
"""
Setting up calendar
"""
creds = None
token_path = '/merger/.creds/tokenCalendar.pickle'
creds_path = '/merger/.creds/credentials.json'

if os.path.exists(token_path):
    with open(token_path, 'rb') as token:
        creds = pickle.load(token)
if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    else:
        flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
        creds = flow.run_local_server(port=0)
    with open(token_path, 'wb') as token:
        pickle.dump(creds, token)

sheets_service = build('sheets', 'v4', credentials=creds)


def get_data(sheet_id: str, range: str) -> list:
    result = sheets_service.spreadsheets().values().get(spreadsheetId=sheet_id, range=range).execute()

    return result.get('values', [])
