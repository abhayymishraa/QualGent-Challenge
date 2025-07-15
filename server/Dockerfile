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
    
ENV HOST=0.0.0.0 \
    PORT=8000 \
    WORKERS=4
    
EXPOSE ${PORT}
    
CMD ["bash","-c", "\
      uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000} & \
      python worker.py worker & \
      python worker.py requeuer \
    "]
