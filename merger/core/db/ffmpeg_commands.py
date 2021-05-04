ffmpeg_commands = {
    "presentation;1920:1080": """cd ~/Desktop/merger_test 
        ffmpeg \
        -i _input1.mp4 \
        -i _input2.mp4 \
        -i _input3.mp4 \
        -filter_complex '[0:v]pad=iw*1.33:ih+400[int];
        [int][1:v]overlay=0:1080[vid1];
        [2:v]crop=640:1080:640:0[ptz];
        [vid1][ptz]overlay=1920:0[vid2]' \
        -map '[vid2]' \
        -c:v libx264 \
        -crf 23 \
        -preset veryfast \
        output.mp4"""
}


def generate_ffmpeg(merge_type, resolution, *input_names):
    i = 1
    output_command = ffmpeg_commands[f"{merge_type};{resolution}"]
    for name_input in input_names:
        output_command = output_command.replace(f"_input{i}.mp4", f"{name_input}")
        i += 1
    return output_command
