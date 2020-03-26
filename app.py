import time
from datetime import datetime, timedelta
import schedule

from driveAPI import get_folders_by_name, share_file
from merge import get_files, create_merge
from models import Session, Record, Room


class DaemonApp:
    records = None

    def __init__(self):
        schedule.every().hour.at(":00").do(self.invoke_merge_events)
        schedule.every().hour.at(":30").do(self.invoke_merge_events)

    def invoke_merge_events(self):
        session = Session()
        self.records = session.query(Record).filter(Record.done == False).all()

        for record in self.records:
            date, end_time = record.date, record.end_time
            if datetime.now() + timedelta(hours=3) <= datetime.strptime(f'{date} {end_time}', '%Y-%m-%d %H:%M'):
                continue
            print(f'start {record.event_name}')
            room = session.query(Room).filter(
                Room.name == record.room_name).first()

            calendar_id = room.calendar if record.event_id else None
            folder_id = self.get_folder_id(record.date, room)
            cameras_file_name, screens_file_name, rounded_start_time, rounded_end_time = get_files(
                record, room)

            file_id = create_merge(cameras_file_name, screens_file_name,
                                   rounded_start_time, rounded_end_time,
                                   record.start_time, record.end_time, folder_id,
                                   calendar_id, record.event_id)

            share_file(file_id, record.user_email)

            record.done = True

        session.commit()
        session.close()

    def get_folder_id(self, date: str, room: Room):
        folders = get_folders_by_name(date)

        for folder_id, folder_parent_id in folders.items():
            if folder_parent_id == room.drive.split('/')[-1]:
                break
        else:
            folder_id = room.drive.split('/')[-1]

        return folder_id

    def run(self):
        while True:
            schedule.run_pending()
            time.sleep(1)


if __name__ == "__main__":
    daemon_app = DaemonApp()
    daemon_app.run()
