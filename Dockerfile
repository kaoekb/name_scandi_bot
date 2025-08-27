FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
 && apt-get update \
 && apt-get install -y --no-install-recommends tzdata \
 && rm -rf /var/lib/apt/lists/*

COPY . .

# каталоги для записи + права под uid:gid 1000:1000 (как в compose)
RUN mkdir -p /app/logs /app/data \
 && chown -R 1000:1000 /app

CMD ["python", "-B", "-u", "main.py"]
