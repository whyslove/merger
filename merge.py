import os
import subprocess
import time
from pathlib import Path
from threading import RLock, Thread

from calendarAPI import add_attachment
from driveAPI import get_video_by_name, upload_video, download_video

lock = RLock()
HOME = str(Path.home())


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
                                        '-c', 'copy',
                                        f'{HOME}/vids/screen_result_{round_start_time}_{round_end_time}.mp4'])
        cam_proc.wait()
        screen_proc.wait()

        time_to_cut_1 = int(start_time.split(
            ':')[1]) - int(round_start_time.split(':')[1])
        time_to_cut_2 = int(round_end_time.split(
            ':')[1]) + 30 - int(end_time.split(':')[1])
        duration = len(cameras) * 30 - time_to_cut_1 - time_to_cut_2
        hours = f'{duration // 60}' if (duration //
                                        60) > 9 else f'0{duration // 60}'
        minutes = f'{duration % 60}' if (
                                                duration % 60) > 9 else f'0{duration % 60}'
        vid_dur = f'{hours}:{minutes}:00'
        vid_start = f'00:{time_to_cut_1}:00' if time_to_cut_1 > 9 else f'00:0{time_to_cut_1}:00'
        cam_cutting = subprocess.Popen(['ffmpeg', '-ss', vid_start, '-t', vid_dur, '-i',
                                        f'{HOME}/vids/cam_result_{round_start_time}_{round_end_time}.mp4',
                                        '-vcodec', 'copy', '-acodec', 'copy',
                                        f'{HOME}/vids/cam_clipped_{start_time}_{end_time}.mp4'])
        os.system("renice -n 20 %s" % (cam_cutting.pid,))
        screen_cutting = subprocess.Popen(['ffmpeg', '-ss', vid_start, '-t', vid_dur, '-i',
                                           f'{HOME}/vids/screen_result_{round_start_time}_{round_end_time}.mp4',
                                           '-vcodec', 'copy', '-acodec', 'copy',
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
        for cam, screen in zip(cameras, screens):
            os.remove(f'{HOME}/vids/{cam}')
            os.remove(f'{HOME}/vids/{screen}')

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
                 calendar_id: str = None, event_id: str = None) -> None:
    last_cam = sorted(cameras)[-1]
    last_screen = sorted(screens)[-1]
    while True:
        try:
            get_video_by_name(last_cam)
            get_video_by_name(last_screen)
            Thread(target=hstack_camera_and_screen,
                   args=(cameras, screens,
                         start_time, end_time,
                         folder_id,
                         calendar_id, event_id), daemon=True).start()
            break
        except Exception as e:
            time.sleep(300)
