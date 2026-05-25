#!/usr/bin/env bash
# ZombieAgent Taint-Tracking Demo
#
# Usage:
#   bash demos/run_demo.sh
#
# Installs rich if needed, optionally starts the FastAPI dashboard server
# in the background so you can watch live events at http://localhost:8765/dashboard,
# then runs the Python demo and cleans up on exit.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"

# ---- Install dependencies ------------------------------------------------

echo "Checking dependencies…"
if ! python -c "import rich" 2>/dev/null; then
    echo "Installing rich…"
    pip install -q "rich>=13.0"
fi

# Install the package itself if not already installed
if ! python -c "import safe_mcp_proxy" 2>/dev/null; then
    echo "Installing safe-mcp-proxy (editable)…"
    pip install -q -e "$ROOT"
fi

# ---- Optional: start FastAPI dashboard server ----------------------------

SERVER_PID=""

if command -v uvicorn &>/dev/null; then
    echo "Starting FastAPI server on http://127.0.0.1:8765 …"
    cd "$ROOT"
    uvicorn api.main:app \
        --host 127.0.0.1 \
        --port 8765 \
        --log-level error \
        --no-access-log &
    SERVER_PID=$!
    sleep 1
    echo "Dashboard: http://localhost:8765/dashboard  (live audit feed)"
    echo
fi

cleanup() {
    if [ -n "$SERVER_PID" ]; then
        kill "$SERVER_PID" 2>/dev/null || true
    fi
}
trap cleanup EXIT

# ---- Run demo ------------------------------------------------------------

cd "$ROOT"
python "$SCRIPT_DIR/demo.py"
