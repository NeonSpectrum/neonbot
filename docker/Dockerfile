FROM --platform=$TARGETOS/$TARGETARCH python:3.13-slim-bookworm

RUN apt update \
    && apt -y install git gcc g++ ca-certificates dnsutils curl iproute2 ffmpeg procps tini python3-poetry \
    && useradd -m -d /home/container container

# Now switch to the container user
USER container
ENV USER=container HOME=/home/container
ENV PATH="/home/container/.local/bin:${PATH}"
WORKDIR /home/container

STOPSIGNAL SIGINT

COPY --chown=container:container ./entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
ENTRYPOINT ["/usr/bin/tini", "-g", "--"]
CMD ["/entrypoint.sh"]
