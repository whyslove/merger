from datetime import date

from flask import Flask, request, jsonify

from calendarAPI import get_events
from models import Session, Record, Room

app = Flask("NVR_VIDEO_MERGE")


@app.route('/', methods=["GET"])
def main():
    return "Merge server v2.0", 200


@app.route('/gcalendar-webhook', methods=["POST"])
def gcalendar_webhook():
    json_data = request.get_json()
    calendar_id = json_data['calendar_id']

    events = get_events(calendar_id)

    session = Session()
    room = session.query(Room).filter(Room.calendar == calendar_id).first()
    records = session.query(Record).filter(
        Record.room_name == room.name, Record.event_id != None).all()
    calendar_events = set(events.keys())
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
        new_record.update(**event, room_name=room.name)
        session.add(new_record)

    for event_id in events_to_check:
        event = events[event_id]
        if date.today().isoformat() != event['updated'].split('T')[0]:
            continue

        record = session.query(Record).filter(
            Record.event_id == event_id).first()
        record.update(**event, room_name=room.name)

    session.commit()
    session.close()

    return f"Room {room.name}: calendar events patched", 200


@app.route('/merge', methods=["POST"])
def start_new_merge():
    json = request.get_json()

    event_name = json.get("event_name")
    room_name = json.get("room_name")
    date = json.get("date")
    start_time = json.get("start_time")
    end_time = json.get("end_time")

    if not event_name:
        return jsonify({"error": "'event_name' required"}), 400
    if not room_name:
        return jsonify({"error": "'room_name' required"}), 400
    if not date:
        return jsonify({"error": "'date' required"}), 400
    if not start_time:
        return jsonify({"error": "'start_time' required"}), 400
    if not end_time:
        return jsonify({"error": "'end_time' required"}), 400

    record = Record(event_name=event_name, room_name=room_name, date=date,
                    start_time=start_time, end_time=end_time)

    session = Session()
    session.add(record)
    session.commit()
    session.close()

    return f"Merge event '{event_name}' added to queue", 201


if __name__ == '__main__':
    app.run()
