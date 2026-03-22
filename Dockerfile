FROM python:3.12-slim

WORKDIR /app

COPY . .

RUN pip install --no-cache-dir .

VOLUME ["/downloads"]

ENTRYPOINT ["bandcamptui"]
CMD ["-c", "/cookies.txt", "-d", "/downloads"]
