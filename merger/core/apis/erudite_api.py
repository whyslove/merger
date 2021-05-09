from aiohttp import ClientSession
from loguru import logger
import requests

from ..settings import settings


class Erudite:
    def __init__(self) -> None:
        self.NVR_API_URL = "https://nvr.miem.hse.ru/api/erudite"
        self.NVR_API_KEY = settings.nvr_api_key

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

        if res.status_code == 200:
            return res.json()
        else:
            return []
