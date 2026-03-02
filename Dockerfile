FROM ghcr.io/parkervcp/yolks:python_3.13

RUN curl -sSL https://install.python-poetry.org | python3 -

RUN mv ./.local/bin/poetry /usr/local/bin/poetry \
    && rm -rf ./.local