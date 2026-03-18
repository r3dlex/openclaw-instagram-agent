#!/usr/bin/env bash
# Run test suite via Docker or Poetry.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

if command -v docker &>/dev/null; then
    echo "Running tests in Docker..."
    docker compose run --rm --entrypoint pytest agent tests/ -v "$@"
elif command -v poetry &>/dev/null; then
    echo "Running tests with Poetry..."
    poetry install --quiet --with dev
    poetry run pytest tests/ -v "$@"
else
    echo "ERROR: Neither Docker nor Poetry found."
    exit 1
fi
