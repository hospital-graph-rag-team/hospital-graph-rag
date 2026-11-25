#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "Starting ClinicalGraph 2.0 Backend (http://127.0.0.1:8000)..."
.venv/bin/python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 &
BACKEND_PID=$!

cleanup() {
  echo ""
  echo "Stopping ClinicalGraph 2.0 services..."
  kill "$BACKEND_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

echo "Starting ClinicalGraph 2.0 Frontend (http://localhost:3000)..."
cd "$ROOT_DIR/apps/web"
npm run dev
