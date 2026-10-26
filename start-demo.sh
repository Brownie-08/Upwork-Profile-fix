#!/usr/bin/env bash
set -euo pipefail
python manage.py migrate --noinput
python seed_demo.py
exec gunicorn demo_wsgi:application --bind "0.0.0.0:${PORT:-8000}" --workers 1 --threads 2 --timeout 120 --access-logfile -
