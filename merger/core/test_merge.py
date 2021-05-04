import subprocess
from db.ffmpeg_commands import generate_ffmpeg

process = subprocess.Popen(
    generate_ffmpeg("presentation", "1920:1080", "main.mp4", "emotions.mp4", "ptz.mp4"),
    stdout=subprocess.PIPE,
    shell=True,
    executable="/bin/bash",
)
output, error = process.communicate()

print(output, error)