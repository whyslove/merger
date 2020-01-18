from threading import Thread
from merge import hstack_camera_and_screen
from flask import Flask, request, jsonify

app = Flask("NVR_VIDEO_MERGE")


@app.route('/', methods=["GET", "POST"])
def main():
    return "Merge server v1.0", 200


@app.route('/merge', methods=["POST"])
def start_new_merge():
    json = request.get_json(force=True)
    print(json)
    if len(json['cameras']) != len(json['screens']):
        resp = {'error': 'The number of camera and screen files should be equal'}
        return jsonify(resp), 400
    Thread(target=hstack_camera_and_screen, kwargs={**json}, daemon=True).start()
    return "Merge started", 200

#
#   {
#    'camera' : ['1', '2', '3'],
#    'screen' : ['1', '2', '3'],
#    'folder_id': ' ',
#    'calendar_id': ' ',
#    'event_id': ' '
#   }
#


if __name__ == '__main__':
    app.run()
