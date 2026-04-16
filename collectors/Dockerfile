FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY __init__.py .
COPY price_collector.py .
COPY news_collector.py .
COPY scrapers/ ./scrapers/

CMD ["python", "price_collector.py"]