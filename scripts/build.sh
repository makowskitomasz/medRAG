#!/usr/bin/env bash
set -euo pipefail

DEV=${DEV:-0}

echo "==> Building images..."
if [ "$DEV" = "1" ]; then
  docker compose -f docker-compose.yml -f docker-compose.dev.yml build "$@"
else
  docker compose build "$@"
fi

echo "==> Pruning dangling images..."
docker image prune -f

echo "==> Done."
