FROM ghcr.io/parkervcp/yolks:python_3.13

RUN curl -sSL https://install.python-poetry.org | python3 -

ENV PATH="/root/.local/bin:${PATH}"