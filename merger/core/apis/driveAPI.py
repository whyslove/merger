from __future__ import print_function

import io
import os.path
import pickle
import logging
from pathlib import Path

from datetime import datetime, timedelta

from aiohttp import ClientSession
from aiofile import AIOFile, Reader

from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload

home = str(Path.home())
logger = logging.getLogger('merger_logger')


SCOPES = 'https://www.googleapis.com/auth/drive'
"""
Setting up drive
"""
creds = None
TOKEN_PATH = '/merger/creds/tokenDrive.pickle'
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
UPLOAD_API_URL = 'https://www.googleapis.com/upload/drive/v3'
API_URL = 'https://www.googleapis.com/drive/v3'
HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {creds.token}"
}
drive_service = build('drive', 'v3', credentials=creds)


def drive_refresh_token():
    logger.info("Recreating google drive creds")
    creds_generate()
    HEADERS["Authorization"] = f"Bearer {creds.token}"


def download_video(video_id: str, video_name: str) -> None:
    logger.info(f'Downloading video {video_name} with id {video_id}')

    request = drive_service.files().get_media(fileId=video_id)
    fh = io.FileIO(f'{home}/vids/{video_name}', mode='w')
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while done is False:
        status, done = downloader.next_chunk()


def get_video_by_name(name: str) -> str:
    logger.info(f'Getting the id of video with name {name}')

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


async def upload_video(file_path: str, folder_id: str) -> None:
    meta_data = {
        "name": file_path.split('/')[-1],
        "parents": [folder_id]
    }

    async with ClientSession() as session:
        resp = await session.post(f'{UPLOAD_API_URL}/files?uploadType=resumable',
                                  headers={**HEADERS,
                                           **{"X-Upload-Content-Type": "video/mp4"}},
                                  json=meta_data,
                                  ssl=False)
        async with resp:
            session_url = resp.headers.get('Location')

        async with AIOFile(file_path, 'rb') as afp:
            file_size = str(os.stat(file_path).st_size)
            reader = Reader(afp, chunk_size=256 * 1024 * 100)  # 25MB
            received_bytes_lower = 0
            async for chunk in reader:
                chunk_size = len(chunk)
                chunk_range = f"bytes {received_bytes_lower}-{received_bytes_lower + chunk_size - 1}"

                resp = await session.put(session_url, data=chunk, ssl=False,
                                         headers={"Content-Length": str(chunk_size),
                                                  "Content-Range": f"{chunk_range}/{file_size}"})
                async with resp:
                    chunk_range = resp.headers.get('Range')

                    try:
                        resp_json = await resp.json()
                        file_id = resp_json['id']
                    except:
                        pass

                    if chunk_range is None:
                        break

                    _, bytes_data = chunk_range.split('=')
                    _, received_bytes_lower = bytes_data.split('-')
                    received_bytes_lower = int(received_bytes_lower) + 1

    logger.info(
        f'Uploaded {file_path}')

    return file_id


async def get_folders_by_name(name):
    logger.info(f'Getting the id of folder with name {name}')

    params = dict(
        fields='nextPageToken, files(name, id, parents)',
        q=f"mimeType='application/vnd.google-apps.folder'and name='{name}'",
        spaces='drive'
    )
    folders = []
    page_token = ''

    async with ClientSession() as session:
        while page_token != False:
            resp = await session.get(f'{API_URL}/files?pageToken={page_token}',
                                     headers=HEADERS, params=params,
                                     ssl=False)
            async with resp:
                resp_json = await resp.json()
                folders.extend(resp_json.get('files', []))
                page_token = resp_json.get('nextPageToken', False)

    return {folder['id']: folder.get('parents', []) for folder in folders}


async def share_file(file_id: str, user_email: str) -> None:
    logger.info(f'Sharing file with id {file_id} to user {user_email}')

    user_permission = {
        'type': 'user',
        'role': 'reader',
        'emailAddress': user_email
    }

    async with ClientSession() as session:
        resp = await session.post(f'{API_URL}/files/{file_id}/permissions',
                                  headers=HEADERS, json=user_permission,
                                  ssl=False)
        async with resp:  # to close connection
            pass
