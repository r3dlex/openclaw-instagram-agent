#!/usr/bin/env bash
# Zero-install runner: uses Docker if available, otherwise Poetry.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

if ! [ -f .env ]; then
    echo "ERROR: .env file not found. Copy .env.example to .env and fill in values."
    echo "  cp .env.example .env"
    exit 1
fi

if command -v docker &>/dev/null; then
    echo "Using Docker..."
    docker compose run --rm agent "$@"
elif command -v poetry &>/dev/null; then
    echo "Using Poetry..."
    poetry install --quiet
    poetry run openclaw-instagram "$@"
else
    echo "ERROR: Neither Docker nor Poetry found."
    echo "Install one of:"
    echo "  - Docker: https://docs.docker.com/get-docker/"
    echo "  - Poetry: https://python-poetry.org/docs/#installation"
    exit 1
fi
