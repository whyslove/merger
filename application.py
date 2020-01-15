from threading import Thread

from merge import merge_video
from merge import merge_new
from flask import Flask, request, jsonify
from driveAPI import download_video, get_video_by_name

app = Flask("NVR_VIDEO_MERGE")


@app.route('/', methods=["GET", "POST"])
def main():
    return "Merge server v1.0", 200


@app.route('/merge', methods=["POST"])
def start_merge():
    json = request.get_json(force=True)
    Thread(target=merge_video,
           args=(json['url'], json["screen_num"],  json["cam_num"], json["record_name"],
                 json["room_id"], json["folder_id"], json['calendar_id'], json['event_id']),
           daemon=True
           ).start()
    return "Merge started", 200

@app.route('/merge/new', methods=["POST"])
def start_new_merge():
    json = request.get_json(force=True)
    if len(json['camera'])  != len(json['screen']):
        resp = {'error':'wrong amount of files'}
        return jsonify(resp), 400
    Thread(target=merge_new, args=(json,), daemon=True).start()
    return "Merge started", 200

#
#   {'camera' : ['1', '2', '3'],
#    'screen' : ['1', '2', '3'],
#       'url':'sjsj', 'room_id': ' ', 'folder_id': ' ', 'calendar_id': ' ', 'event_id': ' '
#  }
# 

if __name__ == '__main__':
    app.run()
