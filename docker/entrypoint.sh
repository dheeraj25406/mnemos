#!/usr/bin/env bash
set -e

echo "[Mnemos] Starting production entrypoint..."

# Wait for PostgreSQL if DATABASE_URL or SYNC_DATABASE_URL is provided
if [ -n "$SYNC_DATABASE_URL" ] || [ -n "$DATABASE_URL" ]; then
    echo "[Mnemos] Applying database migrations (alembic upgrade head)..."
    alembic upgrade head || {
        echo "[Mnemos WARNING] Alembic upgrade encountered an issue or database initializing. Retrying in 5 seconds..."
        sleep 5
        alembic upgrade head
    }
    echo "[Mnemos] Migrations applied successfully."
fi

PORT="${PORT:-8000}"
HOST="${HOST:-0.0.0.0}"

echo "[Mnemos] Launching Uvicorn on ${HOST}:${PORT}..."
exec uvicorn mnemos.api.app:app --host "$HOST" --port "$PORT"
