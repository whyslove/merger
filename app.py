import time

import schedule

from models import Session, Record, Room
from driveAPI import get_folders_by_name


class DaemonApp:
    records = None

    # record_handler = RecordHandler()

    def __init__(self):
        schedule.every().hour.at(":00").do(self.invoke_merge_events)
        schedule.every().hour.at(":30").do(self.invoke_merge_events)

    def invoke_merge_events(self):
        session = Session()
        self.records = session.query(Record).all()
        session.close()

        for record in self.records:
            try:
                pass
                # TODO
            except:
                pass

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
