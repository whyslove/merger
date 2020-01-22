import os
import subprocess
import requests
from pathlib import Path
from threading import RLock, Thread
from driveAPI import get_video_by_name, upload_video, download_video
import time

lock = RLock()
HOME = str(Path.home())
NVR_API_KEY = 'ce72d95a264248558f352768d620ca16'


def merge_video(client_url: str, screen_num: str,
                cam_num: str, record_name: str, room_id: int,
                folder_id: str, calendar_id: str, event_id: str) -> None:
    with lock:
        first = subprocess.Popen(["ffmpeg", "-i", HOME + "/vids/vid_" + cam_num + ".mp4", "-i", HOME + "/vids/vid_" +
                                  screen_num + ".mp4", "-filter_complex", "hstack=inputs=2", HOME + "/vids/vid_" +
                                  record_name + "merged.mp4"], shell=False)
        os.system("renice -n 20 %s" % (first.pid, ))
        first.wait()

    #    mid1 = subprocess.Popen(
    #         ["ffmpeg", "-i", HOME + "/vids/vid_" + screen_num + ".mp4", "-s", "hd720",
    #          HOME + "/vids/" + record_name + "mid_screen.mp4"], shell=False)
    #    os.system("renice -n 20 %s" % (mid1.pid,))
    #    mid1.wait()

    #    mid2 = subprocess.Popen(
    #         ["ffmpeg", "-i", HOME + "/vids/vid_" + cam_num + ".mp4", "-s", "hd720",
    #          HOME + "/vids/" + record_name + "mid_cam.mp4"], shell=False)
    #    os.system("renice -n 20 %s" % (mid2.pid,))
    #    mid2.wait()

    #    crop1 = subprocess.Popen(
    #         ["ffmpeg", "-i", HOME + "/vids/" + record_name + "mid_cam.mp4", "-filter:v", "crop=640:720:40:0",
    #          HOME + "/vids/" + record_name + "cropped_cam.mp4"], shell=False)

    #    os.system("renice -n 20 %s" % (crop1.pid,))
    #    crop1.wait()

    #    second = subprocess.Popen(
    #         ["ffmpeg", "-i", HOME + "/vids/" + record_name + "cropped_cam.mp4", "-i", HOME + "/vids/" +
    #          record_name + "mid_screen.mp4", "-filter_complex", "hstack=inputs=2", HOME + "/vids/vid_" +
    #          record_name + "merged.mp4"], shell=False)
    #    os.system("renice -n 20 %s" % (second.pid,))
    #    second.wait()

        res = ""
        if os.path.exists(HOME + "/vids/sound_" + record_name + ".aac"):
            add_sound(record_name +
                      "merged", record_name)
        else:
            res = "vid_"

        res = requests.post(client_url + "/upload-merged",
                            json={
                                "file_name": res + record_name + "merged.mp4",
                                "room_id": room_id,
                                "folder_id": folder_id,
                                "calendar_id": calendar_id,
                                "event_id": event_id
                            },
                            headers={'content-type': 'application/json',
                                     "key": NVR_API_KEY}
                            )
        print(res.json())


def hstack_camera_and_screen(cameras: list, screens: list,
                             start_time: str, end_time: str,
                             folder_id: str,
                             calendar_id: str = None, event_id: str = None) -> None:
    with lock:
        cameras.sort()
        screens.sort()
        round_start_time = cameras[0].split('_')[1]
        round_end_time = cameras[-1].split('_')[1]
        vids_to_merge_cam = open(
            f'{HOME}/vids/vids_to_merge_cam_{round_start_time}_{round_end_time}.txt', 'a')
        vids_to_merge_screen = open(
            f'{HOME}/vids/vids_to_merge_screen_{round_start_time}_{round_end_time}.txt', 'a')
        log = {'errors':0}
        for cam, screen in zip(cameras, screens):
            cam_file_id = get_video_by_name(cam)
            download_video(cam_file_id, cam)
            vids_to_merge_cam.write(f"file '{HOME}/vids/{cam}'\n")
            screen_file_id = get_video_by_name(screen)
            download_video(screen_file_id, screen)
            vids_to_merge_screen.write(f"file '{HOME}/vids/{screen}'\n")
        vids_to_merge_cam.close()
        vids_to_merge_screen.close()

        cam_proc = subprocess.Popen(['ffmpeg', '-f', 'concat', '-safe', '0', '-i',
                                     f'{HOME}/vids/vids_to_merge_cam_{round_start_time}_{round_end_time}.txt',
                                     '-c', 'copy', f'{HOME}/vids/cam_result_{round_start_time}_{round_end_time}.mp4'])
        screen_proc = subprocess.Popen(['ffmpeg', '-f', 'concat', '-safe', '0', '-i',
                                        f'{HOME}/vids/vids_to_merge_screen_{round_start_time}_{round_end_time}.txt',
                                        '-c', 'copy', f'{HOME}/vids/screen_result_{round_start_time}_{round_end_time}.mp4'])
        cam_proc.wait()
        screen_proc.wait()

        time_to_cut_1 = int(start_time.split(':')[1]) - int(round_start_time.split(':')[1])
        time_to_cut_2 = int(round_end_time.split(':')[1]) + 30 - int(end_time.split(':')[1])
        duration = len(cameras) * 30 - time_to_cut_1 - time_to_cut_2
        hours = f'{duration // 60}' if (duration //60) > 9 else f'0{duration // 60}'
        minutes = f'{duration % 60}' if (duration % 60) > 9 else f'0{duration % 60}'
        vid_dur = f'{hours}:{minutes}:00'
        vid_start = f'00:{time_to_cut_1}:00' if t1 > 9 else f'00:0{time_to_cut_1}:00'
        cam_cutting = subprocess.Popen(['ffmpeg', '-ss', vid_start, '-t', vid_dur, '-i',  f'{HOME}/vids/cam_result_{round_start_time}_{round_end_time}.mp4',
                                   '-vcodec', 'copy', '-acodec', 'copy',  f'{HOME}/vids/cam_clipped_{start_time}_{end_time}.mp4'])
        os.system("renice -n 20 %s" % (cam_cutting.pid, ))
        screen_cutting = subprocess.Popen(['ffmpeg', '-ss', vid_start, '-t', vid_dur, '-i',  f'{HOME}/vids/screen_result_{round_start_time}_{round_end_time}.mp4',
                                   '-vcodec', 'copy', '-acodec', 'copy',  f'{HOME}/vids/screen_clipped_{start_time}_{end_time}.mp4'])
        os.system("renice -n 20 %s" % (screen_cutting.pid, ))
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
        for cam, screen in cameras, screens:
            os.remove(f'{HOME}/vids/{cam}')
            os.remove(f'{HOME}/vids/{screen}')

        first = subprocess.Popen(['ffmpeg', '-i', f'{HOME}/vids/cam_clipped_{start_time}_{end_time}.mp4',
                                  '-i', f'{HOME}/vids/screen_clipped_{start_time}_{end_time}.mp4',
                                  '-filter_complex', 'hstack=inputs=2', f'{HOME}/vids/{start_time}_{end_time}_final.mp4'], shell=False)
        os.system("renice -n 20 %s" % (first.pid, ))
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
        except Exception as e:
            print(e)

        if calendar_id:
            try:
                add_attachment(calendar_id,
                               event_id,
                               file_id)
            except Exception as e:
                print(e)


def process_wait(cameras: list, screens: list,
                             start_time: str, end_time: str,
                             folder_id: str,
                             calendar_id: str = None, event_id: str = None):
    while True:
        try:
            get_video_by_name(cameras.sort()[-1])
            get_video_by_name(screens.sort()[-1])
            hstack_camera_and_screen(cameras, screens, start_time, end_time, folder_id, calendar_id, event_id)
            break
        except:
            time.sleep(300)
        
