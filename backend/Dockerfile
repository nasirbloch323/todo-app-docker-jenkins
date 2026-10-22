FROM python:3.12-slim

ARG APP_VERSION=dev
ENV APP_VERSION=${APP_VERSION} \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY app.py wsgi.py init_db.py ./
RUN useradd --system --no-create-home appuser
USER appuser

EXPOSE 5000
CMD ["sh", "-c", "python init_db.py && exec gunicorn -b 0.0.0.0:5000 -w 2 --threads 4 --access-logfile - wsgi:app"]
