FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies minimal
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    wget \
    ca-certificates && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers (handles Chrome internally)
RUN playwright install chromium && \
    playwright install-deps chromium

COPY app.py .
COPY coinmarketcap.py .
COPY __init__.py .

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8001"]