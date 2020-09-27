import logging
import os
import time
from datetime import datetime, timedelta
from pathlib import Path

import requests
import schedule

from core.apis.calendar_api import add_attachments
from core.apis.classroom_api import create_announcement
from core.apis.driveAPI import get_folders_by_name, share_file, upload_video
from core.apis.spreadsheets_api import get_data
from core.db.models import Session, Record, Room
from core.exceptions.exceptions import FilesNotFoundException
from core.merge import parse_description
from core.merge2 import Merge

HOME = str(Path.home())


class DaemonApp:
    class_sheet_id = '1nyQ0M_3RozJ-MpTuji7eIbsxR7pk1wNPzVgCaiNMryU'
    class_sheet_range = 'A2:B1000'
    logger = logging.getLogger('merger_logger')

    def __init__(self):
        self.logger.info('Class \"DaemonApp\" instantiated')
        schedule.every(10).minutes.do(self.invoke_merge_events)

    def invoke_merge_events(self):
        self.logger.info(f'Starting merge check')

        session = Session()
        process_record = session.query(Record).filter(
            Record.processing == True).first()

        if process_record:
            self.logger.info(
                f'Found processing merge with id {process_record.id}, skipping iteration')
            session.close()
            return

        records_to_create = session.query(Record).filter(Record.done == False,
                                                         Record.processing == False,
                                                         Record.error == False).all()

        try:
            record = next(record for record in records_to_create
                          if datetime.now() >= self.planned_drive_upload(record))
            initially_error = False
        except StopIteration:
            self.logger.info(f'Records not found at {datetime.now()}')
            record = session.query(Record).filter(
                Record.error == True, Record.done == False).first()
            if not record:
                session.close()
                return
            self.logger.info(f'Restart record with error: {record.event_name}')
            initially_error = True
            record.error = False

        try:
            self.logger.info(
                f'Started merging record {record.event_name} with id {record.id}')
            room = session.query(Room).filter(
                Room.name == record.room_name).first()

            record.processing = True
            session.commit()

            calendar_id = room.calendar if record.event_id else None
            folder_id = self.get_folder_id(record.date, room)

            try:
                merge = Merge(record, room)

                file_name, backup_file_name = merge.create_merge()
            except RuntimeError:
                self.logger.error(
                    f'Source videos not found for record {record.event_name} with id {record.id} '
                    f'or some error occured while merging')

                self.send_zulip_msg(record.user_email,
                                    f'Некоторые исходные видео для вашей склейки "{record.event_name}" в NVR не были найдены на Google-диске, '
                                    'и при подготовке склейки произошла ошибка')

                record.error = True
                raise FilesNotFoundException(
                    "Некоторые исходные видео не были найдены на Google-диске.")

            file_id, backup_file_id = self.upload(file_name, backup_file_name, folder_id)

            record.drive_file_url = f'https://drive.google.com/file/d/{file_id}/preview'
            session.commit()

            self.logger.info(
                'Merge was successfully processed, starting files sharing')
            share_file(file_id, record.user_email)
            share_file(backup_file_id, record.user_email)
            self.send_zulip_msg(record.user_email,
                                f'Ваша склейка в NVR готова: '
                                f'https://drive.google.com/a/auditory.ru/file/d/{file_id}/view?usp=drive_web')

            if not calendar_id:
                return

            self.logger.info(
                f'Merge has calendar id {calendar_id}, starting creating attachments')

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
                self.logger.info(
                    f"Course code not provided for event {record.event_name} with id {record.event_id}")
                return

            courses = get_data(self.class_sheet_id,
                               self.class_sheet_range)

            course_id = self.get_course_by_code(course_code, courses)
            if not course_id:
                return

            create_announcement(
                course_id, record.event_name, file_ids, file_urls)

        except:
            self.logger.exception(f'Exception occured while creating attachments. \
                                    Calendar id: {calendar_id}, Record id: {record.id}')

            if initially_error and record.error:  # second try to create merge failed
                record.done = True

        finally:  # можно будет сделать красиво defer/with
            self.logger.info(
                f'Setting record {record.event_name} with id {record.id} as done')

            if not record.error:
                record.done = True

            record.processing = False
            session.commit()
            session.close()

    def planned_drive_upload(self, record):
        record_end_time = datetime.strptime(
            f'{record.date} {record.end_time}', '%Y-%m-%d %H:%M')
        # Record from future
        if record_end_time.minute in [0, 30]:
            delta = 60
        elif 30 > record_end_time.minute > 0:
            delta = 30 - record_end_time.minute + 60
        else:
            delta = 60 - record_end_time.minute + 60

        return record_end_time + timedelta(minutes=delta)

    # 2 unobvious tricks. Better contact a creator
    def get_folder_id(self, date: str, room: Room) -> str:
        self.logger.info(
            f'Started getting folder id from date {date} and room {room.name}')

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
            self.logger.error(f'Course with code {course_code} not found')
            return None

    # change to own NVR notifier
    def send_zulip_msg(self, email, msg):
        res = requests.post('http://172.18.130.41:8080/api/send-msg', json={
            "email": email,
            "msg": msg
        })

        self.logger.info(f'Request to Zulip bot returned code {res.status_code}. \
            Email: {email}, Message: {msg}')

    def upload(self, file_name: str, backup_file_name: str, folder_id: str) -> tuple:
        file_id = upload_video(f'{HOME}/vids/{file_name}', folder_id)
        backup_file_id = upload_video(
            f'{HOME}/vids/{backup_file_name}', folder_id)

        self.logger.info(
            f'Finished uploading videos {file_name} and {backup_file_name}')

        try:
            os.remove(f'{HOME}/vids/{file_name}')
            os.remove(f'{HOME}/vids/{backup_file_name}')
        except OSError:
            self.logger.exception("Error while deleting final videos")

        return file_id, backup_file_id

    def run(self):
        while True:
            schedule.run_pending()
            time.sleep(1)

    @staticmethod
    def create_logger(mode='INFO'):
        logs = {'INFO': logging.INFO,
                'DEBUG': logging.DEBUG}

        logger = logging.getLogger('merger_logger')
        logger.setLevel(logs[mode])

        handler = logging.StreamHandler()
        handler.setLevel(logs[mode])

        formatter = logging.Formatter(
            '%(levelname)-8s  %(asctime)s    %(message)s',
            datefmt='%d-%m-%Y %I:%M:%S %p')

        handler.setFormatter(formatter)

        logger.addHandler(handler)


if __name__ == "__main__":
    DaemonApp.create_logger()

    daemon_app = DaemonApp()
    daemon_app.invoke_merge_events()
    daemon_app.run()
