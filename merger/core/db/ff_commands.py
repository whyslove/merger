import subprocess
import uuid

from pathlib import Path

from loguru import logger

MERGER_PATH = str(Path.home()) + "/merger/"

ffmpeg_commands = {
    "concatenate": """
    cd {merger_path}/{folder_name}
    ffmpeg -f concat -safe 0 -i {file_wth_file_names} -c copy {output_file_name}
    """,
    "cut": """
    cd {merger_path}/{folder_name}
    ffmpeg -ss {time_start} -t {durr} -i {file_name} -c copy  {new_file_name} -nostdin -y
    """,
    "vstack": """
    cd {merger_path}/{folder_name}
    ffmpeg -i {upper_input} -i {lower_input} -filter_complex vstack=inputs=2 -c copy {output} -nostdin -y
    """,
    "hstack": """
    cd {merger_path}/{folder_name}
    ffmpeg -i {left_input} -i {left_input} -filter_complex hstack=inputs=2 {output} -nostdin -y
    """,
}


def execute_command(command: str) -> str:
    """Executes command in bash shell"""
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        shell=True,
        executable="/bin/bash",
    )

    output, error = process.communicate()
    logger.debug(output)
    if error is not None:
        logger.error(f"Error in executing {command} error: {error}")
        raise Exception(error)
    return True


def generate_ffmpeg_command(command_name: str, **data_for_commands: str) -> str:
    """
    Changes dummy names in ffmpeg command on really names
    :param merge_type: can be 'presentation' (presentation alongside ptz and mediacontent)
    :param resolution: resolution of main video in '16:9' format
    :param inputs: iterable string objects with names of files, number of such objects must match merge type
    """
    command = ffmpeg_commands[command_name].format(
        **data_for_commands, merger_path=MERGER_PATH
    )
    return command


def cut(file_name: str, time_start: str, durr: str, folder_name: str) -> str:
    """return file name"""
    new_file_name = str(uuid.uuid4()) + ".mp4"
    logger.debug(f"Cutting file {file_name} into {new_file_name}")
    command = generate_ffmpeg_command(
        "cut",
        file_name=file_name,
        new_file_name=new_file_name,
        time_start=time_start,
        durr=durr,
        folder_name=folder_name,
    )
    execute_command(command)
    return new_file_name


def concat(folder_name, *inputs):
    try:
        file_wth_file_names = str(uuid.uuid4()) + ".txt"
        f = open(f"{MERGER_PATH}/{folder_name}/{file_wth_file_names}", mode="w")
        file_names = [f"file '{input}'\n" for input in inputs]
        for name in file_names:
            f.writelines(name)
        logger.debug(f"starting concatenating {inputs}")
    except Exception as exp:
        logger.error(
            f"error in concatenation error: {exp}",
        )
        raise Exception(exp)
    finally:
        f.close()

    output_file_name = str(uuid.uuid4()) + ".mp4"
    command = generate_ffmpeg_command(
        "concatenate",
        output_file_name=output_file_name,
        file_wth_file_names=file_wth_file_names,
        folder_name=folder_name,
    )
    execute_command(command)
    return output_file_name


def mkdir(dir_path, dir_name) -> None:
    logger.debug(f"Creating directory with name {dir_name}")
    execute_command(f"mkdir {dir_path}/{dir_name}")


def rmdir(dir_name) -> None:
    logger.debug(f"Removing directory with name {dir_name}")
    execute_command(f"rm -rf {MERGER_PATH}/{dir_name}")


def ffmpeg_hstack(folder_name: str, left_file: str, right_file: str) -> None:
    output_file_name = str(uuid.uuid4()) + ".mp4"

    logger.debug(
        f"Horizontally stackingvideos. Left: {left_file}, right: left: {right_file} in {output_file_name}"
    )
    command = generate_ffmpeg_command(
        "hstack",
        left_input=left_file,
        right_input=right_file,
        output=output_file_name,
        folder_name=folder_name,
    )
    execute_command(command)

    return output_file_name


def ffmpeg_vstack(
    folder_name: str,
    upper_file: str,
    lower_file: str,
) -> str:
    output_file_name = str(uuid.uuid4()) + ".mp4"

    logger.debug(
        f"Vertically stackingvideos. Upper: {upper_file}, Lower: left: {lower_file} in {output_file_name}"
    )
    command = generate_ffmpeg_command(
        "hstack",
        upper_input=upper_file,
        lower_input=lower_file,
        output=output_file_name,
        folder_name=folder_name,
    )
    execute_command(command)
    return output_file_name


def get_roles_for_merge_type(merge_type: str):
    if merge_type == "main_emotions":
        return ["main", "emotions"]
    if merge_type == "presentation_ptz_emotions":
        return ["presentation", "Tracking", "emotions"]
    if merge_type == "emotions":
        return ["emotions"]


# def make_single_merge(
#     merging_type: str,
#     folder_name: str,
#     output_file_name: str,
#     start_time: str,
#     end_time: str,
#     right_width: str = None,
#     **inputs,
# ):
#     """Perfoms stadalone merge according to given paramentrs

#     Args:
#         merging_type (str): type of merge, e.g. "ptz_presentation_emo"
#         output_file_name (str): name of file in which merge will be saved
#         right_width (str, optional): If merge is with emo, essential to know where the
#             right of [presentation/emotions]. Defaults to None.


#     Returns:
#         [type]: [description]
#     """
#     command = generate_ffmpeg_command(
#         merging_type,
#         right_width=right_width,
#         output_file_name=output_file_name,
#         folder_name=folder_name,
#         **inputs,
#     )
#     output = execute_command(command)
#     logger.debug(output)
#     return True

# def get_width_height(file_name: str) -> list:
#     """

#     Args:
#         file_name (str): file_name

#     Returns:
#         list: list with len() = 2, list[0] is width, list[1] is height
#     """
#     command = generate_ffmpeg_command("get_width_height", input1=file_name)
#     width_height = execute_command(command).decode("utf-8").split("x")
#     return width_height

# "ptz_presentation_emo": """
#     cd {merger_path}/{folder_name}
#     ffmpeg -i {presentation} -i {ptz}  -i {emotions} \
#         -filter_complex \
#         "[1:v]crop=iw/3:ih:iw/3:0[ptz];
#         [0:v][ptz][2:v]xstack=inputs=3:layout=0_0|{right_width}_0|0_h0[v]" \
#         -map "[v]" \
#         {output_file_name}.mp4
#     """,
#     "get_width_height": """
#     cd {merger_path}/{folder_name}
#     ffprobe -v error -select_streams v:0 \
#         -show_entries stream=width,height -of csv=s=x:p=0 {input1}
#     """,
