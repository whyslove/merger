import os
import subprocess
import requests
from pathlib import Path
from threading import RLock, Thread
from driveAPI import get_video_by_name, upload_video, download_video

lock = RLock()
home = str(Path.home())


def hstack_camera_and_screen(cameras: list, screens: list,
                             start_time: str, end_time: str,
                             folder_id: str,
                             calendar_id: str = None, event_id: str = None) -> None:
    cam = sorted(cameras)
    round_start_time = cam[0].split('_')[1]
    round_end_time = cam[-1].split('_')[1]
    slides = sorted(screens)
    vids_to_merge_cam = open(
        f'{home}/vids/vids_to_merge_cam_{round_start_time}_{round_end_time}.txt', 'a')
    vids_to_merge_sld = open(
        f'{home}/vids/vids_to_merge_sld_{round_start_time}_{round_end_time}.txt', 'a')
    for i in range(len(cam)):
        cam_file_id = get_video_by_name(cam[i])
        download_video(cam_file_id, cam[i])
        vids_to_merge_cam.write(f"file '{home}/vids/{cam[i]}'\n")
        sld_file_id = get_video_by_name(slides[i])
        download_video(sld_file_id, slides[i])
        vids_to_merge_sld.write(f"file '{home}/vids/{slides[i]}'\n")
    vids_to_merge_cam.close()
    vids_to_merge_sld.close()
    cam_proc = subprocess.Popen(['ffmpeg', '-f', 'concat', '-safe', '0', '-i',
                                 f'{home}/vids/vids_to_merge_cam_{round_start_time}_{round_end_time}.txt', '-c', 'copy', f'{home}/vids/cam_result_{round_start_time}_{round_end_time}.mp4'])
    sld_proc = subprocess.Popen(['ffmpeg', '-f', 'concat', '-safe', '0', '-i',
                                 f'{home}/vids/vids_to_merge_sld_{round_start_time}_{round_end_time}.txt', '-c', 'copy', f'{home}/vids/sld_result_{round_start_time}_{round_end_time}.mp4'])
    cam_proc.wait()
    sld_proc.wait()
    for vid in cam:
        os.remove(f'{home}/vids/{vid}')
    for vid in slides:
        os.remove(f'{home}/vids/{vid}')
    first = subprocess.Popen(['ffmpeg', '-i', f'{home}/vids/cam_result_{round_start_time}_{round_end_time}.mp4', '-i', f'{home}/vids/sld_result_{round_start_time}_{round_end_time}.mp4',
                              '-filter_complex', 'hstack=inputs=2', f'{home}/vids/{round_start_time}_{round_end_time}_merged.mp4'], shell=False)
    os.system("renice -n 20 %s" % (first.pid, ))
    first.wait()
    os.remove(f'{home}/vids/cam_result_{round_start_time}_{round_end_time}.mp4')
    os.remove(f'{home}/vids/sld_result_{round_start_time}_{round_end_time}.mp4')
    t1 = int(start_time.split(':')[1]) - \
        int(round_start_time.split(':')[1])
    t2 = int(round_end_time.split(':')[1]) + 30 - \
        int(end_time.split(':')[1])
    duration = len(cam) * 30 - t1 - t2
    hours = f'{duration // 60}' if (duration //
                                    60) > 9 else f'0{duration // 60}'
    minutes = f'{duration % 60}' if (
        duration % 60) > 9 else f'0{duration % 60}'
    d = f'{hours}:{minutes}:00'
    st = f'00:{t1}:00' if t1 > 9 else f'00:0{t1}:00'
    second = subprocess.Popen(['ffmpeg', '-ss', st, '-t', d, '-i', f'{home}/vids/{round_start_time}_{round_end_time}_merged.mp4',
                               '-vcodec', 'copy', '-acodec', 'copy', f'{home}/vids/{round_start_time}_{round_end_time}_final.mp4'])
    os.system("renice -n 20 %s" % (second.pid, ))
    second.wait()
    os.remove(f'{home}/vids/{round_start_time}_{round_end_time}_merged.mp4')

    try:
        file_id = upload_video(
            f'{home}/vids/{round_start_time}_{round_end_time}_final.mp4', folder_id)
        os.remove(f'{home}/vids/{round_start_time}_{round_end_time}_final.mp4')
    except Exception as e:
        print(e)

    if calendar_id:
        try:
            add_attachment(calendar_id,
                           event_id,
                           file_id)
        except Exception as e:
            print(e)
