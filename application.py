from threading import Thread
from merge import hstack_camera_and_screen, process_wait
from flask import Flask, request, jsonify
from driveAPI import get_video_by_name
import time

app = Flask("NVR_VIDEO_MERGE")


@app.route('/', methods=["GET", "POST"])
def main():
    return "Merge server v1.0", 200


@app.route('/merge', methods=["POST"])
def start_merge():
    json = request.get_json(force=True)
    Thread(target=merge_video,
           args=(json['url'], json["screen_num"], json["cam_num"], json["record_name"],
                 json["room_id"], json["folder_id"], json['calendar_id'], json['event_id']),
           daemon=True
           ).start()
    return "Merge started", 200


@app.route('/merge-new', methods=["POST"])
def start_new_merge():
    json = request.get_json(force=True)
    print(json)
    if len(json['cameras']) != len(json['screens']):
        resp = {'error': 'The number of camera and screen files should be equal'}
        return jsonify(resp), 400
    try:
        get_video_by_name(json['cameras'][-1])
        get_video_by_name(json['screens'][-1])
    except:
        Thread(target=process_wait, kwargs={**json}, daemon=True).start()
        return "Videos haven't been uploaded yet", 200
    Thread(target=hstack_camera_and_screen,
           kwargs={**json}, daemon=True).start()
    return "Merge started", 200


if __name__ == '__main__':
    app.run()
