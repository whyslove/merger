from __future__ import print_function
import pickle
import os.path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

SCOPES = ['https://www.googleapis.com/auth/classroom.courses.readonly',
          'https://www.googleapis.com/auth/classroom.coursework.students',
          ]
TOKEN_PATH = '.creds/tokenClassroom.pickle'
CREDS_PATH = '.creds/classroom_creds.json'

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


def get_all_courses():
    results = classroom_service.courses().list().execute()
    courses = results.get('courses', [])
    return courses


def create_assignment(course_id, title, url):
    body = {
        'title': title,
        'description': url,
        'workType': 'ASSIGNMENT',
        'state': 'PUBLISHED',
    }

    work = classroom_service.courses().courseWork().create(
        courseId=course_id, body=body).execute()

    return work


if __name__ == "__main__":
    COURSE_ID = '62566470367'  # test_graders
    URL = 'https://drive.google.com/a/auditory.ru/file/d/1u6d23Y9-tOsL-YF3JQGNmXmJ3w5gYKNN/view?usp=drive_web'

    from pprint import pprint
    pprint(create_assignment(COURSE_ID, URL))
