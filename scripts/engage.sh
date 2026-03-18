#!/usr/bin/env bash
# Run the engagement cycle for List A (influencers).
# Usage: ./scripts/engage.sh [--list a|b|c]
set -euo pipefail
exec "$(dirname "${BASH_SOURCE[0]}")/run.sh" engage "${@:---list a}"
