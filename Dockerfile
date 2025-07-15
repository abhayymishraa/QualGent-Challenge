FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
    
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc build-essential && \
    rm -rf /var/lib/apt/lists/*
    
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
    
COPY . /app
    
CMD ["python","worker.py","worker"]
