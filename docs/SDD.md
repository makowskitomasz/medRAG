# System Design Document — medRAG

## 1. Goal

A technology demonstrator for drug interaction advisory using Retrieval-Augmented Generation. The system answers questions like: *"Can a patient with condition X take drug Y alongside drug Z?"* by retrieving relevant medical knowledge and generating a cited answer.

Secondary goal: compare RAG architectures (Vanilla, HyDE, Self-Reflection, Multi-Agent) experimentally, measured with RAGAS metrics.

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
- Asynchronous RAGAS scoring after each query
- Export eval logs to CSV for analysis

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

| Mode | Flow |
|---|---|
| `vanilla` | query → retrieval → rerank → generate |
| `hyde` | query → LLM generates hypothetical doc → retrieval → rerank → generate |
| `self_reflection` | vanilla flow → LLM self-scores answer → if insufficient: refine query + retry (max 2 iterations) |
| `multi_agent` | query → router agent → specialist agents (per topic) → aggregator → generate |

New modes are added as new orchestrator strategy classes implementing a common `RagPipeline` interface.

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

- **Datasets**: Wikipedia subset (general medical) + drug interactions dataset (TBD source)
- **Ground truth**: 50–100 QA pairs per dataset
- **Metrics (RAGAS)**: faithfulness, answer relevancy, context precision, context recall
- **Experiment**: run all 4 RAG modes against same dataset; compare metrics + latency

---

## 10. Out of scope

- Production security hardening
- HIPAA / GDPR compliance
- GPU inference (CPU-only target for thesis)
- Multi-tenant isolation
- Load balancing / horizontal scaling
