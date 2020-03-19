import time

import schedule

from models import Session, Record


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

    def run(self):
        while True:
            schedule.run_pending()
            time.sleep(1)


if __name__ == "__main__":
    daemon_app = DaemonApp()
    daemon_app.run()
