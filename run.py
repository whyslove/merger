from threading import Thread

from merge import merge_video
from flask import Flask, request

app = Flask("NVR_VIDEO_MERGE")


@app.route('/', methods=["GET", "POST"])
def main():
    return "Merge server v1.0", 200


@app.route('/merge', methods=["POST"])
def start_merge():
    json = request.get_json(force=True)
    Thread(target=merge_video,
           args=(json['url'], json["screen_num"], json["cam_num"], json["record_name"],
                 json["room_id"], json['calendar_id'], json['event_id']),
           daemon=True
           ).start()

    return "Merge started", 200


if __name__ == '__main__':
    app.run()
