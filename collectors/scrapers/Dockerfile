FROM mcr.microsoft.com/playwright/python:v1.50.0-jammy

ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .
COPY coinmarketcap.py .
COPY __init__.py .

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8001"]