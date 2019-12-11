FROM python:3

COPY . /nvr_merge

RUN pip install --no-cache-dir -r /nvr_merge/requirements.txt
