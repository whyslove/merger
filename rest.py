from threading import Thread

from flask import Flask, request, jsonify

from driveAPI import get_video_by_name
from calendarAPI import get_events
from merge import hstack_camera_and_screen, process_wait
from models import Session, Record

app = Flask("NVR_VIDEO_MERGE")


@app.route('/', methods=["GET"])
def main():
    return "Merge server v2.0", 200


@app.route('/gcalendar-webhook', methods=["POST"])
def gcalendar_webhook():
    json_data = request.get_json()
    calendar_id = json_data['calendar_id']

    events, calendar = get_events(calendar_id)
    room_name = calendar['summary']

    session = Session()
    records = session.query(Record).filter(
        Record.room_name == room_name, Record.event_id != None).all()
    calendar_events = events.keys()
    db_events = {record.event_id for record in records}

    new_events = calendar_events - db_events
    deleted_events = db_events - calendar_events
    events_to_check = calendar_events & db_events

    for event_id in deleted_events:
        record = session.query(Record).filter(
            Record.event_id == event_id).first()
        session.delete(record)

    for event_id in new_events:
        event = events[event_id]
        start_date = event['start']['dateTime'].split('T')[0]
        end_date = event['end']['dateTime'].split('T')[0]
        if start_date != end_date:
            continue
        new_record = Record()
        new_record.event_id = event['id']
        new_record.event_src = event['htmlLink']
        new_record.event_name = event.get('summary')
        new_record.date = start_date
        new_record.start_time = event['start']['dateTime'].split('T')[1][:5]
        new_record.end_time = event['end']['dateTime'].split('T')[1][:5]
        new_record.room_name = room_name
        new_record.folder_id = ''

        session.add(new_record)

    for event_id in events_to_check:
        # TODO
        pass

    session.commit()
    session.close()
    return "", 200


@app.route('/merge', methods=["POST"])
def start_new_merge():
    # TODO: переделать весь метод
    json = request.get_json(force=True)
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
