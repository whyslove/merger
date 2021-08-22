import io
from logging import log
import os.path
import pickle
from loguru import logger

from pathlib import Path

from aiohttp import ClientSession

from aiofile import AIOFile, Reader
from uuid import uuid4

from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

from settings import settings  # add two dots (..)
import os

HOME_PATH = str(Path.home())

SCOPES = "https://www.googleapis.com/auth/drive"
creds = None
TOKEN_PATH = settings.token_path
CREDS_PATH = settings.creds_path


def creds_generate():
    global creds
    if os.path.exists(TOKEN_PATH):
        with open(TOKEN_PATH, "rb") as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDS_PATH, SCOPES)
            creds = flow.run_local_server(port=0)
            with open(TOKEN_PATH, "wb") as token:
                pickle.dump(creds, token)


creds_generate()
UPLOAD_API_URL = "https://www.googleapis.com/upload/drive/v3"
API_URL = "https://www.googleapis.com/drive/v3"
HEADERS = {"Content-Type": "application/json", "Authorization": f"Bearer {creds.token}"}
drive_service = build("drive", "v3", credentials=creds)


def drive_refresh_token():
    logger.info("Recreating google drive creds")
    creds_generate()
    HEADERS["Authorization"] = f"Bearer {creds.token}"


def download_video(video_id: str, folder_name: str) -> str:
    """Downloads files from GDrive

    Args:
        video_id (str): video id on Google Drive
        folder_name (str): Folder in which merger is currently working

    Returns:
        str: Name of the downloaded file
    """
    logger.info(f"Downloading id {video_id} into {folder_name}")
    file_name = str(uuid4()) + ".mp4"
    request = drive_service.files().get_media(fileId=video_id)
    fh = io.FileIO(f"{HOME_PATH}/merger/{folder_name}/{file_name}", mode="w")
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while done is False:
        status, done = downloader.next_chunk()
    return file_name


def get_video_by_name(name: str) -> str:
    logger.info(f"Getting the id of video with name {name}")

    page_token = None

    while True:
        response = (
            drive_service.files()
            .list(
                q=f"mimeType='video/mp4'" f"and name='{name}'",
                spaces="drive",
                fields="nextPageToken, files(name, id)",
                pageToken=page_token,
            )
            .execute()
        )
        page_token = response.get("nextPageToken", None)

        if page_token is None:
            break

    return response["files"][0]["id"]


async def upload_video(file_path: str, folder_id: str) -> str:
    meta_data = {"name": file_path.split("/")[-1], "parents": [folder_id]}

    file_id = ""

    logger.info(f"Uploading {file_path}")

    async with ClientSession() as session:
        resp = await session.post(
            f"{UPLOAD_API_URL}/files?uploadType=resumable",
            headers={**HEADERS, **{"X-Upload-Content-Type": "video/mp4"}},
            json=meta_data,
            ssl=False,
        )
        async with resp:
            session_url = resp.headers.get("Location")
            logger.debug(resp)
            pass

        async with AIOFile(file_path, "rb") as afp:
            file_size = str(os.stat(file_path).st_size)
            reader = Reader(afp, chunk_size=256 * 1024 * 100)  # 25MB
            received_bytes_lower = 0
            async for chunk in reader:
                chunk_size = len(chunk)
                chunk_range = f"bytes {received_bytes_lower}-{received_bytes_lower + chunk_size - 1}"

                resp = await session.put(
                    session_url,
                    data=chunk,
                    ssl=False,
                    headers={
                        "Content-Length": str(chunk_size),
                        "Content-Range": f"{chunk_range}/{file_size}",
                    },
                )
                async with resp:
                    chunk_range = resp.headers.get("Range")

                    try:
                        resp_json = await resp.json()
                        file_id = resp_json["id"]
                    except Exception:
                        pass

                    if chunk_range is None:
                        break

                    _, bytes_data = chunk_range.split("=")
                    _, received_bytes_lower = bytes_data.split("-")
                    received_bytes_lower = int(received_bytes_lower) + 1

    logger.info(f"Uploaded {file_path}")

    return file_id


async def upload_to_remote_storage(room_name: str, date: str, file_path: str) -> None:
    folder_with_room_id = list((await get_folders_by_name(room_name)).keys())[0]
    folders_with_date_ids = await get_folders_by_name(date)

    correct_folder_with_date = (
        None  # we have many folders with dates in different rooms
    )
    # so we have to choose exact what we need
    for date_folder, parent_folders in folders_with_date_ids.items():
        if folder_with_room_id in parent_folders:
            correct_folder_with_date = date_folder
            break

    file_id = await upload_video(
        file_path=file_path, folder_id=correct_folder_with_date
    )
    logger.info(f"Finished uploading video {file_path}, now it's id is: {file_id}")
    return f"https://drive.google.com/file/d/{file_id}"


async def get_folders_by_name(name):
    logger.debug(f"Getting the id of folder with name {name}")

    params = dict(
        fields="nextPageToken, files(name, id, parents)",
        q=f"mimeType='application/vnd.google-apps.folder' and name='{name}'",
        spaces="drive",
    )
    folders = []
    page_token = ""

    async with ClientSession() as session:
        while page_token != False:
            resp = await session.get(
                f"{API_URL}/files?pageToken={page_token}",
                headers=HEADERS,
                params=params,
                ssl=False,
            )
            async with resp:
                resp_json = await resp.json()
                folders.extend(resp_json.get("files", []))
                page_token = resp_json.get("nextPageToken", False)

    return {folder["id"]: folder.get("parents", []) for folder in folders}


async def share_file(file_id: str, user_email: str) -> None:
    logger.info(f"Sharing file with id {file_id} to user {user_email}")

    user_permission = {"type": "user", "role": "reader", "emailAddress": user_email}

    async with ClientSession() as session:
        resp = await session.post(
            f"{API_URL}/files/{file_id}/permissions",
            headers=HEADERS,
            json=user_permission,
            ssl=False,
        )
        async with resp:  # to close connection
            pass
