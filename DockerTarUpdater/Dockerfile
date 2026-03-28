FROM python:3.11-alpine

RUN apk add --no-cache nodejs npm tzdata

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY web/ ./web/
RUN cd web && npm install && npm run build

COPY app/ ./app/
COPY config.yaml .

RUN mkdir -p /config /tmp/dockertarupdater/downloads

EXPOSE 3006

ENV PYTHONUNBUFFERED=1
ENV CONFIG_PATH=/app/config.yaml
ENV FRONTEND_DIST=/app/web/dist
ENV TZ=Asia/Shanghai

CMD ["python", "-m", "app.main"]
