#!/usr/bin/env bash

set -e

echo "======================================================================"
echo "             Starting MemoryOS Cognitive AI Assistant"
echo "======================================================================"
echo ""

# Activate virtual environment if present
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# Detect python / uv runner
PYTHON_CMD="python3"
if command -v /Users/vanshrajkesarwani/.local/bin/uv &> /dev/null; then
    RUNNER="/Users/vanshrajkesarwani/.local/bin/uv run --with-requirements requirements.txt"
elif command -v uv &> /dev/null; then
    RUNNER="uv run --with-requirements requirements.txt"
else
    RUNNER="python3"
fi

echo "[1/2] Starting FastAPI Backend on http://127.0.0.1:8000 ..."
PYTHONPATH=. $RUNNER -m uvicorn backend.app:app --host 127.0.0.1 --port 8000 --reload &
BACKEND_PID=$!

echo "[2/2] Backend PID: $BACKEND_PID"
echo ""
echo "======================================================================"
echo " Application is running!"
echo " Backend API & Swagger Docs: http://127.0.0.1:8000/docs"
echo " Web UI:                     http://127.0.0.1:8000 (or http://localhost:5173)"
echo "======================================================================"

# Wait for background processes
wait $BACKEND_PID
