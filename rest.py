from threading import Thread

from flask import Flask, request, jsonify

from driveAPI import get_video_by_name
from merge import hstack_camera_and_screen, process_wait

app = Flask("NVR_VIDEO_MERGE")


@app.route('/', methods=["GET"])
def main():
    return "Merge server v2.0", 200


@app.route('/merge', methods=["POST"])
def start_new_merge():
    # TODO: переделать весь метод
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
        return "Videos are not uploaded yet", 200
    Thread(target=hstack_camera_and_screen,
           kwargs={**json}, daemon=True).start()
    return "Merge event added to queue", 201


if __name__ == '__main__':
    app.run()
