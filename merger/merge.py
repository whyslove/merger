import ast
from loguru import logger

from core.apis.erudite_api import Erudite


erudite = Erudite()


def merge(body: str) -> str:
    """Последовательность закачивания, склейки и выгрузки видоса"""

    import time

    time.sleep(4)

    parsed_message = parce_message(body)
    if not parsed_message:
        logger.error("parce exception")
        return "delete"

    records = erudite.get_records(parsed_message)
    if not records:
        logger.error("records request exception")
        return "delete"
    elif records == []:
        logger.error("no records found")
        return "resend"

    # TODO: тут должна быть ф-ия самой склейки

    logger.info("Message converted")

    return "done"


def parce_message(body: str) -> dict:
    """Парсинг переданной в сообщении строки в словарь"""

    try:
        parsed_message = ast.literal_eval(body)
    except Exception:
        parsed_message = None

    return parsed_message


# res = merge("{'date':'2021-05-01', 'start_time':'10:30:00', 'end_time':'12:30:00', 'room_name':'305'}")
# print(res)
