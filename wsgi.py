from rest import app
from app import DaemonApp
from multiprocessing import Process

if __name__ == "__main__":
    daemon = DaemonApp()
    Process(target=daemon.run).start()
    app.run()
