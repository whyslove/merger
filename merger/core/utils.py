import ast


def parce_message(body: str) -> dict:
    """Парсинг переданной в сообщении строки в словарь"""

    try:
        parsed_message = body.decode()  # get byte dict
        parsed_message = ast.literal_eval(parsed_message)  # get default dict
    except Exception:
        parsed_message = None

    return parsed_message
