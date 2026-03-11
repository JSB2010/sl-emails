FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src

COPY sports-emails/requirements.txt sports-emails/requirements.txt
COPY instagram-poster/requirements.txt instagram-poster/requirements.txt

RUN python -m pip install --no-cache-dir --upgrade pip \
    && python -m pip install --no-cache-dir \
        -r sports-emails/requirements.txt \
        -r instagram-poster/requirements.txt \
        firebase-admin

COPY digital-signage digital-signage
COPY src src

ENV PORT=8080

EXPOSE 8080

CMD ["sh", "-c", "exec python -m flask --app sl_emails.web:create_app run --host=0.0.0.0 --port=${PORT:-8080}"]