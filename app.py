import time
import traceback
from datetime import datetime, timedelta

import requests
import schedule

from calendar_api import add_attachments
from classroom_api import create_assignment
from driveAPI import get_folders_by_name, share_file
from merge import get_files, create_merge
from models import Session, Record, Room
from spreadsheets_api import get_data


class DaemonApp:
    class_sheet_id = '1_YP63y3URvKCMXjHJC7neOJRk1Uyj6DEJTL0jkLYOEI'
    class_sheet_range = 'A2:B500'

    def __init__(self):
        schedule.every().hour.at(":00").do(self.invoke_merge_events)
        schedule.every().hour.at(":30").do(self.invoke_merge_events)

    def invoke_merge_events(self):
        session = Session()
        process_record = session.query(Record).filter(Record.processing is True).first()

        if process_record:
            session.close()
            return

        records_to_create = session.query(Record).filter(Record.done is False,
                                                         Record.processing is False).all()

        now_moscow = datetime.now() + timedelta(hours=3)
        try:
            record = next(record for record in records_to_create
                          if now_moscow >= datetime.strptime(f'{record.date} {record.end_time}', '%Y-%m-%d %H:%M'))
        except StopIteration:
            print(f'Records not found at {now_moscow}')
            session.close()
            return

        try:
            print(f'start {record.event_name}')
            room = session.query(Room).filter(
                Room.name == record.room_name).first()

            record.processing = True
            session.commit()

            calendar_id = room.calendar if record.event_id else None
            folder_id = self.get_folder_id(record.date, room)
            cameras_file_name, screens_file_name, rounded_start_time, rounded_end_time = get_files(
                record, room)

            file_id, backup_file_id = create_merge(cameras_file_name, screens_file_name,
                                                   rounded_start_time, rounded_end_time,
                                                   record.start_time, record.end_time, folder_id,
                                                   record.event_name)

            share_file(file_id, record.user_email)
            share_file(backup_file_id, record.user_email)
            self.send_zulip_msg(record.user_email,
                                f'Ваша склейка в NVR готова: '
                                f'https://drive.google.com/a/auditory.ru/file/d/{file_id}/view?usp=drive_web')

            if calendar_id:
                try:
                    file_ids = [file_id, backup_file_id]
                    file_urls = [
                        f"\nhttps://drive.google.com/a/auditory.ru/file/d/{file_id}/view?usp=drive_web" for file_id in
                        file_ids]

                    description = add_attachments(calendar_id,
                                                  record.event_id,
                                                  file_urls)

                    course_code = description.split('\n')[0]
                    courses = get_data(self.class_sheet_id, self.class_sheet_range)

                    course_id = self.get_course_by_code(course_code, courses)

                    if course_id:
                        create_assignment(course_id, record.event_name, file_urls)
                except:
                    traceback.print_exc()

        except:
            traceback.print_exc()
        finally:
            record.processing = False
            record.done = True
            session.commit()
            session.close()

    def get_folder_id(self, date: str, room: Room) -> str:
        folders = get_folders_by_name(date)

        for folder_id, folder_parent_id in folders.items():
            if folder_parent_id == room.drive.split('/')[-1]:
                break
        else:
            folder_id = room.drive.split('/')[-1]

        return folder_id

    def get_course_by_code(self, course_code: str, courses: list) -> str:
        for course in courses:
            if course[0].strip() == course_code:
                return course[1].strip()

        raise RuntimeError(f"Курс с предметной единицей '{course_code}' не найден")

    def send_zulip_msg(self, email, msg):
        res = requests.post('http://172.18.130.41:8080/api/send-msg', json={
            "email": email,
            "msg": msg
        })
        print(res)

    def run(self):
        while True:
            schedule.run_pending()
            time.sleep(1)


if __name__ == "__main__":
    daemon_app = DaemonApp()
    daemon_app.run()
