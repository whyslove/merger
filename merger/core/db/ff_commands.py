# [1:v]scale=1024:-1[vid1]
# add audio
import subprocess
from pathlib import Path
from loguru import logger

HOME_PATH = str(Path.home()) + "/merger/"

ffmpeg_commands = {
    "presentation;4:3": """
        cd {home_path}/{folder_name}
        ffmpeg \
        -i _input0.mp4 -i _input1.mp4  -i _input2.mp4\
        -filter_complex \
       "[0:v]pad=1920+640:768+200[int]; \
        [int][1:v]overlay=0:768[vid];
        [2:v]crop=640:1080:640:0[vid2];
        [vid][vid2]overlay=1920:0[vid3]" \
        -map "[vid3]" \
        -c:v libx264 -crf 23 output.mp4
        """,
    "presentation;16:9": """
        cd {home_path}/{folder_name}
        ffmpeg \
        -i _input0.mp4 -i _input1.mp4  -i _input2.mp4\
        -filter_complex \
        "[0:v]pad=iw+640:ih+400[int]; \
        [int][1:v]overlay=0:1080[vid];
        [2:v]crop=640:1080:640:0[vid2];
        [vid][vid2]overlay=1920:0[vid3]" \
        -map "[vid3]" \
        -c:v libx264 -crf 23 output.mp4
        """,
    "ptz_presentation_emo": """
    cd {home_path}/{folder_name}
    ffmpeg -i {presentation} -i {ptz}  -i {emotions} \
        -filter_complex \
        "[1:v]crop=iw/3:ih:iw/3:0[ptz];
        [0:v][ptz][2:v]xstack=inputs=3:layout=0_0|{right_width}_0|0_h0[v]" \
        -map "[v]" \
        {output_file_name}.mp4
    """,
    "get_width_height": """
    cd {home_path}/{folder_name}
    ffprobe -v error -select_streams v:0 \
        -show_entries stream=width,height -of csv=s=x:p=0 {input1}
    """,
    "concatenate": """
    cd {home_path}/{folder_name}
    ffmpeg -f concat -safe 0 -i file_names_for_concat.txt -c copy {output_file_name}.mp4
    """,
}


def generate_ffmpeg_command(command_name: str, **data_for_commands: str) -> str:
    """
    Changes dummy names in ffmpeg command on really names
    :param merge_type: can be 'presentation' (presentation alongside ptz and mediacontent)
    :param resolution: resolution of main video in '16:9' format
    :param inputs: iterable string objects with names of files, number of such objects must match merge type
    """
    # important that unused format argumets are ommiteed
    command = ffmpeg_commands[command_name].format(
        **data_for_commands, home_path=HOME_PATH
    )
    return command


def get_width_height(file_name: str) -> list:
    """

    Args:
        file_name (str): file_name

    Returns:
        list: list with len() = 2, list[0] is width, list[1] is height
    """
    command = generate_ffmpeg_command("get_width_height", input1=file_name)
    width_height = execute_command(command).decode("utf-8").split("x")
    return width_height


def concat_videos(output_file_name, *inputs):
    try:
        f = open("file_names_for_concat.txt", mode="w")
        f.writelines(inputs)

        logger.debug(f"starting concatenating {inputs}")

        command = generate_ffmpeg_command("concat", output_file_name=output_file_name)
        output = execute_command(command)
        return output
    except Exception as exp:
        logger.error(
            f"error in concatenation error: {exp}",
        )
        raise Exception(exp)
    finally:
        f.close()


def make_single_merge(
    merging_type: str,
    output_file_name: str,
    right_width: str = None,
    **inputs,
):
    """123213

    Args:
        merging_type (str): [description]
        right_width (str, optional): [description]. Defaults to None.

    Returns:
        [type]: [description]
    """
    command = generate_ffmpeg_command(
        merging_type,
        right_width=right_width,
        output_file_name=output_file_name,
        **inputs,
    )
    output = execute_command(command)
    logger.debug(output)
    return True


def mkdir(dir_path, dir_name) -> None:
    execute_command(f"mkdir {dir_path}/{dir_name}")


def execute_command(command: str) -> str:
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
    return output
