#!/bin/sh
# Public demo container start: migrate the isolated demo database, (re)seed the
# SYNTHETIC corpus and files, then serve the API. Never point this at research data.
set -eu
alembic upgrade head
python -m scripts.seed_demo
exec fastapi run app/main.py --host 0.0.0.0 --port "${PORT:-8000}"
