FROM python:3.11-alpine

RUN apk add --no-cache nodejs npm tzdata

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY web/ ./web/
RUN cd web && npm install && npm run build

COPY app/ ./app/
COPY config.yaml .

COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

RUN mkdir -p /config /tmp/dockertarupdater/downloads

EXPOSE 3006

ENV PYTHONUNBUFFERED=1
ENV CONFIG_PATH=/app/config.yaml
ENV FRONTEND_DIST=/app/web/dist
ENV TZ=Asia/Shanghai
ENV LICENSE_SALT=1234567890987654321

ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["python", "-m", "app.main"]
