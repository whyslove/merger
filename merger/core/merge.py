import logging
import os
import subprocess
import time
from datetime import datetime, timedelta
from pathlib import Path

import html2text
from PIL import Image, ImageChops

from .apis.driveAPI import download_video, get_video_by_name
from .db.models import Record, Room

HOME = str(Path.home())

logger = logging.getLogger('merger_logger')


class Merge:
    def __init__(self, record: Record, room: Room):
        self.start_time = record.start_time
        self.end_time = record.end_time
        self.round_start_time = None
        self.round_end_time = None
        self.event_name = record.event_name
        self.cameras_file_name = f"cam_vids_to_merge_{self.start_time}_{self.end_time}.txt"
        self.screens_file_name = f"screen_vids_to_merge_{self.start_time}_{self.end_time}.txt"

        self.got_all_screens = True

        cam_file_names, screen_file_names, reserve_cam_file_names, date_time_end \
            = self.get_file_names(record.date, room)

        for cam_file_name, screen_file_name, reserve_cam_file_name in zip(cam_file_names, screen_file_names,
                                                                          reserve_cam_file_names):
            reserve_cam_file_id = self.screen_videos_check(
                cam_file_name, screen_file_name, reserve_cam_file_name, date_time_end)

            if not reserve_cam_file_id:
                self.screen_stream_check(
                    screen_file_name, reserve_cam_file_name)

        self.round_start_time = cam_file_names[0].split("_")[1]

        if len(cam_file_names) > 1:
            temp_time = datetime.strptime(
                cam_file_names[-1].split("_")[1], "%H:%M") + timedelta(hours=0, minutes=30)

            self.round_end_time = temp_time.strftime("%H:%M")
        else:
            self.round_end_time = self.end_time

    def create_lecture(self) -> tuple:
        logger.info("No presentation -- concat video and upload")

        self.concat_process(self.cameras_file_name, "cam")
        logger.info(f'Finished concatenating videos '
                    f'cam_result_{self.round_start_time}_{self.round_end_time}.mp4')

        vid_start, vid_dur = self.count_duration()
        logger.info(
            f'For {self.event_name} vid_start = {vid_start}, vid_dur = {vid_dur}')

        self.cutting_process("cam", vid_start, vid_dur)
        logger.info(
            f'Finished cutting videos cam_clipped_{self.start_time}_{self.end_time}.mp4')

        self.remove_intermediate_videos(self.cameras_file_name)
        self.remove_file(
            f'{HOME}/vids/cam_result_{self.round_start_time}_{self.round_end_time}.mp4')

        file_name = f'{self.start_time}_{self.end_time}.mp4'
        file_name = f'{self.event_name.replace(" ", "_")}_{file_name}'

        os.rename(f'{HOME}/vids/cam_clipped_{self.start_time}_{self.end_time}.mp4',
                  f'{HOME}/vids/{file_name}')
        self.remove_file(
            f'{HOME}/vids/cam_clipped_{self.start_time}_{self.end_time}.mp4')

        return (file_name)

    def create_merge(self) -> tuple:
        if not self.got_all_screens:
            return self.create_lecture()

        logger.info("Got presentation -- concat videos, merge and upload")

        self.concat_process(self.cameras_file_name, "cam")
        self.concat_process(self.screens_file_name, "screen")

        logger.info(f'Finished concatenating videos '
                    f'cam_result_{self.round_start_time}_{self.round_end_time}.mp4 and '
                    f'screen_result_{self.round_start_time}_{self.round_end_time}.mp4')

        vid_start, vid_dur = self.count_duration()
        logger.info(
            f'For {self.event_name} vid_start = {vid_start}, vid_dur = {vid_dur}')

        self.cutting_process("cam", vid_start, vid_dur)
        self.cutting_process("screen", vid_start, vid_dur)

        logger.info(f'Finished cutting videos cam_clipped_{self.start_time}_{self.end_time}.mp4 and '
                    f'screen_clipped_{self.start_time}_{self.end_time}.mp4')

        self.remove_intermediate_videos(self.cameras_file_name)
        self.remove_intermediate_videos(self.screens_file_name)
        self.remove_file(
            f'{HOME}/vids/cam_result_{self.round_start_time}_{self.round_end_time}.mp4')
        self.remove_file(
            f'{HOME}/vids/screen_result_{self.round_start_time}_{self.round_end_time}.mp4')

        self.hstack_process()

        logger.info(
            f'Finished merging video {self.start_time}_{self.end_time}_final.mp4')

        self.remove_file(
            f'{HOME}/vids/cam_clipped_{self.start_time}_{self.end_time}.mp4')

        file_name = f'{self.start_time}_{self.end_time}.mp4'
        backup_file_name = f'{self.start_time}_{self.end_time}_backup.mp4'

        if self.event_name is not None:
            file_name = f'{self.event_name.replace(" ", "_")}_' + file_name
            backup_file_name = f'{self.event_name.replace(" ", "_")}_' + \
                               backup_file_name

        try:
            os.rename(f'{HOME}/vids/{self.start_time}_{self.end_time}_final.mp4',
                      f'{HOME}/vids/{file_name}')
            os.rename(f'{HOME}/vids/screen_clipped_{self.start_time}_{self.end_time}.mp4',
                      f'{HOME}/vids/{backup_file_name}')
        except OSError:
            raise RuntimeError

        return file_name, backup_file_name

    def get_file_names(self, date: str, room: Room) -> tuple:
        date_time_start = datetime.strptime(
            f'{date} {self.start_time}', '%Y-%m-%d %H:%M')
        date_time_end = datetime.strptime(
            f'{date} {self.end_time}', '%Y-%m-%d %H:%M')

        start_timestamp = int(date_time_start.timestamp())
        end_timestamp = int(date_time_end.timestamp())

        dates = self.get_dates_between_timestamps(
            start_timestamp, end_timestamp)
        main_source = room.main_source.split('.')[-1].split('/')[0]
        screen_source = room.screen_source.split('.')[-1].split('/')[0]

        reserve_cam = next(
            source for source in room.sources if source.merge.endswith('right'))
        backup_source = reserve_cam.ip.split('.')[-1]

        cam_file_names = [date.strftime(
            f"%Y-%m-%d_%H:%M_{room.name}_{main_source}.mp4") for date in dates]
        screen_file_names = [date.strftime(
            f"%Y-%m-%d_%H:%M_{room.name}_{screen_source}.mp4") for date in dates]
        reserve_cam_file_names = [date.strftime(
            f"%Y-%m-%d_%H:%M_{room.name}_{backup_source}.mp4") for date in dates]
        return cam_file_names, screen_file_names, reserve_cam_file_names, date_time_end

    def screen_videos_check(self, cam_file_name, screen_file_name, reserve_cam_file_name, date_time_end) -> str:
        reserve_cam_file_id = ""

        cams_file = open(f'{HOME}/vids/{self.cameras_file_name}', "a")
        screens_file = open(f'{HOME}/vids/{self.screens_file_name}', "a")

        try:
            cam_file_id = get_video_by_name(cam_file_name)
            download_video(cam_file_id, cam_file_name)
            cams_file.write(f"file '{HOME}/vids/{cam_file_name}'\n")

            try:
                screen_file_id = get_video_by_name(screen_file_name)
                download_video(screen_file_id, screen_file_name)
            except:
                logger.info(f'Screen video {screen_file_name} not found')

                reserve_cam_file_id = get_video_by_name(reserve_cam_file_name)
                download_video(reserve_cam_file_id, reserve_cam_file_name)
                screens_file.write(
                    f"file '{HOME}/vids/{reserve_cam_file_name}'\n")
        except:
            logger.error("Files not found:", cam_file_name,
                         screen_file_name, reserve_cam_file_name)

            if (datetime.now() - date_time_end).total_seconds() // 3600 >= 1:
                raise RuntimeError
        finally:
            cams_file.close()
            screens_file.close()

        return reserve_cam_file_id

    def screen_stream_check(self, screen_file_name: str, reserve_cam_file_name: str) -> None:
        log_file = open(f"/var/log/merger/frame_cut_log.txt", "a")

        cut_proc = subprocess.Popen(['ffmpeg', '-ss', '00:00:01', '-i',
                                     f'{HOME}/vids/{screen_file_name}',
                                     '-frames:', '1', '-y', f'{HOME}/vids/cutted_frame.png', ],
                                    stdout=log_file,
                                    stderr=log_file)
        cut_proc.wait()
        log_file.close()

        im_example = Image.open("/merger/core/example.png")
        im_cutted = Image.open(f"{HOME}/vids/cutted_frame.png")

        screens_file = open(f'{HOME}/vids/{self.screens_file_name}', "a")

        try:
            ImageChops.difference(im_example, im_cutted).getbbox() is None
        except:
            logger.info(f"Merging with presentation: {self.screens_file_name}")
            screens_file.write(f"file '{HOME}/vids/{screen_file_name}'\n")
        else:
            logger.info(
                f"No presentation provided, merging with {reserve_cam_file_name}")
            reserve_cam_file_id = get_video_by_name(reserve_cam_file_name)
            download_video(reserve_cam_file_id, reserve_cam_file_name)
            screens_file.write(
                f"file '{HOME}/vids/{reserve_cam_file_name}'\n")

        screens_file.close()
        im_example.close()
        im_cutted.close()

    def concat_process(self, file_name: str, source_type: str) -> None:
        log_file = open(f"/var/log/merger/concat_log_{source_type}.txt", "a")

        process = subprocess.Popen(['ffmpeg', '-f', 'concat', '-safe', '0', '-i',
                                    f'{HOME}/vids/{file_name}', '-y',
                                    f'-c', 'copy',
                                    f'{HOME}/vids/'
                                    f'{source_type}_result_{self.round_start_time}_{self.round_end_time}.mp4'],
                                   stdout=log_file,
                                   stderr=log_file)
        process.wait()
        log_file.close()

    def count_duration(self) -> tuple:
        time_to_cut_1 = abs(int((time.mktime(time.strptime(self.start_time, '%H:%M')) -
                                 time.mktime(time.strptime(self.round_start_time, '%H:%M'))) // 60))
        time_to_cut_2 = abs(int((time.mktime(time.strptime(self.end_time, '%H:%M')) -
                                 time.mktime(time.strptime(self.round_end_time, '%H:%M'))) // 60))

        with open(f'{HOME}/vids/{self.cameras_file_name}') as cams_file:
            duration = len(cams_file.readlines()) * 30 - \
                time_to_cut_1 - time_to_cut_2

        hours = f'{duration // 60}' if (duration //
                                        60) > 9 else f'0{duration // 60}'
        minutes = f'{duration % 60}' if (
            duration % 60) > 9 else f'0{duration % 60}'
        vid_dur = f'{hours}:{minutes}:00'
        vid_start = f'00:{time_to_cut_1}:00' if time_to_cut_1 > 9 else f'00:0{time_to_cut_1}:00'

        logger.info(f"For {self.cameras_file_name}: "
                    f"start_time = {self.start_time}, round_start_time = {self.round_start_time}, "
                    f"end_time = {self.end_time}, round_end_time = {self.round_end_time}, "
                    f"time_to_cut_1 = {time_to_cut_1}, time_to_cut_2 = {time_to_cut_2}, "
                    f"duration = {duration}, vid_start = {vid_start}, vid_dur = {vid_dur}")

        return vid_start, vid_dur

    def cutting_process(self, source_type: str, vid_start: str, vid_dur: str) -> None:
        log_file = open(f"/var/log/merger/cutting_log_{source_type}.txt", "a")

        process = subprocess.Popen(['ffmpeg', '-ss', vid_start, '-t', vid_dur, '-i',
                                    f'{HOME}/vids/'
                                    f'{source_type}_result_{self.round_start_time}_{self.round_end_time}.mp4',
                                    f'-y', '-c', 'copy',
                                    f'{HOME}/vids/'
                                    f'{source_type}_clipped_{self.start_time}_{self.end_time}.mp4'],
                                   stdout=log_file,
                                   stderr=log_file)
        process.wait()
        log_file.close()

    def remove_intermediate_videos(self, sources_file_name):
        with open(f'{HOME}/vids/{sources_file_name}', "r") as file:
            for line in file.readlines():
                self.remove_file(line.split(' ')[-1].split('\'')[1])

        self.remove_file(
            f'{HOME}/vids/{sources_file_name}')

    def hstack_process(self):
        log_file = open(f"/var/log/merger/hstack_log.txt", "a")

        process = subprocess.Popen(['ffmpeg', '-i', f'{HOME}/vids/cam_clipped_{self.start_time}_{self.end_time}.mp4',
                                    '-i', f'{HOME}/vids/screen_clipped_{self.start_time}_{self.end_time}.mp4',
                                    '-filter_complex', 'hstack=inputs=2', '-y',
                                    f'{HOME}/vids/{self.start_time}_{self.end_time}_final.mp4'],
                                   shell=False,
                                   stdout=log_file,
                                   stderr=log_file)
        process.wait()
        log_file.close()

    @staticmethod
    def get_dates_between_timestamps(start_timestamp: int, stop_timestamp: int) -> list:
        start_timestamp = start_timestamp // 1800 * 1800
        stop_timestamp = (stop_timestamp // 1800 + 1) * 1800 if int(
            stop_timestamp) % 1800 != 0 else (stop_timestamp // 1800) * 1800

        dates = []
        for timestamp in range(start_timestamp, stop_timestamp, 1800):
            dates.append(datetime.fromtimestamp(timestamp))

        return dates

    @staticmethod
    def parse_description(description_raw: str) -> dict:
        logger.info(f'Started parsing description: {description_raw}')

        htm = html2text.HTML2Text()
        htm.ignore_links = True

        if '\n' not in description_raw:
            description_raw = htm.handle(description_raw)

        description_json = {}
        for row in description_raw.split('\n'):
            row_data = row.split(':')
            if len(row_data) == 2:
                key, value = row_data
                description_json[key.strip().lower()] = value.strip()

        return description_json

    @staticmethod
    def remove_file(filename: str) -> None:
        try:
            os.remove(filename)
        except FileNotFoundError:
            logger.warning(f'Failed to remove file {filename}')
        except:
            logger.error(
                f'Failed to remove file {filename}', exc_info=True)
