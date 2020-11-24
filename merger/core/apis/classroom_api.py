import pickle
import os.path
import logging

from aiohttp import ClientSession
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

SCOPES = [
    "https://www.googleapis.com/auth/classroom.courses.readonly",
    "https://www.googleapis.com/auth/classroom.coursework.students",
    "https://www.googleapis.com/auth/classroom.announcements",
]
TOKEN_PATH = "/merger/creds/tokenClassroom.pickle"
CREDS_PATH = "/merger/creds/classroom_creds.json"
creds = None

logger = logging.getLogger("merger_logger")


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
API_URL = "https://classroom.googleapis.com/v1"
HEADERS = {"Content-Type": "application/json", "Authorization": f"Bearer {creds.token}"}


def classroom_refresh_token():
    logger.info("Recreating google classroom creds")
    creds_generate()
    HEADERS["Authorization"] = f"Bearer {creds.token}"


async def create_announcement(
    course_id: str, title: str, file_ids: list, file_urls: list
) -> dict:
    logger.info(f"Creating assignment at course {course_id} with title {title}")

    body = {
        "text": title,
        "materials": [
            {
                "link": {
                    "url": link,
                    "title": title,
                }
            }
            for id, link in zip(file_ids, file_urls)
        ],
    }

    async with ClientSession() as session:
        resp = await session.post(
            f"{API_URL}/courses/{course_id}/announcements",
            headers=HEADERS,
            json=body,
            ssl=False,
        )
        async with resp:
            return await resp.json()
