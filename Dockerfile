FROM ubuntu:latest
LABEL authors="Bigelow Systems, LLC. <engineering+cmit@bigelow.systems>"

RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-dev \
    build-essential \
    libssl-dev \
    libffi-dev \
    python3-setuptools \
    python3-venv \
    git \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && pip3 install supervisor requests

RUN mkdir -p /var/log/supervisor /var/log/cmit

COPY cmit /src/cmit
COPY ./demo/ /src/

CMD ["/bin/sh", "-c", "supervisord -c /src/supervisord.conf"]