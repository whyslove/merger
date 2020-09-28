import logging
import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from threading import Thread
import asyncio
from copy import deepcopy

from aiohttp import ClientSession
import schedule

from core.apis.calendar_api import add_attachments, calendar_creds_check
from core.apis.classroom_api import create_announcement, classroom_creds_check
from core.apis.driveAPI import get_folders_by_name, share_file, upload_video, drive_creds_check
from core.apis.spreadsheets_api import get_data, sheets_creds_check
from core.db.models import Session, Record, Room
from core.db.utils import update_record_driveurl
from core.exceptions.exceptions import FilesNotFoundException
from core.merge import Merge

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

        calendar_creds_check()
        classroom_creds_check()
        drive_creds_check()
        sheets_creds_check()

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

            try:
                merge = Merge(record, room)
                file_name, backup_file_name = merge.create_merge()
            except RuntimeError:
                self.logger.error(
                    f'Source videos not found for record {record.event_name} with id {record.id} '
                    f'or some error occured while merging')

                asyncio.run(
                    self.send_zulip_msg(record.user_email,
                                        f'Некоторые исходные видео для вашей склейки "{record.event_name}" в NVR не были найдены на Google-диске, '
                                        'и при подготовке склейки произошла ошибка')
                )

                record.error = True
                raise FilesNotFoundException(
                    "Некоторые исходные видео не были найдены на Google-диске.")

            Thread(target=asyncio.run, args=(self.apis_stuff(
                deepcopy(record), deepcopy(room), file_name, backup_file_name), )).start()

        except Exception as err:
            self.logger.error(f'Exception occurred: {err}')

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

    # change to own NVR notifier
    async def send_zulip_msg(self, email, msg):
        async with ClientSession() as session:
            res = await session.post('http://172.18.130.41:8080/api/send-msg', ssl=False,
                                     json={
                                         "email": email,
                                         "msg": msg
                                     })

        self.logger.info(f'Request to Zulip bot returned code {res.status}. \
            Email: {email}, Message: {msg}')

    async def apis_stuff(self, record, room, file_name, backup_file_name):
        folder_id = await self.get_folder_id(record.date, room)
        file_id, backup_file_id = await self.upload(file_name, backup_file_name, folder_id)

        await update_record_driveurl(record, f'https://drive.google.com/file/d/{file_id}/preview')

        self.logger.info(
            'Merge was successfully processed, starting files sharing')

        await asyncio.gather(share_file(file_id, record.user_email),
                             share_file(backup_file_id, record.user_email))
        await self.send_zulip_msg(record.user_email,
                                  f'Ваша склейка в NVR готова: '
                                  f'https://drive.google.com/a/auditory.ru/file/d/{file_id}/view?usp=drive_web')

        calendar_id = room.calendar if record.event_id else None
        if not calendar_id:
            return

        self.logger.info(
            f'Merge has calendar id {calendar_id}, starting creating attachments')

        file_ids = [file_id, backup_file_id]
        file_urls = [
            f"https://drive.google.com/a/auditory.ru/file/d/{file_id}/view?usp=drive_web"
            for file_id in file_ids]

        description = await add_attachments(calendar_id,
                                            record.event_id,
                                            file_urls)
        desc_json = Merge.parse_description(description)

        course_code = desc_json.get('поток')
        if not course_code:
            self.logger.info(
                f"Course code not provided for event {record.event_name} with id {record.event_id}")
            return

        courses = await get_data(self.class_sheet_id,
                                 self.class_sheet_range)

        course_id = self.get_course_by_code(course_code, courses)
        if not course_id:
            return

        await create_announcement(
            course_id, record.event_name, file_ids, file_urls)

    async def get_folder_id(self, date: str, room: Room) -> str:

        self.logger.info(
            f'Started getting folder id from date {date} and room {room.name}')

        folders = await get_folders_by_name(date)

        # 2 unobvious tricks. Better contact a creator
        room_drive_id = room.drive.split('/')[-1]
        for folder_id, folder_parent_ids in folders.items():
            if room_drive_id in folder_parent_ids:
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

    async def upload(self, file_name: str, backup_file_name: str, folder_id: str) -> tuple:
        file_id, backup_file_id = await asyncio.gather(
            upload_video(f'{HOME}/vids/{file_name}', folder_id),
            upload_video(
                f'{HOME}/vids/{backup_file_name}', folder_id)
        )

        self.logger.info(
            f'Finished uploading videos {file_name} and {backup_file_name}')

        self.remove_file(f'{HOME}/vids/{file_name}')
        self.remove_file(f'{HOME}/vids/{backup_file_name}')

        return file_id, backup_file_id

    def remove_file(self, filename: str) -> None:
        try:
            os.remove(filename)
        except FileNotFoundError:
            self.logger.warning(f'Failed to remove file {filename}')
        except:
            self.logger.error(
                f'Failed to remove file {filename}', exc_info=True)

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
