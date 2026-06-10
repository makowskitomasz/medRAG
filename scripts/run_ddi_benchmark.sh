#!/usr/bin/env bash
# Run DDI benchmark against all 9 RAG modes.
#
# Usage:
#   ./scripts/run_ddi_benchmark.sh <PROJECT_ID> <JWT_TOKEN> [extra benchmark_runner args]
#
# Example:
#   ./scripts/run_ddi_benchmark.sh 683f1a2b... eyJhbGci...
#   ./scripts/run_ddi_benchmark.sh 683f1a2b... eyJhbGci... --modes vanilla,multi_agent --dry-run
#
# Results land in: results/ddi_results.json
# Analysis:        python scripts/analyze_ddi.py --input results/ddi_results.json

set -euo pipefail

PROJECT_ID="${1:?Usage: $0 <PROJECT_ID> <JWT_TOKEN>}"
TOKEN="${2:?Usage: $0 <PROJECT_ID> <JWT_TOKEN>}"
shift 2

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"

DATASET="$REPO_ROOT/data/ddi_qa.json"
OUTPUT="$REPO_ROOT/results/ddi_results.json"
GATEWAY="${GATEWAY_URL:-http://localhost:8000}"

if [[ ! -f "$DATASET" ]]; then
  echo "ERROR: dataset not found at $DATASET"
  echo "       Run scripts/prepare_drugbank_xml.py first."
  exit 1
fi

QA_COUNT=$(python3 -c "import json; d=json.load(open('$DATASET')); print(len(d))")
echo "Dataset:    $DATASET  ($QA_COUNT questions)"
echo "Project ID: $PROJECT_ID"
echo "Output:     $OUTPUT"
echo "Gateway:    $GATEWAY"
echo ""

mkdir -p "$REPO_ROOT/results"

cd "$SCRIPT_DIR"
python3 benchmark_runner.py \
  --dataset "$DATASET" \
  --project-id "$PROJECT_ID" \
  --token "$TOKEN" \
  --gateway-url "$GATEWAY" \
  --output "$OUTPUT" \
  --concurrency 1 \
  "$@"

echo ""
echo "Benchmark done. Run analysis:"
echo "  python scripts/analyze_ddi.py --input $OUTPUT --project-id $PROJECT_ID"
