from __future__ import print_function
import pickle
import os.path
import logging
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

SCOPES = ['https://www.googleapis.com/auth/classroom.courses.readonly',
          'https://www.googleapis.com/auth/classroom.coursework.students',
          'https://www.googleapis.com/auth/classroom.announcements']
TOKEN_PATH = '/merger/creds/tokenClassroom.pickle'
CREDS_PATH = '/merger/creds/classroom_creds.json'

creds = None

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

classroom_service = build('classroom', 'v1', credentials=creds)

logger = logging.getLogger('merger_logger')


def get_all_courses():
    logger.info(f'Getting info about all classroom courses')

    results = classroom_service.courses().list().execute()
    courses = results.get('courses', [])
    return courses


def create_announcement(course_id: str, title: str, file_ids: list, file_urls: list) -> dict:
    logger.info(f'Creating assignment at course {course_id} with title {title}')

    body = {
        'text': title,
        "materials": [
            {
                "link": {
                    "url": link,
                    "title": title,
                }
            } for id, link in zip(file_ids, file_urls)
        ],
    }

    logger.info(f'Created assignment at course {course_id} with title {title}')

    return classroom_service.courses().announcements().create(
        courseId=course_id, body=body).execute()


def get_course_by_code(course_code):
    logger.info(f'Getting course by course code {course_code}')

    courses = get_all_courses()
    for course in courses:
        if course_code == course.get('description', ''):
            return course

    return None
