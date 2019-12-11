from threading import Thread

from merge import merge_video
from flask import Flask, request, jsonify

app = Flask("NVR_VIDEO_MERGE")


@app.route('/', methods=["GET", "POST"])
def main():
    return "Merge server v1.0", 200


@app.route('/merge', methods=["POST"])
def start_merge():
    json = request.get_json(force=True)
    Thread(target=merge_video,
           args=(json['url'], json["screen_num"], json["record_name"], json["record_num"],
                 json["room_id"], json['calendar_id'], json['event_id']),
           daemon=True
           ).start()
    # try:
    #     merge_video(json['url'], json["screen_num"], json["record_name"], json["record_num"],
    #                 json["room_id"], json['calendar_id'], json['event_id'])
    # except Exception as e:
    #     return jsonify({'error': str(e)}), 401

    return "Merge started", 200


if __name__ == '__main__':
    app.run()
