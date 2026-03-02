FROM --platform=$TARGETOS/$TARGETARCH python:3.13-slim-bookworm

RUN apt update \
            && apt -y install git gcc g++ ca-certificates dnsutils curl iproute2 ffmpeg procps tini \
            && useradd -m -d /home/container container

USER container
ENV USER=container HOME=/home/container
WORKDIR /home/container

RUN curl -sSL https://install.python-poetry.org | python3 - \
    && mv /home/container/.local/bin/poetry /usr/bin/poetry \
    && rm -rf /home/container/.local

STOPSIGNAL SIGINT

COPY --chown=container:container ./entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
ENTRYPOINT ["/usr/bin/tini", "-g", "--"]
CMD ["/entrypoint.sh"]