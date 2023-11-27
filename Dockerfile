FROM python:3.9-slim

# Keeps Python from generating .pyc files in the container
ENV PYTHONDONTWRITEBYTECODE=1

# Turns off buffering for easier container logging
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get -y update \
    && apt-get install -y --no-install-recommends ffmpeg

RUN python -m pip install --upgrade pip
RUN pip install pipenv && pipenv install --dev --system --deploy

CMD ["python", "main.py"]