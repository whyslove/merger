FROM python:3.8

ENV TZ=Europe/Moscow
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone
RUN apt -y update && apt -y install ffmpeg libpq-dev
COPY ./merger /merger
COPY ./creds /creds
COPY ./requirements.txt /

RUN pip install -r requirements.txt
RUN mkdir /root/merger
RUN mkdir /var/log/merger


CMD ["python", "/merger/main.py"]
