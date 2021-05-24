import asyncio
from datetime import datetime
from asyncio.events import set_event_loop
from logging import log
from pathlib import Path

from requests.api import request
import aiohttp

from uuid import uuid4
from loguru import logger

from db.ff_commands import (
    mkdir,
    rmdir,
    cut,
    concat,
    ffmpeg_hstack,
    ffmpeg_vstack,
    get_roles_for_merge_type,
)
from apis.erudite_api import Erudite as Nvr_db
from apis.driveAPI import download_video

token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOnsiZW1haWwiOiJzdnZveWxvdkBtaWVtLmhzZS5ydSIsInJvbGUiOiJhZG1pbiIsIm9yZ19uYW1lIjoiXHUwNDFjXHUwNDE4XHUwNDJkXHUwNDFjIn0sImlhdCI6MTYxNTkxNTAxMywiZXhwIjoxNjIzMTcyNjEzfQ.sR6_akiOiPq0mMFl84igjY1piLquE43xcDiVSMy743E"
input_message = {
    "room_name": "307",
    "date": "2021-05-13",
    "start_time": "15:10",
    "end_time": "15:25",
    "id": "609709bbd05edc45876e4eaf",
}
ERUDITE_URL = "https://nvr.miem.hse.ru/api/erudite"


def get_id_form_url(url: str) -> str:
    """Parse a certain type gdrive url to return an id from it"""
    return url.split("/file/d/")[1].split("/preview")[0]


def patch_emotion_records(records: list):
    """To perfom a unified interface for downloading videos needed to save video url in 'url' key.
    But emotions have url in anouther key
    Args:
        records (list): list of records where key 'emotions_url' exists

    Returns:
        [List[records]]: list records
    """
    for i in range(len(records)):
        records[i]["url"] = records[i]["emotions_url"]
    return records


def cut_videos(records, start_time, end_time, folder_name) -> None:
    """Cutting videos in system acording to user's datetimes. Return list[Records] with new file_names"""

    request_start = datetime.strptime(start_time, "%H:%M")
    request_end = datetime.strptime(end_time, "%H:%M")
    if len(records) == 1:
        record_start = datetime.strptime(records[0].get("start_time"), "%H:%M:%S")

        records[0]["file_name"] = cut(
            file_name=records[0]["file_name"],
            time_start=str(request_start - record_start),
            durr=str(request_end - request_start),
            folder_name=folder_name,
        )
    else:
        record_start = datetime.strptime(records[0].get("start_time"), "%H:%M:%S")
        record_end = datetime.strptime(records[0].get("end_time"), "%H:%M:%S")

        records[0]["file_name"] = cut(
            file_name=records[0]["file_name"],
            time_start=str(request_start - record_start),
            durr=str(record_end - request_start),
            folder_name=folder_name,
        )

        records[-1]["file_name"] = cut(
            file_name=records[-1]["file_name"],
            time_start=str(
                datetime.strptime("00:00:00", "%H:%M:%S")
                - datetime.strptime("00:00:00", "%H:%M:%S")
            ),
            durr=str(request_end - record_start),
            folder_name=folder_name,
        )
    return records


def concat_videos(role_records: dict, folder_name: str) -> dict:
    """Concatenates videos presented in dict and returns dict with new file_names.
    One file_name for one role

    Args:
        role_records (dict): dict with keys: roles; values: list records
        folder_name (str): folder in which videos are located

    Returns:
        dict: Dict with new file_names. One file_name for one role
    """
    concatenated_videos = {}
    for role, records in role_records.items():
        concatenated_videos[role] = concat(
            folder_name,
            *[el.get("file_name") for el in records],
        )
    return concatenated_videos


class Merger:
    """
    Base logic of Merger work. We are proceeding one video among different hstack | vstack
    commands to get appropriate video and then upload it
    """

    def __init__(self, merge_type: str, details_from_request: dict):
        """
        Args:
            merge_type (str): Type of merge e.g. 'main_emotions'
            details_from_request (dict): Message from Rabbit
        """
        self.merge_type = merge_type
        self.details_from_request = details_from_request
        self.folder_name = str(uuid4())  # uses for store local files for processing
        self.Nvr_db = Nvr_db()

        mkdir(str(Path.home()) + "/merger/", self.folder_name)

    async def download_necessary_videos(self) -> list:
        request_equipment = get_roles_for_merge_type(self.merge_type)
        equipment = await self.Nvr_db.get_equipment_from_room(
            self.details_from_request["room_name"], request_equipment
        )

        # dictionary with keys: roles; values: List[records]
        role_records = {}
        for role, ip in equipment.items():
            role_records[role] = await self.Nvr_db.get_records_for_ip(
                ip,
                self.details_from_request["room_name"],
                self.details_from_request["date"],
                self.details_from_request["start_time"],
                self.details_from_request["end_time"],
            )
        if role_records.get("emotions") is not None:
            role_records["emotions"] = patch_emotion_records(role_records["emotions"])

        # download exact videos and append to each record in dictionary
        # new value: file_name in system
        for role in role_records.keys():
            for i in range(len(role_records[role])):
                role_records[role][i]["file_name"] = download_video(
                    get_id_form_url(role_records[role][i]["url"]), self.folder_name
                )
        return role_records

    def perform_merge(self, role_records: list):
        for role, records in role_records.items():
            role_records[role] = cut_videos(
                records,
                self.details_from_request["start_time"],
                self.details_from_request["end_time"],
                self.folder_name,
            )
        concatenated_videos = concat_videos(
            role_records,
            self.folder_name,
        )

        if self.merge_type == "main_emotions":
            self._main_emotions_merge(concatenated_videos)
        if self.merge_type == "ptz_preza_emotions":
            self._ptz_presa_emo_merge(concatenated_videos)
        if self.merge_type == "emotions":
            self._emotions(concatenated_videos)
        # publish
        pass
        rmdir(self.folder_name)
        pass

    def _main_emotions_merge(self, concatenated_videos: dict):
        # result will be saved in processing_file
        processing_file = concatenated_videos["main"]
        processing_file = ffmpeg_hstack(
            self.folder_name, processing_file, concatenated_videos["emotions"]
        )
        print("AAAAA FINALLY EBAT")
        return processing_file

    def _ptz_presa_emo_merge(self, concatenated_videos: dict):
        # result will be saved in processing_file
        processing_file = concatenated_videos["presentation"]
        processing_file = ffmpeg_hstack(
            self.folder_name, processing_file, concatenated_videos["emotions"]
        )
        processing_file = ffmpeg_hstack(
            self.folder_name, processing_file, concatenated_videos["ptz"]
        )
        print("AAAAA FINALLY EBAT")
        return processing_file

    def _emotions(self, concatenated_videos: dict):
        processing_file = concatenated_videos["emotions"]
        pass


async def asd():
    mg = Merger("main_emotions", input_message)
    a = await mg.download_necessary_videos()
    b = await mg.perform_merge(a)


asyncio.run(asd())
