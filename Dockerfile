FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=config.settings.production

WORKDIR /app

COPY requirements/ requirements/
RUN pip install --no-cache-dir -r requirements/production.txt

COPY . .

RUN useradd --system --uid 10001 --no-create-home app
USER app

EXPOSE 8000

# One worker + threads: the app is I/O bound and tiny, this fits a small VM,
# and DRF's throttle counters live in per-process memory, so a single process
# keeps the 5/min login limit exact (N workers would allow N x 5).
CMD ["gunicorn", "config.wsgi:application", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "1", "--threads", "4", \
     "--timeout", "30", \
     "--access-logfile", "-"]
