FROM python:3.11-alpine

RUN apk add --no-cache nodejs npm

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/
COPY config.yaml .

RUN mkdir -p /data/dockertarupdater /tmp/dockertarupdater/downloads

EXPOSE 5000

ENV PYTHONUNBUFFERED=1
ENV CONFIG_PATH=/app/config.yaml

CMD ["python", "-m", "app.main"]
