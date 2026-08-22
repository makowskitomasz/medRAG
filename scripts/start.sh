#!/usr/bin/env bash
# Start medRAG dev stack with native reranker (MPS on Mac).
#
# Usage:
#   ./scripts/start.sh          # dev mode (hot reload)
#   ./scripts/start.sh prod     # production mode

set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

MODE="${1:-dev}"

if [[ "$MODE" == "dev" ]]; then
  COMPOSE_FILES="-f docker-compose.yml -f docker-compose.dev.yml -f docker-compose.native-reranker.yml"
else
  COMPOSE_FILES="-f docker-compose.yml -f docker-compose.native-reranker.yml"
fi

# All services except reranker
SERVICES=$(docker compose $COMPOSE_FILES config --services | grep -v '^reranker$' | tr '\n' ' ')

echo "▶ Starting Docker services (no build)..."
docker compose $COMPOSE_FILES up -d --no-build $SERVICES || true

echo "▶ Stopping Docker reranker container (port 8005 needed for native)..."
docker compose $COMPOSE_FILES stop reranker 2>/dev/null || true
docker compose $COMPOSE_FILES rm -f reranker 2>/dev/null || true

echo "▶ Freeing port 8005 (killing any leftover process)..."
lsof -ti :8005 | xargs kill -9 2>/dev/null || true

echo "▶ Loading .env..."
set -a
# shellcheck disable=SC1091
[ -f "$ROOT/.env" ] && source "$ROOT/.env"
set +a

echo "▶ Starting native reranker on port 8005 (MPS)..."
cd "$ROOT/services/reranker"
exec uv run uvicorn app.main:app --host 0.0.0.0 --port 8005
