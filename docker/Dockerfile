FROM --platform=$TARGETOS/$TARGETARCH python:3.13-slim-bookworm

RUN apt update \
    && apt -y install git gcc g++ ca-certificates dnsutils curl iproute2 ffmpeg libopus0 procps tini \
    && useradd -m -d /home/container container

# Install Poetry globally into /opt/poetry
ENV POETRY_HOME=/opt/poetry
RUN curl -sSL https://install.python-poetry.org | python3 - \
    && chmod +x /opt/poetry/bin/poetry

# Make global poetry available to everyone
ENV PATH="/opt/poetry/bin:${PATH}"

# Now switch to the container user
USER container
ENV USER=container HOME=/home/container
WORKDIR /home/container

# Install Poetry (poetry goes to /home/container/.local/bin)
RUN curl -sSL https://install.python-poetry.org | python3 -

STOPSIGNAL SIGINT

COPY --chown=container:container ./entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
ENTRYPOINT ["/usr/bin/tini", "-g", "--"]
CMD ["/entrypoint.sh"]
