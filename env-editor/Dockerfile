FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY . /app

ENV PORT=8000
ENV ENV_ROOT=/config
ENV ENV_FILENAME=app.env

EXPOSE 8000

CMD ["python", "app.py"]
