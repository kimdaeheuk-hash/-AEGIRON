FROM python:3.11-slim

WORKDIR /app

COPY epiweather-api/requirements.txt epiweather-api/requirements.txt
RUN pip install --no-cache-dir -r epiweather-api/requirements.txt

COPY epiweather-api epiweather-api

CMD uvicorn main:app --app-dir epiweather-api --host 0.0.0.0 --port $PORT
