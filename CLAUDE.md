# CLAUDE.md — medRAG

## Thesis context

**Title**: "Retrieval-Augmented Generation for Improving Large Language Models: Technology Analysis and Design of an Experimental Advisory System"

**System**: Drug interaction advisory demonstrator — when a patient takes multiple drugs prescribed by different doctors, the system detects potential conflicts. Proof-of-concept, not a production medical device.

**Research**: Compare RAG architectures (Vanilla, HyDE/Query Rewriting, Self-Reflection/Self-RAG, Multi-Agent) on medical datasets. Evaluate with RAGAS metrics.

**Deadline**: working system by end of June 2026; thesis writing July–August 2026.

---

## Architecture

Two pipelines:

- **Ingestion** (async, event-driven via RabbitMQ): upload → parse → chunk → embed → index
- **Query** (sync REST + SSE): gateway → orchestrator → [query processor] → retrieval → reranker → generation

See `diagrams/` for C4 container diagram and sequence diagrams (PlantUML `.puml` sources + rendered `.png`).

---

## Services

| Service | Port | Responsibility |
|---|---|---|
| `api-gateway` | 8000 | JWT validation, routing to services |
| `auth` | 8001 | register/login, PyJWT + bcrypt |
| `orchestrator` | 8002 | query flow coordinator, saves conversations |
| `query-processor` | 8003 | query rewrite, HyDE |
| `retrieval` | 8004 | hybrid search (Weaviate BM25 + vector, alpha configurable) |
| `reranker` | 8005 | cross-encoder (BGE-reranker-v2-m3) |
| `generation` | 8006 | LLM call + SSE streaming + citation extraction |
| `ingestion` | 8007 | file upload, content_hash dedup, publish to MQ |
| `parser` | 8008 | pypdf / docling text extraction |
| `chunking` | 8009 | configurable strategies (fixed / recursive / semantic) |
| `embedding` | 8010 | configurable provider (local BGE-m3 / Cohere / OpenAI) |
| `indexing` | 8011 | Weaviate vector insert + status update |
| `admin` | 8012 | project CRUD, document list, reindex trigger |
| `eval` | 8013 | RAGAS metrics, async consumer of `query.completed` |

---

## Stack

- **Python services**: FastAPI + **uv** (not poetry, not pip — always use uv)
- **Frontend**: Next.js 15 + TypeScript + Tailwind + shadcn/ui; designs from claude.ai/design
- **Databases**: MongoDB 7, Weaviate 1.27
- **Message broker**: RabbitMQ 3.13
- **LLM**: Anthropic Claude (`claude-sonnet-4-6` default); configurable via `LLM_PROVIDER` env
- **Embeddings**: abstracted provider; default `local_bge` (BGE-m3 via sentence-transformers); configurable via `EMBEDDING_PROVIDER`
- **Reranker**: BGE-reranker-v2-m3 via sentence-transformers cross-encoder
- **Containerization**: Docker multi-stage non-root + docker-compose

---

## Repo layout

```
medRAG/
├── services/
│   ├── api-gateway/
│   ├── auth/
│   ├── orchestrator/
│   ├── query-processor/
│   ├── retrieval/
│   ├── reranker/
│   ├── generation/
│   ├── ingestion/
│   ├── parser/
│   ├── chunking/
│   ├── embedding/
│   ├── indexing/
│   ├── admin/
│   └── eval/
├── shared/              # shared Python lib: logger, MQ client, Mongo client, base models
├── frontend/            # Next.js 15
├── docker/              # per-service Dockerfiles, compose overrides
├── docs/
│   ├── SDD.md           # system design document
│   ├── adr/             # architecture decision records
│   ├── plan_zadan.md    # task checklist
│   └── wycena.md        # time estimate
├── diagrams/            # PlantUML sources + rendered PNGs
├── scripts/             # seed scripts, eval runners
├── .env.example
└── docker-compose.yml
```

---

## Python conventions (every service)

- Managed with **uv**; `pyproject.toml` + `uv.lock` at service root
- Python 3.12; base image `python:3.12-slim`; multi-stage build; non-root user `appuser`
- Structured JSON logging via `shared.logger` with `trace_id` propagated from `X-Trace-Id` header/AMQP property
- Settings via `shared.config.BaseSettings` (pydantic-settings, reads `.env`)
- Every service exposes `GET /health → {"status": "ok", "service": "<name>"}`
- No module-level side effects; dependency injection via FastAPI `Depends`
- Type hints everywhere; no `Any` unless unavoidable

---

## Strategy pattern — configurable per project

Active strategy stored in MongoDB `projects.settings`. Allows comparing approaches without code changes:

| Setting | Options |
|---|---|
| `chunking_strategy` | `fixed_512` \| `recursive` \| `semantic` |
| `embedding_provider` | `local_bge` \| `cohere` \| `openai` |
| `rag_mode` | `vanilla` \| `hyde` \| `self_reflection` \| `multi_agent` |

The `orchestrator` reads `rag_mode` from project settings and selects the pipeline variant. New modes are added without touching existing code.

---

## Environment variables

See `.env.example`. Key variables:

```
ANTHROPIC_API_KEY=
LLM_PROVIDER=anthropic          # anthropic | openai
LLM_MODEL=claude-sonnet-4-6

EMBEDDING_PROVIDER=local_bge    # local_bge | cohere | openai
COHERE_API_KEY=

MONGODB_URI=mongodb://mongo:27017/medrag
WEAVIATE_URL=http://weaviate:8080
RABBITMQ_URL=amqp://guest:guest@rabbitmq:5672/

JWT_SECRET=changeme
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=1440

ADMIN_EMAIL=admin@medrag.local
ADMIN_PASSWORD=changeme
```

---

## Git workflow

### Branches

| Branch | Purpose | Who merges |
|---|---|---|
| `main` | Stable, demo-ready. Protected — PR required, CI must be green. | From `develop` only |
| `develop` | Integration branch. All features land here first. Protected — PR required, CI must be green. | From feature branches |
| `feature/FAZA-X.Y-short-desc` | One task or logical group of tasks from `plan_zadan.md` | You, then PR → `develop` |

### Branch naming examples

```
feature/FAZA-0-setup-infra
feature/FAZA-1-auth-gateway
feature/FAZA-2.1-shared-models
feature/FAZA-3.2-generation-streaming
fix/rabbitmq-connection-retry
chore/update-dependencies
```

### Workflow per task

```
git checkout develop
git pull
git checkout -b feature/FAZA-X.Y-description
# implement
git push -u origin feature/FAZA-X.Y-description
# open PR → develop
# CI runs → merge when green
```

### Release to main

When a phase is complete and demo-ready:
```
git checkout main && git merge develop --no-ff
git tag v0.X-faza-Y-done
```

---

## CI/CD (GitHub Actions)

### Workflows

| File | Trigger | What it does |
|---|---|---|
| `.github/workflows/ci.yml` | PR → `develop` or `main` | Lint (ruff), typecheck (mypy), pytest per changed service; frontend tsc + eslint |
| `.github/workflows/cd.yml` | Push to `develop` | `docker compose build` + healthcheck smoke test (all services return 200 on `/health`) |

### CI details

- Python: `ruff check` + `mypy` + `pytest` (skips service if no tests yet)
- Frontend: `tsc --noEmit` + `eslint` + `vitest run` (when `frontend/` changes)
- Docker: `docker compose build` validates all Dockerfiles compile
- Smoke test on `develop`: `docker compose up -d` → wait for healthchecks → `curl /health` per service → `docker compose down`

### Secrets needed in GitHub repo

```
ANTHROPIC_API_KEY      # for integration tests that call LLM
```

---

## What to delegate to Claude [C]

Anything from `docs/plan_zadan.md` marked `[C]`:
- All FastAPI boilerplate (models, endpoints, DI, settings, middleware)
- Docker / docker-compose configuration
- Weaviate schema and query code
- RabbitMQ topology, consumer/publisher wrappers
- Shared lib code (logger, clients, base models)
- React/Next.js components, forms, layouts
- RAGAS eval integration
- ADR documents
- Thesis chapter drafts (architecture, implementation sections)

## What requires your judgment

- Experiment design: chunking sizes, hybrid search alpha, top-k values
- Dataset selection and quality assessment (drug interactions source)
- Interpretation of RAGAS metrics and scientific conclusions
- Which RAG architecture to recommend in the thesis
- All scientific claims and original analysis

---

## Datasets

1. **Wikipedia** — general medical knowledge baseline
2. **Drug interactions** — TBD; candidates: DrugBank, OpenFDA, NDF-RT, SIDER, DrugCentral

---

## Current phase

**Faza 0 — Setup** (week 1: 5–11 May 2026)

Next: `docker-compose` with MongoDB + Weaviate + RabbitMQ starts and passes healthchecks. See `docs/plan_zadan.md` for full checklist.
