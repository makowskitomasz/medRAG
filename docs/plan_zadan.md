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

- [x] **3.1** `[C]` Retrieval Service: hybrid search w Weaviate (`hybrid()`: BM25 + vector + alpha z project settings)
- [x] **3.2** `[C]` Retrieval: enrichment chunków metadanymi z Mongo (tytuł, strona, projekt)
- [x] **3.3** `[C]` Reranker Service: cross-encoder BGE-reranker-v2-m3 (sentence-transformers)
- [x] **3.4** `[C]` Query Processor: query rewriting (LLM call) + HyDE (generuj hipotetyczny dokument)
- [x] **3.5** `[C]` Generation Service: prompt template + integracja z openai SDK przez OpenRouter (`base_url=https://openrouter.ai/api/v1`, model konfigurowalny przez `LLM_MODEL`)
- [x] **3.6** `[C]` Generation: streaming SSE (`StreamingResponse` FastAPI)
- [x] **3.7** `[C]` Generation: ekstrakcja cytowań z odpowiedzi
- [x] **3.8** `[C]` Orchestrator: abstrakcja `RagPipeline`, implementacja `VanillaPipeline`
- [x] **3.9** `[C]` Orchestrator: implementacja `HydePipeline` (używa Query Processor)
- [x] **3.10** `[C]` Orchestrator: routing do pipeline'u na podstawie `project.settings.rag_mode`
- [x] **3.11** `[C]` Orchestrator: zapis konwersacji do Mongo (`conversations` collection)
- [x] **3.12** `[C]` Orchestrator: publish `query.completed` do RabbitMQ
- [x] **3.13** `[C]` Testy jednostkowe: retrieval mock, reranker, citation extraction, pipeline routing
- [x] **3.14** Test e2e: pytanie przez gateway → streamowana odpowiedź z cytowaniami

**Branche**: `feature/phase-3.1-retrieval-reranker`, `feature/phase-3.2-generation-streaming`, `feature/phase-3.3-orchestrator-vanilla`, `feature/phase-3.4-orchestrator-hyde`

---

## Faza 4 — Pełna biblioteka architektur RAG + RARE-RAG (cel: 9 trybów + auto-router)

Kontekst: dataset `Drug Interactions Reference Guide` zawiera m.in. interakcje warfaryna–aspiryna,
warfaryna–NLPZ, statyny–CYP3A4, inhibitory ACE–diuretyki, metformina–środki kontrastowe,
SSRI–MAOI, klopidogrel–IPP, digoksyna. Te przypadki posłużą jako pytania testowe do porównania architektur.

Architektury wg dokumentu analitycznego (bez GraphRAG): Classic RAG (vanilla), HyDE, Query Rewriting,
Self-RAG, Corrective RAG, Iterative Multi-Hop RAG, MA-RAG, MADAM-RAG, RARE-RAG.

### 4.1 Zaimplementowane (done w poprzednim commicie)
- [x] **4.1.1** `[C]` `VanillaPipeline` (Classic RAG baseline)
- [x] **4.1.2** `[C]` `HydePipeline` (Hypothetical Document Embeddings)
- [x] **4.1.3** `[C]` `QueryRewritingPipeline` (rewrite → retrieval)
- [x] **4.1.4** `[C]` `SelfReflectionPipeline` (Self-RAG: score → retry max 2×)
- [x] **4.1.5** `[C]` `MultiAgentPipeline` (MA-RAG: 3 perspektywy równolegle, dedup)
- [x] **4.1.6** `[C]` `CorrectiveRagPipeline` (ocena relevance, fallback BM25)
- [x] **4.1.7** `[C]` Generation `/evaluate` endpoint (LLM score 0–1 dla self-reflection)

### 4.2 Iterative Multi-Hop RAG
- [x] **4.2.1** `[C]` `IterativeMultiHopPipeline` — Query Processor `/decompose` rozkłada pytanie na pod-pytania → każde niezależny retrieval → agregacja dowodów → rerank → generate
- [x] **4.2.2** `[C]` Query Processor: endpoint `/decompose` — LLM rozkłada złożone pytanie na listę pod-pytań
- [x] **4.2.3** `[C]` Testy: weryfikacja dekompozycji, agregacji i deduplikacji chunków między hopami

### 4.3 MADAM-RAG (sprzeczne dowody)
- [x] **4.3.1** `[C]` `MadamRagPipeline` — conflict detection → diverse retrieval → Pro/Counter/Conflict agents → cautious aggregation → generate z uncertainty
- [x] **4.3.2** `[C]` Generation `/detect_conflict` endpoint — LLM ocenia czy chunki zawierają sprzeczne informacje (bool + confidence)
- [x] **4.3.3** `[C]` Testy: conflict detection mock, cautious answer gdy wykryto konflikt

### 4.4 RARE-RAG (Risk-Aware Routed Evidence RAG)
- [x] **4.4.1** `[C]` `RareRagPipeline` — meta-pipeline: LLM triage pytania → wybiera jeden z 8 trybów → deleguje do odpowiedniego pipeline → grounding verification → odpowiedź lub abstencja
- [x] **4.4.2** `[C]` Query Processor: endpoint `/triage` — klasyfikacja pytania: complexity (simple/standard/complex/multi_hop), conflict_risk (low/medium/high), returns route decision
- [x] **4.4.3** `[C]` Abstention path: gdy grounding score < progu po retry — zwrot `{"abstained": true, "reason": "..."}`
- [x] **4.4.4** `[C]` Testy: routing decisions dla każdego typu pytania, abstention przy niskim score

### 4.5 Shared models i integracja
- [x] **4.5.1** `[C]` RagMode enum: dodanie `iterative_multihop`, `madam_rag`, `rare_rag`
- [x] **4.5.2** `[C]` Factory: rejestracja wszystkich 9 pipeline'ów
- [x] **4.5.3** `[C]` Testy integracyjne: wszystkie 9 trybów na zapytaniu "What are the risks of combining aspirin and warfarin?"

**Branch**: `feature/phase-4-eval-rag-architectures`

---

## Faza 5 — Admin + Eval (cel: metryki zbierane automatycznie, bez RAGAS)

- [ ] **5.1** `[C]` Admin Service: CRUD projektów z `settings` (chunking_strategy, rag_mode, embedding_provider)
- [ ] **5.2** `[C]` Admin: lista dokumentów ze statusem, paginacja, filtrowanie
- [ ] **5.3** `[C]` Admin: endpoint `POST /projects/{id}/reindex` (re-publish events)
- [ ] **5.4** `[C]` Eval Service: konsument `query.completed`, własne metryki RAG (bez RAGAS)
  - **Tryb benchmark** (event zawiera `gold_answer`): token F1, EM, faithfulness (LLM-as-judge), answer_relevance (BGE cosine similarity pytania i odpowiedzi)
  - **Tryb produkcja** (brak `gold_answer`): faithfulness (LLM-as-judge), context_relevance (avg reranker score), citation_precision, latency_ms, token_count
  - Wyniki zapisywane do kolekcji `eval_results` z polami: `rag_mode`, `question`, `metrics`, `mode` (benchmark/production), `timestamp`
  - Skrypt `scripts/benchmark_runner.py`: wysyła pytania z Wikipedia QA dataset przez `/chat/query` z polem `gold_answer`, porównuje wyniki per `rag_mode`
- [ ] **5.5** `[C]` Eval: model `EvalResult`, zapis do Mongo (`eval_results`)
- [ ] **5.6** `[C]` Eval: `GET /results?project_id=&rag_mode=` — lista wyników; `GET /results/summary` — tabela porównawcza architektur
- [ ] **5.7** `[C]` Admin: endpoint GET eval results z filtrem po `rag_mode`, export CSV

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

- [ ] **7.1** Wybór i przygotowanie datasetu Wikipedia (subset, 800-1000 QA pairs) — **TWOJE**
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
| 4. Advanced RAG | 11 | 9 |
| 5. Admin + Eval | 6 | 6 |
| 6. Frontend | 9 | 9 |
| 7. Ewaluacja | 6 | 3 |
| **Razem** | **78** | **67** |

~67 zadań do delegowania Claude'owi, ~12 wymaga Twojego głębokiego zaangażowania.
