import asyncio


from datetime import datetime
from pathlib import Path


from uuid import uuid4
from loguru import logger

from .apis.erudite_api import Erudite as Nvr_db
from .apis.driveAPI import download_video, upload_to_remote_storage

from .db.ff_commands import (
    mkdir,
    rmdir,
    cut,
    concat,
    ffmpeg_hstack,
    ffmpeg_vstack,
)

input_message = {
    "room_name": "307",
    "date": "2021-05-13",
    "start_time": "15:10",
    "end_time": "15:11",
    "video_purpose": "complete_video",
    "merge_type": "main_Tracking",
    "publishing": "GDrive",
}
ERUDITE_URL = "https://nvr.miem.hse.ru/api/erudite"
MERGER_PATH = str(Path.home()) + "/merger"


def get_id_from_gdrive_url(url: str) -> str:
    return url.split("/file/d/")[1].split("/preview")[0]


def patch_emotion_records(records: list) -> list:
    """To perfom a unified interface for downloading videos needed to save video url in 'url' key.
    But emotions have url in anouther key
    Args:
        records (list): list of records where key 'emotions_url' exists

    Returns:
        list: list of records
    """
    for i in range(len(records)):
        records[i]["url"] = records[i]["emotions_url"]
    return records


def cut_videos(records, start_time, end_time, folder_name) -> None:
    """Cutting videos in system acording to user's datetimes. Return list of records with new file_names"""

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
        role_records (dict): dict with keys: roles; values: list of records
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
            merge_type (str): Type of merge must contain only names of equipment through undersocre
            e.g. "main_emotions"
            details_from_request (dict): Message from Rabbit
        """
        self.merge_type = merge_type
        self.details_from_request = details_from_request
        self.folder_name = str(uuid4())  # uses for store local files for processing
        self.Nvr_db = Nvr_db()

        logger.info(
            f"Initialized class merger with merge_type: {self.merge_type} and message: {details_from_request}"
        )
        mkdir(str(Path.home()) + "/merger/", self.folder_name)

    async def identify_videos_for_merging(self) -> list:
        request_equipment = self.merge_type.split(
            "_"
        )  # in merge type we store info about equip
        equipment = await self.Nvr_db.get_equipment_from_room(
            self.details_from_request["room_name"], request_equipment
        )

        # dictionary with keys: roles; values: list of records
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
            role_records["emotions"] = patch_emotion_records(
                role_records["emotions"]
            )  # perform unidied interface for downloading
        return role_records

    async def download_videos(self, role_records: dict) -> list:
        # download exact videos and append to each record in dictionary
        # new value: file_name in system
        for role in role_records.keys():
            for i in range(len(role_records[role])):
                role_records[role][i]["file_name"] = download_video(
                    get_id_from_gdrive_url(role_records[role][i]["url"]),
                    self.folder_name,
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
        if self.merge_type == "main_Tracking":
            output_file = self._main_tracking(concatenated_videos)
        if self.merge_type == "main_emotions":
            output_file = self._main_emotions_merge(concatenated_videos)
        if self.merge_type == "ptz_preza_emotions":
            self._ptz_presa_emo_merge(concatenated_videos)
        if self.merge_type == "emotions":
            self._emotions(concatenated_videos)
        return output_file

    async def upload(self, result_video_name: str) -> str:
        """Do all necessary uploadings after merge process. Upload to remote storage video and
        in Erduite Url of this video

        Args:
            result_video_name (str): result file name in system

        Returns:
            str: url in remote storage
        """
        # upload to Drive
        file_url = await upload_to_remote_storage(
            self.details_from_request["room_name"],
            self.details_from_request["date"],
            file_path=f"{MERGER_PATH}/{self.folder_name}/{result_video_name}",
        )

        # save info about file placement in database
        await self.Nvr_db.send_record(
            self.details_from_request["room_name"],
            self.details_from_request["date"],
            self.details_from_request["start_time"],
            self.details_from_request["end_time"],
            merge_type=self.details_from_request["merge_type"],
            video_purpose=self.details_from_request["video_purpose"],
            email=self.details_from_request["email"],
            record_url=file_url,
        )
        logger.info(f"Merging process was ended, deleting {self.folder_name}")
        rmdir(self.folder_name)
        return file_url

    def _main_emotions_merge(self, concatenated_videos: dict):
        # result will be saved in processing_file
        processing_file = concatenated_videos["main"]
        processing_file = ffmpeg_vstack(
            self.folder_name, processing_file, concatenated_videos["emotions"]
        )
        return processing_file

    def _main_tracking(self, concatenated_videos: dict):
        # result will be saved in processing_file
        processing_file = concatenated_videos["main"]
        processing_file = ffmpeg_hstack(
            self.folder_name, processing_file, concatenated_videos["Tracking"]
        )
        return processing_file

    def _emotions(self, concatenated_videos: dict):
        return concatenated_videos["emotions"]


async def merge(input_message: str) -> str:
    """Function that provide series of methods of merger class

    Args:
        input_message (str): should contain room_name, date, start_time, end_time, type complete_video,
        merge_type, publishing
    Returns:
        "delete" if bad input message, "resend" if not all videos were found, url with video if all good
    """
    # TODO если файлы не нашлись, то выкидывать Exception

    merger = Merger(input_message.get("merge_type"), input_message)
    role_records = await merger.identify_videos_for_merging()
    role_records = await merger.download_videos(role_records)
    result_file = merger.perform_merge(role_records)
    result_url = await merger.upload(result_file)
    await merger.Nvr_db.session.close()
    return result_url


if __name__ == "__main__":
    asyncio.run(merge(input_message))
