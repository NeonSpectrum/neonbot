FROM python:3.9-slim

# Keeps Python from generating .pyc files in the container
ENV PYTHONDONTWRITEBYTECODE=1

# Turns off buffering for easier container logging
ENV PYTHONUNBUFFERED=1

RUN apt-get -y update \
    && apt-get install -y --no-install-recommends ffmpeg git

WORKDIR /app

COPY docker/entrypoint.sh .
COPY requirements.txt .

RUN chmod +x entrypoint.sh

ENTRYPOINT ["./entrypoint.sh"]