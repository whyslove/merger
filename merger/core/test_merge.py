import subprocess
from db.ffmpeg_commands import generate_ffmpeg
import asyncio
import aiohttp

token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOnsiZW1haWwiOiJzdnZveWxvdkBtaWVtLmhzZS5ydSIsInJvbGUiOiJhZG1pbiIsIm9yZ19uYW1lIjoiXHUwNDFjXHUwNDE4XHUwNDJkXHUwNDFjIn0sImlhdCI6MTYxNTkxNTAxMywiZXhwIjoxNjIzMTcyNjEzfQ.sR6_akiOiPq0mMFl84igjY1piLquE43xcDiVSMy743E"
input_message = ["305", "2021-05-01 11:00:00", "2021-05-01 12:30:00"]
ERUDITE_URL = "https://nvr.miem.hse.ru/api/erudite"
# process = subprocess.Popen(
#     generate_ffmpeg("presentation", "1920:1080", "main.mp4", "emotions.mp4", "ptz.mp4"),
#     stdout=subprocess.PIPE,
#     shell=True,
#     executable="/bin/bash",
# )
# output, error = process.communicate()

# print(output, error)\


async def get_all_needed_equipment(session) -> dict:
    processing_equipment = {}

    async with session.get(
        f"{ERUDITE_URL}/equipment", params={"room_name": input_message[0]}
    ) as equipment:
        equipment = await equipment.json()
        try:
            for eq in equipment:
                if eq.get("role") == "Tracking":
                    processing_equipment["main"] = eq.get("ip")
                if eq.get("role") == "emotions":
                    processing_equipment["emotions"] = eq.get("ip")
                if eq.get("role") == "presentation":
                    processing_equipment["preza"] = eq.get("ip")

            if processing_equipment.get("ptz") == None:
                # no tracking -> use first cam in the auditory which is not emotions
                processing_equipment["main"] = (
                    equipment[0].get("ip")
                    if equipment[0].get("role") != "emotions"
                    else equipment[1].get("ip")
                )
        except Exception as exp:
            print(exp)
    return processing_equipment


async def main():
    async with aiohttp.ClientSession() as session:
        equipment = await get_all_needed_equipment(session)

        async with session.get(
            f"{ERUDITE_URL}/records",
            params={
                "room_name": input_message[0],
                "fromdate": input_message[1],
                "todate": input_message[2],
                "camera_ip": equipment["main"],
            },
        ) as records_main:
            for record in await records_main.json():

                record.pop("id")
                record.pop("keywords")
                print(record)


asyncio.run(main())

# import requests

# params = {"room_name": "304"}
# records = requests.get(
#     "https://nvr.miem.hse.ru/api/erudite/records",
#     headers={"token": token},
#     params=params,
# )
# print(records.status_code)
# for record in records.json():
#     record.pop("id")
#     record.pop("keywords")
#     print(record)


def check_ptz(equipment, merging_sheet):
    for eq in equipment:
        if eq.get("role") == "Tracking":
            merging_sheet["ptz"] = eq.ip
            return merging_sheet


def check_emotions(records, merging_sheet):
    for rec in records:
        pass
