import os
import subprocess
from datetime import datetime
from pathlib import Path
from threading import RLock

from calendarAPI import add_attachment
from driveAPI import upload_video, download_video, get_video_by_name
from models import Record, Room

LOCK = RLock()
HOME = str(Path.home())


def get_dates_between_timestamps(start_timestamp: int, stop_timestamp: int) -> list:
    start_timestamp = start_timestamp // 1800 * 1800
    stop_timestamp = (stop_timestamp // 1800 + 1) * 1800 if int(
        stop_timestamp) % 1800 != 0 else (stop_timestamp // 1800) * 1800

    dates = []
    for timestamp in range(start_timestamp, stop_timestamp, 1800):
        dates.append(datetime.fromtimestamp(timestamp))

    return dates

# add smart merge


def get_files(record: Record, room: Room) -> tuple:
    cameras_file_name = f"cam_vids_to_merge_{record.start_time}_{record.end_time}.txt"
    screens_file_name = f"screen_vids_to_merge_{record.start_time}_{record.end_time}.txt"

    cams_file = open(cameras_file_name, "w")
    screens_file = open(screens_file_name, "w")

    date_time_start = datetime.strptime(
        f'{record.date} {record.start_time}', '%Y-%m-%d %H:%M')
    date_time_end = datetime.strptime(
        f'{record.date} {record.end_time}', '%Y-%m-%d %H:%M')

    start_timestamp = int(date_time_start.timestamp())
    end_timestamp = int(date_time_end.timestamp())

    dates = get_dates_between_timestamps(start_timestamp, end_timestamp)
    main_source = room.main_source.split('.')[-1].split('/')[0]
    screen_source = room.screen_source.split('.')[-1].split('/')[0]

    cam_file_names = [date.strftime(
        f"%Y-%m-%d_%H:%M_{room.name}_{main_source}.mp4") for date in dates]
    screen_file_names = [date.strftime(
        f"%Y-%m-%d_%H:%M_{room.name}_{screen_source}.mp4") for date in dates]

    for cam_file_name, screen_file_name in zip(cam_file_names, screen_file_names):
        cam_file_id = get_video_by_name(cam_file_name)
        download_video(cam_file_id, cam_file_name)

        screen_file_id = get_video_by_name(screen_file_name)
        download_video(screen_file_id, screen_file_name)

        cams_file.write(f"file '{HOME}/vids/{cam_file_name}'")
        screens_file.write(f"file '{HOME}/vids/{screen_file_name}'")

    cams_file.close()
    screens_file.close()

    rounded_start_time = cam_file_names[0].split("_")[1]
    rounded_end_time = cam_file_names[-1].split("_")[1]

    return cameras_file_name, screens_file_name, rounded_start_time, rounded_end_time


def create_merge(cameras_file_name: str, screens_file_name: str,
                 round_start_time: str, round_end_time: str,
                 start_time: str, end_time: str, folder_id: str,
                 calendar_id: str = None, event_id: str = None) -> None:
    with LOCK:
        cam_proc = subprocess.Popen(['ffmpeg', '-f', 'concat', '-safe', '0', '-i',
                                     f'{HOME}/vids/{cameras_file_name}',
                                     '-c', 'copy', f'{HOME}/vids/cam_result_{start_time}_{end_time}.mp4'])
        screen_proc = subprocess.Popen(['ffmpeg', '-f', 'concat', '-safe', '0', '-i',
                                        f'{HOME}/vids/{screens_file_name}',
                                        '-c', 'copy',
                                        f'{HOME}/vids/screen_result_{start_time}_{end_time}.mp4'])
        cam_proc.wait()
        screen_proc.wait()

        time_to_cut_1 = int(start_time.split(
            ':')[1]) - int(round_start_time.split(':')[1])
        time_to_cut_2 = int(round_end_time.split(
            ':')[1]) + 30 - int(end_time.split(':')[1])

        duration = len(open(cameras_file_name).readlines()) * \
            30 - time_to_cut_1 - time_to_cut_2

        hours = f'{duration // 60}' if (duration //
                                        60) > 9 else f'0{duration // 60}'
        minutes = f'{duration % 60}' if (
            duration % 60) > 9 else f'0{duration % 60}'
        vid_dur = f'{hours}:{minutes}:00'
        vid_start = f'00:{time_to_cut_1}:00' if time_to_cut_1 > 9 else f'00:0{time_to_cut_1}:00'
        cam_cutting = subprocess.Popen(['ffmpeg', '-ss', vid_start, '-t', vid_dur, '-i',
                                        f'{HOME}/vids/cam_result_{round_start_time}_{round_end_time}.mp4',
                                        '-c', 'copy',
                                        f'{HOME}/vids/cam_clipped_{start_time}_{end_time}.mp4'])
        os.system("renice -n 20 %s" % (cam_cutting.pid,))
        screen_cutting = subprocess.Popen(['ffmpeg', '-ss', vid_start, '-t', vid_dur, '-i',
                                           f'{HOME}/vids/screen_result_{round_start_time}_{round_end_time}.mp4',
                                           '-c', 'copy',
                                           f'{HOME}/vids/screen_clipped_{start_time}_{end_time}.mp4'])
        os.system("renice -n 20 %s" % (screen_cutting.pid,))
        screen_cutting.wait()
        cam_cutting.wait()
        os.remove(
            f'{HOME}/vids/cam_result_{round_start_time}_{round_end_time}.mp4')
        os.remove(
            f'{HOME}/vids/screen_result_{round_start_time}_{round_end_time}.mp4')
        os.remove(
            f'{HOME}/vids/vids_to_merge_cam_{round_start_time}_{round_end_time}.txt')
        os.remove(
            f'{HOME}/vids/vids_to_merge_screen_{round_start_time}_{round_end_time}.txt')

        # TODO 22.03.2020: remove origin 30m videos
        # for cam, screen in zip(cameras, screens):
        #     os.remove(f'{HOME}/vids/{cam}')
        #     os.remove(f'{HOME}/vids/{screen}')

        first = subprocess.Popen(['ffmpeg', '-i', f'{HOME}/vids/cam_clipped_{start_time}_{end_time}.mp4',
                                  '-i', f'{HOME}/vids/screen_clipped_{start_time}_{end_time}.mp4',
                                  '-filter_complex', 'hstack=inputs=2',
                                  f'{HOME}/vids/{start_time}_{end_time}_final.mp4'], shell=False)
        os.system("renice -n 20 %s" % (first.pid,))
        first.wait()
        os.remove(
            f'{HOME}/vids/cam_clipped_{start_time}_{end_time}.mp4')
        os.remove(
            f'{HOME}/vids/screen_clipped_{start_time}_{end_time}.mp4')
        try:
            file_id = upload_video(
                f'{HOME}/vids/{start_time}_{end_time}_final.mp4', folder_id)
            os.remove(
                f'{HOME}/vids/{start_time}_{end_time}_final.mp4')

            # TODO 22.03.2020: add link of the uploaded video to DB
        except Exception as e:
            print(e)

        if calendar_id:
            try:
                add_attachment(calendar_id,
                               event_id,
                               file_id)
            except Exception as e:
                print(e)
