FROM python:3.11-slim

WORKDIR /app

COPY requirements-prod.txt .
RUN pip install --no-cache-dir -r requirements-prod.txt

COPY . .

RUN mkdir -p logs cache

ENV DISABLE_SEMANTIC_CACHE=true

EXPOSE 8080

CMD uvicorn api.server:app --host 0.0.0.0 --port $PORT