# Plan implementacji — medRAG mikroserwisy

Format: każde zadanie jest atomowe, da się oszacować, da się delegować.
Symbol `[C]` = zadanie idealne do delegowania Claude'owi.

Konwencja branchy: `feature/phase-X.Y-krotki-opis` → PR → `develop` → merge → `main` (release)

---

## Faza 0 — Setup & Infra (cel: docker-compose ze stackiem startuje, CI zielone)

- [x] **0.0** Branching: utwórz `develop`, ustaw branch protection na `main` i `develop` (wymagany PR + CI green)
- [x] **0.1** `[C]` Inicjalizacja monorepo: struktura `services/`, `shared/`, `frontend/`, `docker/`, `docs/`, `scripts/`
- [x] **0.2** `[C]` Setup uv + bazowy `pyproject.toml` template per service (ruff, mypy, pytest w dev deps)
- [x] **0.3** `[C]` Bazowy `Dockerfile` dla serwisów Python (multi-stage, slim, non-root `appuser`)
- [x] **0.4** `[C]` `docker-compose.yml` z MongoDB + Weaviate + RabbitMQ + healthchecks
- [x] **0.5** `[C]` Shared lib (`shared/`): structured logger z `trace_id`, base Pydantic Settings, AMQP client wrapper, MongoDB client wrapper
- [x] **0.6** `[C]` GitHub Actions: CI workflow (lint ruff + typecheck mypy + pytest) na PR do `develop`/`main`
- [x] **0.7** `[C]` GitHub Actions: CD workflow (docker compose build + healthcheck smoke test) na push do `develop`
- [ ] **0.8** Smoke test lokalny: `docker compose up`, połączenie do każdej bazy z hello-world serwisu
- [x] **0.9** `[C]` `.github/PULL_REQUEST_TEMPLATE.md` i podstawowy `.gitignore`

**Branch**: `feature/phase-0-setup-infra`

---

## Faza 1 — Auth + Gateway (cel: logowanie działa, JWT walidowany przez gateway)

- [x] **1.1** `[C]` Auth Service: model `User` (Pydantic + Mongo), kolekcja `users`, indeksy
- [x] **1.2** `[C]` Auth: endpointy `POST /register`, `POST /login`, `GET /me` z bcrypt + PyJWT
- [x] **1.3** `[C]` Auth: middleware FastAPI do walidacji JWT (do reuse w innych serwisach)
- [x] **1.4** `[C]` API Gateway: routing do serwisów (httpx.AsyncClient), forward JWT
- [x] **1.5** `[C]` Auth: seed admin user przy starcie z env (`ADMIN_EMAIL`, `ADMIN_PASSWORD`)
- [x] **1.6** `[C]` Unit testy Auth: register, login, invalid credentials, expired token
- [x] **1.7** Test e2e: rejestracja → login → call do chronionego endpointa przez gateway

**Branch**: `feature/phase-1-auth-gateway`

---

## Faza 2 — Ingestion pipeline (cel: PDF → wektory w Weaviate)

- [x] **2.1** `[C]` Modele: `Project`, `Document`, `Chunk` w `shared/models/`
- [x] **2.2** `[C]` Ingestion API: endpoint `POST /projects/{id}/documents` (multipart upload)
- [x] **2.3** `[C]` Ingestion: walidacja typu pliku, content_hash (deduplikacja), zapis do `/tmp/uploads`
- [x] **2.4** `[C]` Ingestion: insert document w Mongo + publish `document.uploaded` do RabbitMQ
- [x] **2.5** `[C]` RabbitMQ topology: exchange `documents` (topic), queues + bindings + DLX (dead-letter)
- [x] **2.6** `[C]` Parser Service: konsument `document.uploaded`, integracja z `pypdf` (DOCX: `python-docx`)
- [x] **2.7** `[C]` Parser: zapis `extracted_text` do Mongo, cleanup `/tmp`, publish `document.parsed`
- [x] **2.8** `[C]` Chunking Service: strategia `recursive` (LangChain `RecursiveCharacterTextSplitter`) jako default
- [x] **2.9** `[C]` Chunking: strategia `fixed_512` i `semantic` jako dodatkowe warianty
- [x] **2.10** `[C]` Chunking: insert chunks do Mongo, publish `document.chunked`
- [x] **2.11** `[C]` Embedding Service: abstrakcja `EmbeddingProvider`, implementacja `LocalBGEProvider` (BGE-m3)
- [x] **2.12** `[C]` Embedding: batch processing, publish `chunks.embedded`
- [x] **2.13** `[C]` Indexing Service: schema Weaviate (klasa `Chunk`), insert vectors
- [x] **2.14** `[C]` Status tracking: każdy serwis aktualizuje `documents.status_history` z `trace_id`
- [x] **2.15** `[C]` Testy jednostkowe: chunking strategies, parser (mock pypdf), embedding batch
- [x] **2.16** Test e2e: upload PDF → status `indexed` w Mongo, wektory w Weaviate

**Branche**: `feature/phase-2.1-shared-models`, `feature/phase-2.2-ingestion-api`, `feature/phase-2.3-parser-chunking`, `feature/phase-2.4-embedding-indexing`

---

## Faza 3 — Query pipeline (cel: pytanie → streamowana odpowiedź z cytowaniami)

- [ ] **3.1** `[C]` Retrieval Service: hybrid search w Weaviate (`hybrid()`: BM25 + vector + alpha z project settings)
- [ ] **3.2** `[C]` Retrieval: enrichment chunków metadanymi z Mongo (tytuł, strona, projekt)
- [ ] **3.3** `[C]` Reranker Service: cross-encoder BGE-reranker-v2-m3 (sentence-transformers)
- [ ] **3.4** `[C]` Query Processor: query rewriting (LLM call) + HyDE (generuj hipotetyczny dokument)
- [ ] **3.5** `[C]` Generation Service: prompt template + integracja z openai SDK przez OpenRouter (`base_url=https://openrouter.ai/api/v1`, model konfigurowalny przez `LLM_MODEL`)
- [ ] **3.6** `[C]` Generation: streaming SSE (`StreamingResponse` FastAPI)
- [ ] **3.7** `[C]` Generation: ekstrakcja cytowań z odpowiedzi
- [ ] **3.8** `[C]` Orchestrator: abstrakcja `RagPipeline`, implementacja `VanillaPipeline`
- [ ] **3.9** `[C]` Orchestrator: implementacja `HydePipeline` (używa Query Processor)
- [ ] **3.10** `[C]` Orchestrator: routing do pipeline'u na podstawie `project.settings.rag_mode`
- [ ] **3.11** `[C]` Orchestrator: zapis konwersacji do Mongo (`conversations` collection)
- [ ] **3.12** `[C]` Orchestrator: publish `query.completed` do RabbitMQ
- [ ] **3.13** `[C]` Testy jednostkowe: retrieval mock, reranker, citation extraction, pipeline routing
- [ ] **3.14** Test e2e: pytanie przez gateway → streamowana odpowiedź z cytowaniami

**Branche**: `feature/phase-3.1-retrieval-reranker`, `feature/phase-3.2-generation-streaming`, `feature/phase-3.3-orchestrator-vanilla`, `feature/phase-3.4-orchestrator-hyde`

---

## Faza 4 — Self-Reflection + Multi-Agent RAG (cel: 4 tryby działają)

- [ ] **4.1** `[C]` Orchestrator: `SelfReflectionPipeline` (iteracyjne refinowanie: max 2 rundy)
- [ ] **4.2** `[C]` Orchestrator: `MultiAgentPipeline` (router agent + specialist agents + aggregator)
- [ ] **4.3** Decyzja: które architektury agentowe (MARAG/MADAM) implementować — **TWOJA DECYZJA**
- [ ] **4.4** `[C]` Testy integracyjne: wszystkie 4 tryby RAG na tym samym zapytaniu testowym

**Branch**: `feature/phase-4-advanced-rag-modes`

---

## Faza 5 — Admin + Eval (cel: metryki RAGAS zbierane automatycznie)

- [ ] **5.1** `[C]` Admin Service: CRUD projektów z `settings` (chunking_strategy, rag_mode, embedding_provider)
- [ ] **5.2** `[C]` Admin: lista dokumentów ze statusem, paginacja, filtrowanie
- [ ] **5.3** `[C]` Admin: endpoint `POST /projects/{id}/reindex` (re-publish events)
- [ ] **5.4** `[C]` Eval Service: konsument `query.completed`, integracja z RAGAS
- [ ] **5.5** `[C]` Eval: model `EvalLog`, zapis do Mongo (`eval_logs`)
- [ ] **5.6** `[C]` Admin: endpoint GET eval logs z filtrem po `rag_mode`, export CSV

**Branch**: `feature/phase-5-admin-eval`

---

## Faza 6 — Frontend Next.js (cel: działające demo UI)

- [ ] **6.1** `[C]` Setup Next.js 15 z TypeScript, Tailwind, shadcn/ui (na bazie designu z claude.ai/design)
- [ ] **6.2** `[C]` Strona logowania (form + call do `/auth/login` + zapis JWT w cookie httpOnly)
- [ ] **6.3** `[C]` Layout z sidebar (lista konwersacji) + main content (chat)
- [ ] **6.4** `[C]` Chat UI ze streamingiem (EventSource API dla SSE)
- [ ] **6.5** `[C]` Wyświetlanie cytowań pod wiadomością (popover ze snippetem)
- [ ] **6.6** `[C]` Admin panel: tabela projektów, tabela dokumentów ze statusem (polling)
- [ ] **6.7** `[C]` Admin: formularz uploadu z drag&drop (react-dropzone)
- [ ] **6.8** `[C]` Historia konwersacji (lista + detal)
- [ ] **6.9** `[C]` GitHub Actions: frontend CI (tsc --noEmit + eslint + vitest) na PR

**Branche**: `feature/phase-6.1-frontend-setup`, `feature/phase-6.2-chat-ui`, `feature/phase-6.3-admin-panel`

---

## Faza 7 — Ewaluacja eksperymentalna (cel: wyniki do pracy)

- [ ] **7.1** Wybór i przygotowanie datasetu Wikipedia (subset, 50-100 QA pairs) — **TWOJE**
- [ ] **7.2** Wybór i przygotowanie datasetu drug interactions — **TWOJE**
- [ ] **7.3** `[C]` Skrypt ewaluacji: uruchom N pytań w każdym trybie RAG, zbierz metryki
- [ ] **7.4** Eksperyment: uruchom ewaluację dla wszystkich 4 trybów × 2 datasety — **TWOJE**
- [ ] **7.5** `[C]` Wykresy (matplotlib/seaborn): faithfulness, answer_relevancy, context_precision vs rag_mode, latency
- [ ] **7.6** Interpretacja wyników i wnioski naukowe — **TWOJE**

**Branch**: `feature/phase-7-eval-experiment`

---

## Podsumowanie

| Faza | Zadania | [C] delegowane |
|---|---|---|
| 0. Setup & CI/CD | 9 | 7 |
| 1. Auth + Gateway | 7 | 6 |
| 2. Ingestion | 16 | 14 |
| 3. Query pipeline | 14 | 13 |
| 4. Advanced RAG | 4 | 3 |
| 5. Admin + Eval | 6 | 6 |
| 6. Frontend | 9 | 9 |
| 7. Ewaluacja | 6 | 3 |
| **Razem** | **71** | **61** |

~65 zadań do delegowania Claude'owi, ~12 wymaga Twojego głębokiego zaangażowania.
