# Public demo image: SYNTHETIC Demo Reservoir only (APP_ENV=demo).
# The code keeps the repository depth (apps/api) because settings resolve
# default paths relative to the repository root.
FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.9 /uv /uvx /bin/

WORKDIR /srv/mvdt/apps/api
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONUNBUFFERED=1

COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --no-install-project

COPY alembic.ini ./
COPY alembic ./alembic
COPY app ./app
COPY scripts ./scripts
RUN uv sync --locked --no-dev

ENV PATH="/srv/mvdt/apps/api/.venv/bin:$PATH" \
    APP_ENV=demo \
    STORAGE_ROOT=/srv/demo-data/storage \
    RAG_LITE_ENABLED=true \
    RAG_LITE_ALLOWLIST_PATH=/srv/demo-data/storage/rag-lite/allowlist.json \
    RAG_LITE_INDEX_DIR=/srv/demo-data/storage/rag-lite \
    RAG_GENERATION_AUTHORIZATION_PATH=/srv/demo-data/storage/rag-lite/model-grant.json

RUN useradd --create-home demo && mkdir -p /srv/demo-data && chown demo /srv/demo-data
USER demo

EXPOSE 8000
CMD ["sh", "scripts/demo_entrypoint.sh"]
