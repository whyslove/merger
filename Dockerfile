FROM ubuntu:18.04

RUN apt-get -y update && apt-get -y install python3-pip python3-dev python3-venv ffmpeg
COPY . /merger
RUN pip3 install --no-cache-dir -r /merger/requirements.txt
RUN mkdir /root/vids

CMD ["python3", "/merger/app.py"]
