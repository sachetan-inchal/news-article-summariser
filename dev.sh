#!/usr/bin/env bash
# Terminal 1: uvicorn --reload for Python
# Terminal 2: nodemon watching app/static, triggering browser reload
set -e
source .venv/bin/activate

if ! command -v nodemon >/dev/null 2>&1; then
  echo "[dev] nodemon not found. Install with: npm install -g nodemon"
  echo "[dev] Falling back to uvicorn --reload only (manual browser refresh)."
  exec uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
fi

# Run uvicorn in background, nodemon in foreground
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 &
UV_PID=$!
trap "kill $UV_PID 2>/dev/null || true" EXIT

nodemon --watch app/static --ext html,css,js \
  --exec "python frontend/dev-reload.py trigger"

