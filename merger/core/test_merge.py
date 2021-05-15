import asyncio
from pathlib import Path
import aiohttp

from uuid import uuid4
from loguru import logger

from db.ff_commands import make_single_merge, get_width_height, mkdir
from apis.erudite_api import Erudite as Nvr_db
from apis.driveAPI import download_video

token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOnsiZW1haWwiOiJzdnZveWxvdkBtaWVtLmhzZS5ydSIsInJvbGUiOiJhZG1pbiIsIm9yZ19uYW1lIjoiXHUwNDFjXHUwNDE4XHUwNDJkXHUwNDFjIn0sImlhdCI6MTYxNTkxNTAxMywiZXhwIjoxNjIzMTcyNjEzfQ.sR6_akiOiPq0mMFl84igjY1piLquE43xcDiVSMy743E"
input_message = {
    "room_name": "307",
    "date": "2021-05-11",
    "start_time": "11:10",
    "end_time": "11:15",
    "id": "609709bbd05edc45876e4eaf",
}
ERUDITE_URL = "https://nvr.miem.hse.ru/api/erudite"


def get_max_width(*file_names):

    """Returns max width of all inputs"""
    max_width = -1
    for file_name in file_names:
        curr_width = int(get_width_height(file_name)[0])
        if curr_width > max_width:
            max_width = curr_width
    return max_width


def check_ptz(equipment, merging_sheet):
    for eq in equipment:
        if eq.get("role") == "Tracking":
            merging_sheet["ptz"] = eq.ip
            return merging_sheet


def check_emotions(records, merging_sheet):
    for rec in records:
        pass


class Merger:
    def __init__(self, merge_type: str, details_from_request: dict):
        self.merge_type = merge_type
        self.details_from_request = details_from_request
        self.folder_name = str(uuid4())  # uses for store local files for processing
        self.session = aiohttp.ClientSession()
        self.Nvr_db = Nvr_db()

        mkdir(str(Path.home()) + "/merger/", self.folder_name)

    def upload_merge():
        # This more convenient way to use upload_necessary_videos and
        # perform_merge functions
        pass

    async def upload_necessary_videos(self):
        equipment = await self.Nvr_db.get_all_relevant_equipment_from_room(
            self.session, self.details_from_request["room_name"]
        )

        # dictionary with keys: roles, values: List[records]
        role_list_records = {}
        for role, ip in equipment.items():
            role_list_records[role] = await self.Nvr_db.get_records_for_ip(
                self.session,
                ip,
                self.details_from_request["room_name"],
                self.details_from_request["date"],
                self.details_from_request["start_time"],
                self.details_from_request["end_time"],
            )

        # dictionary with keys: roles; keys: List[records_file_names_in_directory]
        role_list_names = {}
        for role, records in role_list_records.items():
            role_list_names[role] = []
            for record in records:
                role_list_names[role].append(
                    download_video(get_id_form_url(record["url"]), self.folder_name)
                )

        pass

    def perform_merge():
        pass

    def _ptz_presa_emo_merge(self):
        # Get max width to know where the first rigth edge of the merge. i.e correctly
        # handle 16:9 and 4:3 presentaions alongside with ptz

        file1 = "input1.mp4"
        file2 = "input2.mp4"
        file3 = "input3.mp4"
        output_file_name = uuid4()

        max_width = get_max_width(file1, file2)
        logger.debug(f"Max width of 2 files {file1} {file2} is {max_width}")

        records = [[], [], []]

        make_single_merge(
            "ptz_presentation_emo",
            output_file_name,
            max_width,
            presentation=file1,
            ptz=file3,
            emotions=file2,
        )


async def asd():
    mg = Merger("merge_type", input_message)
    await mg.upload_necessary_videos()


def get_id_form_url(url: str) -> str:
    """Parse a certain type gdrive url to obtain an id from it"""
    return url.split("/file/d/")[1].split("/preview")[0]


asyncio.run(asd())