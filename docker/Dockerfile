FROM --platform=$TARGETOS/$TARGETARCH python:3.13-slim-bookworm

RUN apt update \
    && apt -y install git gcc g++ ca-certificates dnsutils curl iproute2 ffmpeg procps tini \
    && useradd -m -d /home/container container

# Install Poetry as root (poetry goes to /root/.local/bin)
RUN curl -sSL https://install.python-poetry.org | python3 - \
    && mv /root/.local/share/pypoetry/venv/bin/poetry /usr/bin/poetry \
    && chmod 755 /usr/bin/poetry \
    && rm -rf /root/.local

# Now switch to the container user
USER container
ENV USER=container HOME=/home/container
WORKDIR /home/container

STOPSIGNAL SIGINT

COPY --chown=container:container ./entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
ENTRYPOINT ["/usr/bin/tini", "-g", "--"]
CMD ["/entrypoint.sh"]
