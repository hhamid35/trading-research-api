#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

echo "==> Starting infrastructure (PostgreSQL, Qdrant, SearXNG)..."
docker compose up -d --wait

echo "==> Setting up Python virtual environment..."
if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi
source .venv/bin/activate

echo "==> Installing Python dependencies..."
pip install -q -r requirements.txt

if [ ! -f ".env" ] && [ -f ".env.example" ]; then
  echo "==> Copying .env.example to .env..."
  cp .env.example .env
fi

echo "==> Starting API server on http://localhost:8000 ..."
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
