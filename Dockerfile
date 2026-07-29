FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p logs cache

ENV DISABLE_SEMANTIC_CACHE=true
ENV PORT=8001

EXPOSE 8001

CMD uvicorn api.server:app --host 0.0.0.0 --port ${PORT:-8001} --timeout-keep-alive 300