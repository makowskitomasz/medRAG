# Wycena czasu — RAG mikroserwisy

**Założenia:** mid-level developer (3-5 lat), Python + Next.js,
nieregularnie ~13h/tydzień (weekendy + wieczory).

## Solo (bez Claude'a)

| Faza | Godziny | Tygodnie |
|---|---|---|
| 0. Setup | 10 | 0.8 |
| 1. Auth + Gateway | 14 | 1.1 |
| 2. Ingestion (8 serwisów) | 38 | 2.9 |
| 3. Query (5 serwisów) | 30 | 2.3 |
| 4. Admin + Eval | 15 | 1.2 |
| 5. Frontend Next.js | 32 | 2.5 |
| 6. Eval + pisanie pracy | 40 | 3.1 |
| Bufor 15% | 27 | 2.1 |
| **Razem** | **~206h** | **~16 tygodni (~4 miesiące)** |

## Z Claude'em (świadoma współpraca)

| Faza | Godziny | Tygodnie |
|---|---|---|
| 0. Setup | 4 | 0.3 |
| 1. Auth + Gateway | 6 | 0.5 |
| 2. Ingestion | 17 | 1.3 |
| 3. Query | 14 | 1.1 |
| 4. Admin + Eval | 7 | 0.5 |
| 5. Frontend Next.js | 13 | 1.0 |
| 6. Eval + pisanie pracy | 22 | 1.7 |
| Bufor 15% | 12 | 0.9 |
| **Razem** | **~95h** | **~7-8 tygodni (~2 miesiące)** |

## Kalendarz tygodniowy (z Claude'em)

Start: ok. 5 maja 2026 (po spotkaniu z promotorem 7 maja).

| Tydzień | Daty | Cel |
|---|---|---|
| 1 | 5-11 maja | Setup + Auth: docker-compose stoi, działa logowanie |
| 2 | 12-18 maja | Ingestion API + Parser + Chunking: PDF → tekst → chunki |
| 3 | 19-25 maja | Embedding + Indexing: pełny ingestion, dane w Weaviate |
| 4 | 26 maja - 1 czerwca | Retrieval + Reranker: wyszukiwanie działa |
| 5 | 2-8 czerwca | Generation + Orchestrator: pełny RAG e2e (CLI/Postman) |
| 6 | 9-15 czerwca | Frontend Next.js: UI, demo działa |
| 7 | 16-22 czerwca | Admin + Eval Service: można mierzyć |
| 8 | 23-29 czerwca | Eksperyment porównawczy + zbieranie metryk |
| 9-10 | 30 czerwca - 13 lipca | Pisanie pracy |
| 11+ | od 14 lipca | Bufor, polish, prezentacja, obrona |

**Realny termin gotowości:** połowa lipca 2026.
**Komfortowa obrona:** wrzesień/październik 2026.

## Gdzie Claude oszczędza najwięcej

| Obszar | Oszczędność |
|---|---|
| Boilerplate FastAPI (modele, endpointy, DI) | 70-80% |
| Setup Docker / docker-compose | 70% |
| Schema Weaviate, queries, RabbitMQ topology | 60% |
| Pisanie ADR-ów, dokumentacji, rozdziałów pracy | 50-60% |
| Komponenty React, formularze, layout | 60-70% |
| Konfiguracja TypeScript, Tailwind, eslint | 70% |

## Gdzie Claude pomaga mniej

| Obszar | Oszczędność |
|---|---|
| Debugging specyficznych problemów w środowisku | 20-30% |
| Eksperymenty i interpretacja wyników | 10-20% |
| Pisanie wkładu naukowego (oryginalna myśl) | minimalnie |
| Decyzje architektoniczne | doradztwo, nie zastępstwo |
| Komunikacja z promotorem | 0% |

## Ryzyka i bufory

**Ryzyka, które warto przewidzieć:**
- **Weaviate hybrid search** — pierwsza konfiguracja może zająć więcej
  niż się wydaje (alpha parameter, fusion type). Bufor: +3h.
- **Streaming SSE między serwisami** — od Generation przez Orchestrator
  do Frontendu, łatwo o bug. Bufor: +4h.
- **RAGAS na własnym datasecie** — wymaga ground truth answers,
  ich przygotowanie zajmuje czas. Bufor: +6h.
- **Pisanie pracy zawsze trwa dłużej niż planujesz** — bufor +30%
  na fazę 6.

**Co robić, jeśli czas zaczyna gonić:**
1. **Wytnij Query Processor** (rewriting/HyDE) — zostań przy raw query.
   Mniej diagramów, ale działa.
2. **Streamlit zamiast Next.js** — oszczędność ~10h.
3. **Jedna strategia chunkingu zamiast trzech** — mniej eksperymentów,
   ale praca i tak ma wkład.
4. **Cohere API zamiast lokalnych modeli** — oszczędność czasu na
   konfigurację GPU/CPU, ale koszt $.
