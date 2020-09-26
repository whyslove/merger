from __future__ import print_function

from threading import RLock
import io
import os.path
import pickle
import logging
from pathlib import Path

from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload

home = str(Path.home())


lock = RLock()

SCOPES = 'https://www.googleapis.com/auth/drive'
"""
Setting up drive
"""
creds = None
token_path = '/merger/creds/tokenDrive.pickle'
creds_path = '/merger/creds/credentials.json'

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


logger = logging.getLogger('merger_logger')


def download_video(video_id: str, video_name: str) -> None:
    with lock:
        logger.info(f'Downloading video {video_name} with id {video_id}')

        request = drive_service.files().get_media(fileId=video_id)
        fh = io.FileIO(f'{home}/vids/{video_name}', mode='w')
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while done is False:
            status, done = downloader.next_chunk()

        logger.info(f'Downloaded video {video_name}')


def upload_video(file_name: str, folder_id: str) -> tuple:
    """
    Upload file "filename" on drive folder 'folder_id'
    """
    with lock:
        logger.info(
            f'Uploading video {file_name} to folder with id {folder_id}')

        media = MediaFileUpload(
            file_name, mimetype="video/mp4", resumable=True)
        file_data = {
            "name": file_name.split('/')[-1],
            "parents": [folder_id]
        }
        file = drive_service.files().create(
            body=file_data, media_body=media).execute()

        logger.info(
            f'Uploaded video {file_name} to folder with id {folder_id}')

        return file.get('id')


def get_video_by_name(name: str) -> str:
    with lock:
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


def get_folders_by_name(name):
    with lock:
        logger.info(f'Getting the id of folder with name {name}')

        page_token = None

        while True:
            response = drive_service.files().list(q=f"mimeType='application/vnd.google-apps.folder'"
                                                    f"and name='{name}'",
                                                  spaces='drive',
                                                  fields='nextPageToken, files(name, id, parents)',
                                                  pageToken=page_token).execute()
            page_token = response.get('nextPageToken', None)

            if page_token is None:
                break

        return {folder['id']: folder.get('parents', [''])[0] for folder in response['files']}


def share_file(file_id, user_email):
    with lock:
        logger.info(f'Sharing file with id {file_id} to user {user_email}')

        user_permission = {
            'type': 'user',
            'role': 'reader',
            'emailAddress': user_email}

        drive_service.permissions().create(
            fileId=file_id, body=user_permission).execute()

        logger.info(f'Shared file with id {file_id} to user {user_email}')
