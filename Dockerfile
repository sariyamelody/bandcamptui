FROM python:3.12-slim

WORKDIR /app

COPY . .

RUN apt-get update && apt-get install -y --no-install-recommends git ncurses-term \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir . \
    && apt-get purge -y --auto-remove git

ENV TERM=xterm-256color

VOLUME ["/downloads"]

ENTRYPOINT ["bandcamptui"]
CMD ["-c", "/cookies.txt", "-d", "/downloads"]
