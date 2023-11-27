FROM python:3.9-slim

# Keeps Python from generating .pyc files in the container
ENV PYTHONDONTWRITEBYTECODE=1

# Turns off buffering for easier container logging
ENV PYTHONUNBUFFERED=1

RUN apt-get -y update \
    && apt-get install -y --no-install-recommends ffmpeg

RUN python -m pip install --upgrade pip && pip install pipenv

WORKDIR /app

RUN PIPENV_VENV_IN_PROJECT=1 pipenv install

CMD ["pipenv", "run", "python", "main.py"]