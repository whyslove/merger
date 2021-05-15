from logging import log
from aiohttp import ClientSession
import aiohttp
from loguru import logger
import requests
from datetime import datetime

from settings import settings  # мб надо вернуть две точки


class Erudite:
    def __init__(self) -> None:
        self.NVR_API_URL = "https://nvr.miem.hse.ru/api/erudite"
        self.NVR_API_KEY = settings.nvr_api_key
        # self.NVR_API_KEY = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOnsiZW1haWwiOiJzdnZveWxvdkBtaWVtLmhzZS5ydSIsInJvbGUiOiJhZG1pbiIsIm9yZ19uYW1lIjoiXHUwNDFjXHUwNDE4XHUwNDJkXHUwNDFjIn0sImlhdCI6MTYxNTkxNTAxMywiZXhwIjoxNjIzMTcyNjEzfQ.sR6_akiOiPq0mMFl84igjY1piLquE43xcDiVSMy743E"

    async def send_record(
        self,
        room_name: str,
        date: str,
        start_time: str,
        end_time: str,
        record_url: str,
    ) -> None:
        """ Выгружает в Эрудит запись о сделанной склейке """

        async with ClientSession() as session:
            async with session.post(
                f"{self.NVR_API_URL}/records",
                json={
                    "room_name": room_name,
                    "date": date,
                    "start_time": start_time,
                    "end_time": end_time,
                    "url": record_url,
                    "type": "Offline",
                },
                headers={"key": self.NVR_API_KEY},
                ssl=False,
            ) as resp:
                logger.info(f"Erudite response: {await resp.json()}")

    def get_records(self, params: dict) -> list or None:
        """ Получает нужные записи для склейки из Эрудита """

        new_params = self.parse_params(params)
        if not new_params:
            return None

        records = self.request_records(new_params)

        return records

    def parse_params(self, old_params: dict) -> dict:
        """ Делает новый словарь из параметров, подходящих для запроса в Эрудит """

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
        """ Делает запрос в Эрудит по заданным параметрам, запрашивая записи """

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

    async def get_all_relevant_equipment_from_room(
        self, session: aiohttp.ClientSession, room_name: str
    ) -> dict:
        processing_equipment = {}
        async with session.get(
            f"{self.NVR_API_URL}/equipment", params={"room_name": room_name}
        ) as equipment:
            equipment = await equipment.json()
            # if equipment.get("message") == "Equipment are not found":
            #     logger.error(f"There is no equipment in a room with name {room_name}")
            #     raise Exception("Error while getting equipment")

            for eq in equipment:
                if eq.get("role") == "Tracking":
                    processing_equipment["main"] = eq.get("ip")
                if eq.get("role") == "emotions":
                    processing_equipment["emotions"] = eq.get("ip")
                if eq.get("role") == "presentation":
                    processing_equipment["preza"] = eq.get("ip")
                if eq.get("role") == "default":
                    processing_equipment["default"] = eq.get("ip")

            if processing_equipment.get("main") is None:
                # No ptz use default
                processing_equipment["main"] = processing_equipment["default"]

        logger.debug(f"processing_equipment: {processing_equipment}")
        return processing_equipment

    async def get_records_for_ip(
        self,
        session: aiohttp.ClientSession,
        camera_ip: str,
        room_name: str,
        date: str,
        start_time: str,
        end_time: str,
    ) -> list:
        # Get records for the all date
        start = date + " " + "01:00"
        end = date + " " + "23:59"
        params = {
            "room_name": room_name,
            "fromdate": start,
            "todate": end,
            "camera_ip": camera_ip,
        }
        res = True
        while res != []:
            async with session.get(
                f"{self.NVR_API_URL}/records",
                params=params,
            ) as records:
                records = await records.json()
                # records = [record.pop("keywords") for record in await records.json()]
                records = choose_relevant_records(records, start_time, end_time)
                logger.debug(records)
            return records


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
