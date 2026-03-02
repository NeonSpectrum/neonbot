FROM ghcr.io/parkervcp/yolks:python_3.12

RUN curl -sSL https://install.python-poetry.org | python3 -

RUN mv /root/.local/bin/poetry /usr/local/bin/poetry \
    && rm -rf /root/.local