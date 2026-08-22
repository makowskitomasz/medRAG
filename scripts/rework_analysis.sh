#!/usr/bin/env bash
# Pulls per-question faithfulness + answer_correctness from MongoDB for both rework runs
# (newest eval_result per question inside each run window) and pipes it to the paired
# significance analysis. Mongo is the source of truth; the results JSON files accumulated
# duplicate/stale records across resumes.
set -euo pipefail

HOTPOT_PID=6a2150973b2820344a79ba44
DDI_PID=6a26774166042cbcf3f8e9b5
HOTPOT_START='2026-07-10T14:26:00Z'
DDI_START='2026-07-11T19:39:00Z'

docker compose exec -T mongo mongosh medrag --quiet --eval "
function pull(pid, startISO){
  const cut = new Date(Date.parse(startISO));
  const out = {};
  ['vanilla','iterative_multihop','multi_agent','madam_rag','rare_rag'].forEach(mode=>{
    const rows = db.eval_results.aggregate([
      {\$match:{project_id:pid, rag_mode:mode, timestamp:{\$gte:cut}}},
      {\$sort:{timestamp:1}},
      {\$group:{_id:'\$question',
                f:{\$last:'\$metrics.faithfulness'},
                c:{\$last:'\$metrics.answer_correctness'}}}
    ]).toArray();
    const m = {};
    rows.forEach(r=>{ m[r._id.trim()] = {faithfulness:r.f, answer_correctness:r.c}; });
    out[mode] = m;
  });
  return out;
}
const result = {hotpot: pull('${HOTPOT_PID}','${HOTPOT_START}'),
                ddi:    pull('${DDI_PID}','${DDI_START}')};
print(JSON.stringify(result));
" > /tmp/rework_metrics.json
cd "$(dirname "$0")" && uv run python rework_significance.py < /tmp/rework_metrics.json
