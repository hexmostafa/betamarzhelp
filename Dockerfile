FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
VOLUME ["/app/data", "/app/logs"]
ENV DATABASE_PATH=/app/data/bot_database.db
ENV PYTHONUNBUFFERED=1
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python3 src/health_check.py || exit 1
CMD ["python3", "src/bot.py"]
