FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV SITE_ROOT=/app
ENV PYTHONUNBUFFERED=1

EXPOSE 8080

# Coolify sets PORT. CMS_PASSWORD (or CMS_USERS) must be set in the environment.
CMD ["sh", "-c", "uvicorn cms.app:app --host 0.0.0.0 --port ${PORT:-8080}"]
