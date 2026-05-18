# System Design Document — medRAG

## 1. Goal

A technology demonstrator for drug interaction advisory using Retrieval-Augmented Generation. The system answers questions like: *"Can a patient with condition X take drug Y alongside drug Z?"* by retrieving relevant medical knowledge and generating a cited answer.

Secondary goal: compare all 9 RAG architectures experimentally using custom evaluation metrics (no RAGAS dependency).

---

## 2. Users

| Actor | Description |
|---|---|
| **User** | Queries the system via chat interface |
| **Admin** | Uploads documents, manages projects, monitors ingestion status |

---

## 3. Functional requirements

### Ingestion
- Upload PDF documents to a named project
- Automatic pipeline: parse → chunk → embed → index into vector store
- Configurable chunking strategy per project
- Document status tracking with full history

### Query
- Submit natural-language query against a project's knowledge base
- Streamed answer (SSE) with inline citations (chunk references)
- Configurable RAG mode per project

### Admin
- Create/update/delete projects with settings (chunking strategy, RAG mode, embedding provider)
- View document list with status
- Trigger reindex for a project

### Evaluation
- Asynchronous metric computation after each query (RabbitMQ consumer of `query.completed`)
- Two evaluation modes: **benchmark** (with `gold_answer`) and **production** (without)
- Benchmark mode: token F1, EM, faithfulness (LLM-as-judge), answer_relevance (BGE cosine)
- Production mode: faithfulness, context_relevance, citation_precision, latency_ms, token_count
- Results stored in `eval_results` collection, queryable by `rag_mode` and `project_id`
- Export eval results to CSV for cross-architecture comparison

---

## 4. Non-functional requirements

- All services independently deployable via Docker
- Embedding provider swappable without code changes
- RAG architecture swappable without code changes
- All queries traced end-to-end via `trace_id`
- Streaming latency: first token < 2s after query submission (target)

---

## 5. Architecture decisions

| Decision | Choice | Rationale |
|---|---|---|
| Service orchestration | docker-compose (not k8s) | Scope: thesis demonstrator, single machine |
| Vector store | Weaviate 1.27 | Hybrid search (BM25 + vector) built-in, self-hosted |
| Document store | MongoDB 7 | Flexible schema for chunk metadata + status history |
| Message broker | RabbitMQ 3.13 | Lower overhead than Kafka for this scale |
| Python tooling | uv | Fast, lockfile-first, modern |
| LLM default | Claude (claude-sonnet-4-6) | Best reasoning, strong tool use, native streaming |
| Embedding default | BGE-m3 (local) | No API cost, strong multilingual performance |
| Reranker | BGE-reranker-v2-m3 | SOTA cross-encoder, free, pairs with BGE-m3 |

Full rationale in `docs/adr/`.

---

## 6. Data models (simplified)

### `users`
```
_id, email, hashed_password, role (user|admin), created_at
```

### `projects`
```
_id, name, description, settings: {
  chunking_strategy, embedding_provider, rag_mode, hybrid_alpha, top_k, rerank_top_n
}, created_by, created_at
```

### `documents`
```
_id, project_id, filename, content_hash, status (uploaded|parsed|chunked|embedded|indexed|failed),
status_history: [{status, timestamp, trace_id, error?}], extracted_text, stats: {chunk_count}
```

### `chunks`
```
_id, document_id, project_id, chunk_index, content, page, metadata, weaviate_id
```

### `conversations`
```
_id, project_id, user_id, messages: [{role, content, citations, rag_mode, trace_id, timestamp}]
```

### `eval_logs`
```
_id, conversation_id, trace_id, query, answer, contexts, faithfulness, answer_relevancy,
context_precision, context_recall, latency_ms, rag_mode, timestamp
```

---

## 7. RAG pipeline variants

All variants share the same retrieval + reranker layer. They differ in how the query is processed and how generation is triggered.

| Mode | Flow | Key idea |
|---|---|---|
| `vanilla` | query → retrieval → rerank → generate | Baseline; no query transformation |
| `hyde` | query → LLM generates hypothetical doc → embed hypothetical doc → retrieval → rerank → generate | Hypothetical Document Embeddings (Gao et al. 2022); improves vector recall for complex questions |
| `query_rewriting` | query → LLM rewrites to medical terminology → retrieval → rerank → generate | Bridges colloquial queries and technical corpus vocabulary (e.g. "mixing pills" → "drug-drug interaction pharmacokinetics") |
| `self_reflection` | vanilla flow → LLM self-scores answer sufficiency (0–1) → if below threshold: refine query + retry (max 2 rounds) | Self-RAG style (Asai et al. 2023); catches incomplete answers before returning to user |
| `multi_agent` | query → router agent classifies intent (mechanism / risk / dosing / contraindication) → specialist agents run parallel retrieval variants → aggregator synthesises | Multi-perspective retrieval; each agent queries with a different reformulation |
| `corrective_rag` | vanilla flow → retrieved docs scored for relevance → low-relevance docs trigger web search fallback → regenerate | CRAG (Yan et al. 2024); handles knowledge gaps in the local corpus |

New modes are added as new orchestrator strategy classes implementing a common `RagPipeline` interface. The `rag_mode` field in `projects.settings` selects the active pipeline without code changes.

### Pipeline selection rationale for thesis

The six modes represent three generations of RAG:
1. **Naive** (`vanilla`) — baseline, minimal processing
2. **Query-side augmentation** (`hyde`, `query_rewriting`) — transform the question before retrieval
3. **Answer-side verification** (`self_reflection`, `corrective_rag`) — validate and refine after generation
4. **Decomposition** (`multi_agent`) — break the question into sub-tasks

This taxonomy maps directly to a thesis chapter comparing retrieval quality and generation faithfulness across generations.

---

## 8. Ingestion event flow

```
document.uploaded  →  Parser  →  document.parsed
document.parsed    →  Chunking →  document.chunked
document.chunked   →  Embedding → chunks.embedded
chunks.embedded    →  Indexing   (no further event, updates Mongo directly)
```

DLX (dead-letter exchange) on every queue. Failed messages land in `*.failed` queue with original headers preserved.

---

## 9. Evaluation approach

### Datasets

**Dataset A — Wikipedia medical QA** (benchmark, general baseline)
- ~100 QA pairs from Wikipedia medical articles
- Used to establish general RAG quality baseline
- Has `gold_answer` → enables token F1, EM, answer_relevance

**Dataset B — Drug interactions** (benchmark, domain-specific)
- 50–100 curated QA pairs covering:
  - Warfarin + Aspirin (bleeding risk, INR monitoring)
  - Warfarin + NSAIDs (GI hemorrhage risk)
  - Statins + CYP3A4 inhibitors (myopathy risk)
  - ACE inhibitors + potassium-sparing diuretics (hyperkalemia)
  - Metformin + contrast media (lactic acidosis)
  - SSRIs + MAOIs (serotonin syndrome, washout periods)
  - Clopidogrel + PPIs (CYP2C19 inhibition)
  - Digoxin + amiodarone/verapamil (narrow therapeutic index)
  - Rifampicin + oral contraceptives (CYP3A4 induction)
- Has `gold_answer` → full benchmark mode metrics

**Dataset C — Production queries** (no ground truth)
- Real-world queries without reference answers
- Production mode metrics only

### Metrics

**Benchmark mode** (requires `gold_answer`):

| Metric | What it measures | How computed |
|---|---|---|
| `token_f1` | Token overlap between answer and gold | Standard NLP F1 on token sets |
| `em` | Exact match after normalisation | Lowercase + strip punctuation |
| `faithfulness` | Answer grounded in retrieved context | LLM-as-judge (Claude, single prompt) |
| `answer_relevance` | Semantic similarity of answer to question | BGE cosine similarity |

**Production mode** (no `gold_answer` required):

| Metric | What it measures | How computed |
|---|---|---|
| `faithfulness` | Answer grounded in retrieved context | LLM-as-judge |
| `context_relevance` | Quality of retrieved evidence set | Avg reranker score of passed chunks |
| `citation_precision` | Fraction of cited chunks in final answer | `len(citations) / len(chunks_passed)` |
| `latency_ms` | End-to-end query latency | Timestamp from `query.completed` event |
| `token_count` | Input + output tokens | From LLM response metadata |

### Eval service architecture

```
query.completed (RabbitMQ)
    └── eval_service consumer
            ├── extract: query, answer, chunks, citations, latency_ms, token_count, rag_mode
            ├── if gold_answer present → benchmark mode (all 6 metrics)
            └── else → production mode (faithfulness, context_relevance, citation_precision, latency, tokens)
            └── write to MongoDB eval_results
                    { rag_mode, project_id, question, metrics{}, eval_mode, timestamp }
```

Benchmark runner (`scripts/benchmark_runner.py`):
- Reads QA pairs from JSON file (`{ question, gold_answer }`)
- POSTs each to `/chat/query` with `gold_answer` injected into the event payload
- Iterates over all 9 `rag_mode` values
- Outputs comparison table: `rag_mode × metric`

### Experiment design

Run all **9 RAG modes** × **2 datasets** × **same QA pairs**. Compare:
- All benchmark metrics per mode
- Latency P50/P95 per mode
- Token cost per query per mode

Expected hypotheses:
- `self_reflection` and `corrective_rag` score higher on `faithfulness`
- `hyde` and `query_rewriting` improve `answer_relevance` on colloquial queries
- `iterative_multihop` scores higher on complex multi-fact questions
- `vanilla` is fastest and cheapest but least faithful
- `rare_rag` approaches best-of-all but at highest latency cost

---

## 10. Out of scope

- Production security hardening
- HIPAA / GDPR compliance
- GPU inference (CPU-only target for thesis)
- Multi-tenant isolation
- Load balancing / horizontal scaling
