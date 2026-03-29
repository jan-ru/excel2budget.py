#!/usr/bin/env bash
# Check if frontend/src/types/api.d.ts is stale relative to backend Pydantic models.
#
# This script starts the backend temporarily, regenerates types into a temp file,
# and compares against the committed api.d.ts. Exits non-zero if they differ.
#
# Requires: backend venv set up, frontend node_modules installed.

set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
GENERATED="$REPO_ROOT/frontend/src/types/api.d.ts"
TEMP_GENERATED=$(mktemp)
PORT=18321

cleanup() {
    rm -f "$TEMP_GENERATED"
    if [ -n "${SERVER_PID:-}" ]; then
        kill "$SERVER_PID" 2>/dev/null || true
        wait "$SERVER_PID" 2>/dev/null || true
    fi
}
trap cleanup EXIT

# Start backend from the backend dir with PYTHONPATH pointing to repo root
PYTHONPATH="$REPO_ROOT" uv run --directory "$REPO_ROOT/backend" \
    uvicorn backend.app.main:app --port "$PORT" --log-level error &
SERVER_PID=$!

# Wait for the server to be ready (up to 10 seconds)
for i in $(seq 1 20); do
    if curl -sf "http://localhost:$PORT/openapi.json" > /dev/null 2>&1; then
        break
    fi
    sleep 0.5
done

if ! curl -sf "http://localhost:$PORT/openapi.json" > /dev/null 2>&1; then
    echo "Error: backend did not start within 10 seconds"
    exit 1
fi

# Generate types to temp file
npx --prefix "$REPO_ROOT/frontend" \
    openapi-typescript "http://localhost:$PORT/openapi.json" -o "$TEMP_GENERATED" 2>/dev/null

# Compare
if ! diff -q "$GENERATED" "$TEMP_GENERATED" > /dev/null 2>&1; then
    echo "ERROR: $GENERATED is stale."
    echo "Backend Pydantic models have changed but types were not regenerated."
    echo ""
    echo "Run: cd frontend && npm run generate-types"
    exit 1
fi

echo "api.d.ts is up to date."
