from __future__ import print_function
import pickle
import os.path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

SCOPES = ['https://www.googleapis.com/auth/classroom.courses.readonly',
          'https://www.googleapis.com/auth/classroom.coursework.students']
TOKEN_PATH = '/merger/.creds/tokenClassroom.pickle'
CREDS_PATH = '/merger/.creds/classroom_creds.json'

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


def create_assignment(course_id, title, files):
    body = {
        'title': title,
        'description': '\n'.join(files),
        'workType': 'ASSIGNMENT',
        'state': 'PUBLISHED',
    }

    work = classroom_service.courses().courseWork().create(
        courseId=course_id, body=body).execute()

    return work


def get_course_by_code(course_code):
    courses = get_all_courses()
    for course in courses:
        if course_code == course.get('description', ''):
            return course

    return None
