from aiohttp import ClientSession
import aiohttp
from loguru import logger
import requests
from datetime import datetime

from ..settings import settings  # мб надо вернуть две точки


class Erudite:
    def __init__(self) -> None:
        self.NVR_API_URL = "https://nvr.miem.hse.ru/api/erudite"
        self.NVR_API_KEY = settings.nvr_api_key
        self.session = aiohttp.ClientSession()

    async def send_record(
        self,
        room_name: str,
        date: str,
        start_time: str,
        end_time: str,
        merge_type: str,
        video_purpose: str,
        record_url: str,
        email: str,
    ) -> None:
        """Выгружает в Эрудит запись о сделанной склейке"""
        start_point = date + " " + start_time + ":00"
        end_point = date + " " + end_time + ":00"
        async with ClientSession() as session:
            async with session.post(
                f"{self.NVR_API_URL}/records",
                json={
                    "room_name": room_name,
                    "date": date,
                    "start_point": start_point,
                    "end_point": end_point,
                    "url": record_url,
                    "type": merge_type,
                    "video_purpose": video_purpose,
                    "email": email,
                },
                headers={"key": self.NVR_API_KEY},
                ssl=False,
            ) as resp:
                logger.info(f"Erudite response: {await resp.json()}")

    def get_records(self, params: dict) -> list or None:
        """Получает нужные записи для склейки из Эрудита"""

        new_params = self.parse_params(params)
        if not new_params:
            return None

        records = self.request_records(new_params)

        return records

    def parse_params(self, old_params: dict) -> dict:
        """Делает новый словарь из параметров, подходящих для запроса в Эрудит"""

        try:
            new_params = {
                "room_name": old_params["room_name"],
                "fromdate": f"{old_params['date']} {old_params['start_time']}",
                "todate": f"{old_params['date']} {old_params['end_time']}",
            }
        except Exception:
            new_params = None

        return new_params

    def request_records(self, params: dict) -> dict:
        """Делает запрос в Эрудит по заданным параметрам, запрашивая записи"""

        res = requests.get(
            f"{self.NVR_API_URL}/records",
            params=params,
            headers={"key": self.NVR_API_KEY},
        )
        logger.info(res.json())
        self.NVR_API_URL
        if res.status_code == 200:
            return res.json()
        else:
            return []

    async def get_equipment_from_room(
        self, room_name: str, request_equipment: list
    ) -> dict:

        async with self.session.get(
            f"{self.NVR_API_URL}/equipment", params={"room_name": room_name}
        ) as equipment:
            equipment = [
                eq
                for eq in await equipment.json()
                if eq.get("role") in request_equipment
            ]
            if len(equipment) != len(request_equipment):
                # Here is processing whether merge is possible
                logger.error(
                    f"Not all equipment required for the merge type was found in room {room_name}"
                )
                raise Exception("Exception in getting equipment")

            equipment_ip = dict((eq["role"], eq["ip"]) for eq in equipment)

            return equipment_ip

    async def get_records_for_ip(
        self,
        camera_ip: str,
        room_name: str,
        date: str,
        start_time: str,
        end_time: str,
        emotions: bool = None,
    ) -> list:
        # Get records for the all date
        start = date + " " + "01:00"
        end = date + " " + "23:59"
        params = {
            "room_name": room_name,
            "date": date,
            "fromdate": start,
            "todate": end,
            "camera_ip": camera_ip,
        }
        res_records = []
        res = 1
        while res != []:
            async with self.session.get(
                f"{self.NVR_API_URL}/records",
                params=params,
            ) as records:
                records = await records.json()
                records = choose_relevant_records(records, start_time, end_time)
                if emotions is True:
                    records[""]
                    pass
                logger.debug(records)
                res_records.extend(records)
            res_records = datetime_sort_records(res_records)
            return res_records


def choose_relevant_records(records: list, start_time: str, end_time: str):
    """Gets all records from erudite for the DAY(!), and then returns records from the given period"""
    start_time = datetime.strptime(start_time, "%H:%M")
    end_time = datetime.strptime(end_time, "%H:%M")

    start_times = [
        item
        for item in records
        if datetime.strptime(item["end_time"], "%H:%M:%S") > start_time
    ]
    end_times = [
        item
        for item in records
        if datetime.strptime(item["start_time"], "%H:%M:%S") < end_time
    ]
    relevant_videos = []
    for el in start_times:
        if el in end_times:
            relevant_videos.append(el)
    return relevant_videos


def datetime_sort_records(records: list):
    """Sort records according to their start time"""
    for i in range(len(records)):
        records[i]["start_datetime"] = datetime.strptime(
            records[i]["date"] + " " + records[i]["start_time"], "%Y-%m-%d %H:%M:%S"
        )
    for i in range(len(records) - 1):
        for j in range(len(records) - i - 1):
            if records[j]["start_datetime"] > records[j + 1]["start_datetime"]:
                records[j], records[j + 1] = records[j + 1], records[j]
    return records
