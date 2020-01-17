import os
import subprocess
import requests
from pathlib import Path
from threading import Lock
from driveAPI import *

lock = Lock()
home = str(Path.home())

NVR_API_KEY = 'ce72d95a264248558f352768d620ca16'


def merge_video(client_url: str, screen_num: str, cam_num: str, record_name: str, room_id: int, folder_id: str, calendar_id: str, event_id: str) -> None:
    with lock:

        first = subprocess.Popen(["ffmpeg", "-i", home + "/vids/vid_" + cam_num + ".mp4", "-i", home + "/vids/vid_" +
                                  screen_num + ".mp4", "-filter_complex", "hstack=inputs=2", home + "/vids/vid_" +
                                  record_name + "merged.mp4"], shell=False)
        os.system("renice -n 20 %s" % (first.pid, ))
        first.wait()

    #    mid1 = subprocess.Popen(
    #         ["ffmpeg", "-i", home + "/vids/vid_" + screen_num + ".mp4", "-s", "hd720",
    #          home + "/vids/" + record_name + "mid_screen.mp4"], shell=False)
    #    os.system("renice -n 20 %s" % (mid1.pid,))
    #    mid1.wait()

    #    mid2 = subprocess.Popen(
    #         ["ffmpeg", "-i", home + "/vids/vid_" + cam_num + ".mp4", "-s", "hd720",
    #          home + "/vids/" + record_name + "mid_cam.mp4"], shell=False)
    #    os.system("renice -n 20 %s" % (mid2.pid,))
    #    mid2.wait()

    #    crop1 = subprocess.Popen(
    #         ["ffmpeg", "-i", home + "/vids/" + record_name + "mid_cam.mp4", "-filter:v", "crop=640:720:40:0",
    #          home + "/vids/" + record_name + "cropped_cam.mp4"], shell=False)

    #    os.system("renice -n 20 %s" % (crop1.pid,))
    #    crop1.wait()

    #    second = subprocess.Popen(
    #         ["ffmpeg", "-i", home + "/vids/" + record_name + "cropped_cam.mp4", "-i", home + "/vids/" +
    #          record_name + "mid_screen.mp4", "-filter_complex", "hstack=inputs=2", home + "/vids/vid_" +
    #          record_name + "merged.mp4"], shell=False)
    #    os.system("renice -n 20 %s" % (second.pid,))
    #    second.wait()

        res = ""
        if os.path.exists(home + "/vids/sound_" + record_name + ".aac"):
            add_sound(record_name +
                      "merged", record_name)
        else:
            res = "vid_"

        res = requests.post(client_url + "/upload-merged",
                            json={
                                "file_name": res + record_name + "merged.mp4",
                                "room_id": room_id,
                                "folder_id" : folder_id,
                                "calendar_id": calendar_id,
                                "event_id": event_id
                            },
                            headers={'content-type': 'application/json',
                                     "key": NVR_API_KEY}
                            )
        print(res.json())


def add_sound(record_name: str, audio_cam_num: str) -> None:
    proc = subprocess.Popen(["ffmpeg", "-i", home + "/vids/sound_" + audio_cam_num + ".aac", "-i",
                             home + "/vids/vid_" + record_name +
                             ".mp4", "-y", "-shortest", "-c", "copy",
                             home + "/vids/" + record_name + ".mp4"], shell=False)
    proc.wait()

def merge_new(files: dict):
    cam = sorted(files['camera'])
    start_time = cam[0].split('_')[1]
    end_time = cam[-1].split('_')[1]
    slides = sorted(files['screen'])
    vids_to_merge_cam = open(f'{home}/vids/vids_to_merge_cam_{start_time}_{end_time}.txt', 'a')
    vids_to_merge_sld = open(f'{home}/vids/vids_to_merge_sld_{start_time}_{end_time}.txt', 'a')
    for i in range(len(cam)):
        cam_file_id = get_video_by_name(cam[i])
        thread1 = Thread(target=download_video, args=(cam_file_id, cam[i],))
        thread1.start()
        vids_to_merge_cam.write(f"file '{home}/vids/{cam[i]}'\n")
        sld_file_id = get_video_by_name(slides[i])
        thread2 = Thread(target=download_video, args=(sld_file_id, slides[i],))
        thread2.start()
        vids_to_merge_sld.write(f"file '{home}/vids/{slides[i]}'\n")
        thread1.join()
        thread2.join()
    vids_to_merge_cam.close()
    vids_to_merge_sld.close()
    cam_proc = subprocess.Popen(['ffmpeg', '-f', 'concat', '-safe', '0', '-i', f'{home}/vids/vids_to_merge_cam_{start_time}_{end_time}.txt', '-c','copy', f'{home}/vids/cam_result_{start_time}_{end_time}.mp4'])
    sld_proc = subprocess.Popen(['ffmpeg', '-f', 'concat', '-safe', '0', '-i', f'{home}/vids/vids_to_merge_sld_{start_time}_{end_time}.txt', '-c', 'copy', f'{home}/vids/sld_result_{start_time}_{end_time}.mp4'])
    cam_proc.wait()
    sld_proc.wait()
    for vid in cam:
        os.remove(vid)
    for vid in slides:
        os.remove(vid)
    first = subprocess.Popen(['ffmpeg', '-i', f'{home}/vids/cam_result_{start_time}_{end_time}.mp4', '-i', f'{home}/vids/sld_result_{start_time}_{end_time}.mp4', '-filter_complex', 'hstack=inputs=2', f'{home}/vids/{start_time}_{end_time}_merged.mp4'], shell=False)
    os.system("renice -n 20 %s" % (first.pid, ))
    first.wait()
    os.remove(f'{home}/vids/cam_result_{start_time}_{end_time}.mp4')
    os.remove(f'{home}/vids/sld_result_{start_time}_{end_time}.mp4')
    t1 = int(files['start'].split(':')[1]) - int(start_time.split(':')[1])
    t2 = int(end_time.split(':')[1]) + 30 - int(files['end'].split(':')[1])
    duration =  len(cam) * 30 - t1 - t2
    if (duration // 60) > 9:
        d = f'{duration//60}:{duration%60}:00'
    else:
        d = f'0{duration//60}:{duration%60}:00'
    if t1 > 9:
        st = f'00:{t1}:00'
    else:
        st = f'00:0{t1}:00'
    second = subprocess.Popen(['ffmpeg', '-ss', st, '-t', d, '-i', f'{home}/vids/{start_time}_{end_time}_merged.mp4', '-vcodec', 'copy', '-acodec', 'copy', f'{home}/vids/{start_time}_{end_time}_final.mp4'])
    os.system("renice -n 20 %s" % (second.pid, ))
    second.wait()
    # res = requests.post(files['url'] + "/upload-merged",
    #                 json={
    #                     "file_name": f"{start_time}_{end_time}_merged.mp4",
    #                     "room_id": files['room_id'],
    #                     "folder_id" : files['folder_id'],
    #                     "calendar_id": files['calendar_id'],
    #                     "event_id": files['event_id']
    #                 },
    #                 headers={'content-type': 'application/json',
    #                             "key": NVR_API_KEY}
    #                 )
    # print(res.json())

# merge_new({'camera':['2019-12-20_15:10_504_136'], 'screen':['2019-12-20_15:10_504_12']})

