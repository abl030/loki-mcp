#!/usr/bin/env bash
# Wait for Loki to be ready, then seed test data.
set -euo pipefail

LOKI_URL="${1:-http://localhost:3100}"
MAX_WAIT=120
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Waiting for Loki at ${LOKI_URL}..."
elapsed=0
while ! curl -sf "${LOKI_URL}/ready" >/dev/null 2>&1; do
    if (( elapsed >= MAX_WAIT )); then
        echo "ERROR: Loki not ready after ${MAX_WAIT}s"
        exit 1
    fi
    sleep 2
    elapsed=$((elapsed + 2))
    echo "  Waiting... (${elapsed}s)"
done
echo "Loki is ready!"

echo ""
echo "Seeding test data..."
python3 "${SCRIPT_DIR}/seed-data.py" "${LOKI_URL}"
echo ""
echo "Stack is ready for testing."
