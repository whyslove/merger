from __future__ import print_function
import pickle
import os.path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.http import MediaIoBaseDownload
import io
from datetime import datetime
from merge import home


from threading import RLock
lock = RLock()


SCOPES = 'https://www.googleapis.com/auth/drive'
"""
Setting up drive
"""
creds = None
token_path = '.creds/tokenDrive.pickle'
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

drive_service = build('drive', 'v3', credentials=creds)



def download_video(video_id: str, video_name: str) -> None:
    request = drive_service.files().get_media(fileId=video_id)
    fh = io.FileIO(f'{home}/vids/{video_name}', mode='w')
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while done is False:
        status, done = downloader.next_chunk()


def get_video_by_name(name: str) -> str:
    page_token = None

    while True:
        response = drive_service.files().list(q=f"mimeType='video/mp4'"
                                                f"and name='{name}'",
                                                spaces='drive',
                                                fields='nextPageToken, files(name, id)',
                                                pageToken=page_token).execute()
        page_token = response.get('nextPageToken', None)

        if page_token is None:
            break

    return response['files'][0]['id']

# Example

# for i in d:
#     # i в формате '2020-01-11_21:30_Зал_54.mp4'
#     g = get_video_by_name(i)
#     download_video(g, i)
