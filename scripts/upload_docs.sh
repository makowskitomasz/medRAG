#!/usr/bin/env bash
# Upload documents from a directory to medRAG ingestion pipeline.
#
# Usage:
#   ./scripts/upload_docs.sh <docs_dir> <project_id> <token>
#
# Example:
#   ./scripts/upload_docs.sh data/squad_contexts 6a2144b33b2820344a79ba42 eyJhbG...
#   ./scripts/upload_docs.sh data/drugbank_docs  6a2144b33b2820344a79ba42 eyJhbG...

set -euo pipefail

DOCS_DIR="${1:?Usage: $0 <docs_dir> <project_id> <token>}"
PROJECT_ID="${2:?Usage: $0 <docs_dir> <project_id> <token>}"
TOKEN="${3:?Usage: $0 <docs_dir> <project_id> <token>}"
GATEWAY_URL="${GATEWAY_URL:-http://localhost:8000}"

files=("$DOCS_DIR"/*.txt)
total=${#files[@]}
ok=0
fail=0

echo "Uploading $total files from $DOCS_DIR to project $PROJECT_ID..."
echo ""

for f in "${files[@]}"; do
    fname=$(basename "$f")
    response=$(curl -s -o /tmp/upload_resp.json -w "%{http_code}" \
        -X POST "${GATEWAY_URL}/ingest/projects/${PROJECT_ID}/documents" \
        -H "Authorization: Bearer ${TOKEN}" \
        -F "file=@${f}")

    if [[ "$response" == "200" || "$response" == "201" || "$response" == "202" ]]; then
        ok=$((ok + 1))
        echo "  [OK $ok/$total] $fname"
    else
        fail=$((fail + 1))
        body=$(cat /tmp/upload_resp.json)
        echo "  [FAIL $response] $fname — $body"
    fi
done

echo ""
echo "Done: $ok uploaded, $fail failed."
