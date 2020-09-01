import time
import traceback
from datetime import datetime, timedelta

import requests
import schedule

from core.apis.calendar_api import add_attachments
from core.apis.classroom_api import create_announcement
from core.apis.driveAPI import get_folders_by_name, share_file
from core.apis.spreadsheets_api import get_data
from core.db.models import Session, Record, Room
from core.exceptions.exceptions import FilesNotFoundException, NoCourseCode
from core.merge import get_files, create_merge, parse_description


class DaemonApp:
    class_sheet_id = '1_YP63y3URvKCMXjHJC7neOJRk1Uyj6DEJTL0jkLYOEI'
    class_sheet_range = 'A2:B1000'

    def __init__(self):
        schedule.every(10).minutes.do(self.invoke_merge_events)

    def invoke_merge_events(self):
        session = Session()
        process_record = session.query(Record).filter(
            Record.processing == True).first()

        if process_record:
            print(
                f'Processing now {process_record.id}: {process_record.event_name}')
            session.close()
            return

        records_to_create = session.query(Record).filter(Record.done == False,
                                                         Record.processing == False).all()

        now_moscow = datetime.now()
        try:
            record = next(record for record in records_to_create
                          if now_moscow >= self.planned_drive_upload(record))
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

            try:
                files = get_files(record, room)
                if not files:
                    raise
            except:
                self.send_zulip_msg(record.user_email,
                                    f'Некоторые исходные видео для вашей склейки "{record.event_name}" в NVR не были найдены на Google-диске, '
                                    'и при подготовке склейки произошла ошибка')
                # logger.error("Some videos not found on Google Drive")
                record.error = True
                raise FilesNotFoundException(
                    "Некоторые исходные видео не были найдены на Google-диске.")

            cameras_file_name, screens_file_name, rounded_start_time, rounded_end_time = files
            file_id, backup_file_id = create_merge(cameras_file_name, screens_file_name,
                                                   rounded_start_time, rounded_end_time,
                                                   record.start_time, record.end_time, folder_id,
                                                   record.event_name)

            record.drive_file_url = f'https://drive.google.com/file/d/{file_id}/preview'
            session.commit()

            share_file(file_id, record.user_email)
            share_file(backup_file_id, record.user_email)
            self.send_zulip_msg(record.user_email,
                                f'Ваша склейка в NVR готова: '
                                f'https://drive.google.com/a/auditory.ru/file/d/{file_id}/view?usp=drive_web')

            if not calendar_id:
                return

            file_ids = [file_id, backup_file_id]
            file_urls = [
                f"https://drive.google.com/a/auditory.ru/file/d/{file_id}/view?usp=drive_web"
                for file_id in file_ids]

            description = add_attachments(calendar_id,
                                          record.event_id,
                                          file_urls)
            desc_json = parse_description(description)

            course_code = desc_json.get('поток')
            if not course_code:
                # logger.info("Course code not provided")
                return

            courses = get_data(self.class_sheet_id,
                               self.class_sheet_range)

            course_id = self.get_course_by_code(course_code, courses)
            if not course_id:
                # logger.info("Course id not found in spreadsheet")
                return

            create_announcement(
                course_id, record.event_name, file_ids, file_urls)

        except:
            traceback.print_exc()  # Это не нужно будет при логах, как и кидать ошибки
        finally:  # можно будет сделать красиво defer
            record.processing = False
            record.done = True
            session.commit()
            session.close()

    def planned_drive_upload(self, record):
        record_end_time = datetime.strptime(
            f'{record.date} {record.end_time}', '%Y-%m-%d %H:%M')
        # Record from future
        if record_end_time.minute in [0, 30]:
            delta = 10
        elif 30 > record_end_time.minute > 0:
            delta = 30 - record_end_time.minute + 10
        else:
            delta = 60 - record_end_time.minute + 10

        return record_end_time + timedelta(minutes=delta)

    # 2 unobvious tricks. Better contact a creator
    def get_folder_id(self, date: str, room: Room) -> str:
        folders = get_folders_by_name(date)

        for folder_id, folder_parent_id in folders.items():
            if folder_parent_id == room.drive.split('/')[-1]:
                break
        else:
            folder_id = room.drive.split('/')[-1]

        return folder_id

    def get_course_by_code(self, course_code: str, courses: list) -> str or None:
        try:
            course_row = next(
                course for course in courses if course and course[0].strip() == course_code)
            return course_row[1].strip()
        except StopIteration:
            return None

    # change to own NVR notifier
    def send_zulip_msg(self, email, msg):
        res = requests.post('http://172.18.130.41:8080/api/send-msg', json={
            "email": email,
            "msg": msg
        })

    def run(self):
        while True:
            schedule.run_pending()
            time.sleep(1)


if __name__ == "__main__":
    daemon_app = DaemonApp()
    daemon_app.invoke_merge_events()
    daemon_app.run()
