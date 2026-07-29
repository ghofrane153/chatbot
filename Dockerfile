FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p logs cache

ENV DISABLE_SEMANTIC_CACHE=true

EXPOSE 8001

CMD ["python", "start.py"]