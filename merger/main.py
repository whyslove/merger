import asyncio
import ast
from loguru import logger

from core.apis.erudite_api import Erudite


erudite = Erudite()
# records = asyncio.run(erudite.a_get_record("504", "2021-06-01",  "10:30:00", "12:00:00"))
# for record in records:
#     record.pop("keywords")
# print(records)


def merge(body: str) -> str:
    """ Последовательность закачивания, склейки и выгрузки видоса """

    parsed_message = parce_message(body)
    if not parsed_message:
        logger.error("parce exception")
        return "parce exception"

    records = erudite.get_records(parsed_message)
    print(records)
    if not records:
        logger.error("records request exception")
        return "records request exception"
    elif records == []:
        logger.error("no records found")
        return "no records found"

    return "done"


def parce_message(body: str) -> dict:
    """ Парсинг переданной в сообщении строки в словарь"""

    try:
        parsed_message = ast.literal_eval(body)
    except Exception:
        parsed_message = None

    return parsed_message


res = merge("{'date':'2021-05-01', 'start_time':'10:30:00', 'end_time':'12:30:00', 'room_name':'305'}")
print(res)
