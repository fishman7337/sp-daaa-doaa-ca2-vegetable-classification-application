FROM python:3.14-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY backend /app/backend
COPY webapp/app /app/webapp/app
COPY db /app/db
COPY models /models

RUN mkdir -p /app/backend/uploads

EXPOSE 5000
CMD ["sh", "-c", "gunicorn backend.app:app --bind 0.0.0.0:${PORT:-5000} --workers ${GUNICORN_WORKERS:-2} --threads ${GUNICORN_THREADS:-4} --timeout ${GUNICORN_TIMEOUT:-120} --access-logfile - --error-logfile -"]
