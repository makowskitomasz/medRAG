# Plan przepisania trybów RAG + re-ewaluacja

Cel: przepisać cztery tryby tak, by realnie odpowiadały literaturze (a nie były
atrapami), i przeliczyć wyniki. Kolejność benchmarków: **najpierw DDI (100 pytań),
potem HotpotQA (1000)**.

## Kontekst i stan (przeczytaj najpierw — dla nowej sesji)

**Dlaczego przepisujemy.** Przegląd kodu w `services/orchestrator/app/pipelines/`
pokazał, że cztery tryby są mocno uproszczone względem tego, co obiecuje literatura
i opis w pracy (`thesis-latex/`):
- `iterative_multihop.py` — dekompozycja RAZ + retrieval RÓWNOLEGŁY, nie sekwencyjny
  łańcuch (praca opisuje „sequence, each call uses evidence collected so far").
- `multi_agent.py` — 3 sztywne perspektywy → hurtowa generacja ze scalonych chunków;
  brak plannera/executorów/głosowania (tabela ch6 mówi „agents vote").
- `madam_rag.py` — prawie bliźniak multi_agent: 3 perspektywy + detekcja konfliktu +
  ostrożny prompt + JEDNA generacja; brak debaty, rund, sędziego (praca opisuje debatę).
- `rare_rag.py` — router do wielu trybów (nie binarny simple/complex z ch3);
  BRAK set-wise MMR (ch3 §3.4 opisuje ją ze wzorami); grounding = jeden holistyczny
  score, próg 0.3 (ch3 mówi claim-level + τ=0.5). Abstencja empirycznie 0/100 na DDI.

Wierne literaturze i OK: vanilla, hyde, query_rewriting. Self_reflection jest
uproszczony (whole-answer, 2 iteracje) — to JUŻ oznaczone w ch4/ch6 jako
„prompt-based approximation".

**Stan danych (P0 rozwiązany — patrz sekcja na końcu).** Faithfulness w
`ddi_results.json` dla rare/self_reflection był załatany stałą, ale prawdziwe
per-pytaniowe wartości SĄ w MongoDB `eval_results` i zgadzają się z pracą. Liczby
w tabelach są rzetelne.

**Jak odpalić dev (hot reload).** Pierwszy raz: `DEV=1 ./scripts/build.sh`.
Potem: `./scripts/start.sh` — stack w Dockerze z `uvicorn --reload` + reranker
natywnie na MPS (port 8005; terminal zostaje zajęty przez reranker). Pliki
pipeline'ów, query-processor i generation są zamontowane, więc zmiany łapią się
bez rebuildu. Logi: `docker compose -f docker-compose.yml -f docker-compose.dev.yml
-f docker-compose.native-reranker.yml logs -f orchestrator`.

**Branch:** `feature/rework-rag-pipelines` (od develop). W nowej sesji:
`git checkout feature/rework-rag-pipelines` przed startem.

## Ustalone parametry

| Tryb | Kluczowy parametr |
|---|---|
| Iterative Multi-hop | max hopów: **2 dla HotpotQA, 3 dla DDI** |
| MADAM-RAG | **1 runda debaty**, 2 agentów + sędzia |
| RARE-RAG | próg abstencji **τ = 0.3 (bez zmian)** |

## Kolejność implementacji

Iterative → Multi-Agent → MADAM → **RARE na końcu** (bo router RARE woła
pozostałe sub-pipeline'y, więc musi powstać po nich).

**Status kodu:** wszystkie cztery tryby przepisane, testy jednostkowe zielone
(19 passed). Zostały: smoke-testy na żywym stacku i re-run benchmarków.

Każdy tryb: kod → lokalny smoke-test na 3–5 pytaniach → dopiero potem pełny re-run.

---

## 1. Iterative Multi-hop — sekwencyjny łańcuch

Plik: `services/orchestrator/app/pipelines/iterative_multihop.py`

Obecnie: dekompozycja raz + retrieval równoległy (asyncio.gather) + scalenie.
Zmiana na prawdziwie sekwencyjny łańcuch (Chain-of-Retrieval):

1. Dekompozycja na uporządkowane pod-pytania (istniejący endpoint `/decompose`).
2. Pętla po hopach (max 2 HotpotQA / 3 DDI):
   - retrieval dla bieżącego pod-pytania,
   - wyciągnięcie częściowej odpowiedzi / encji-pomostu z pobranych fragmentów,
   - dołożenie tej wiedzy do kontekstu następnego hopa (przeformułowanie
     kolejnego pod-pytania z użyciem tego, co już wiadomo).
3. Finalna synteza z całego zebranego kontekstu.

Endpointy: potrzebny krok „extract intermediate finding" — dodać do
query-processor lub generation (`/extract_hop` albo reużyć `/generate` z krótkim
promptem). Budżet LLM: ~1 (decompose) + N×(extract) + 1 (synteza).

---

## 2. Multi-Agent (MA-RAG) — planner → executorzy → synteza

Plik: `services/orchestrator/app/pipelines/multi_agent.py`

Obecnie: trzy sztywne perspektywy, równoległy retrieval, hurtowa generacja z
scalonych chunków. Zmiana na realny podział ról:

1. **Planner** rozbija zapytanie na pod-zadania (dynamicznie, nie 3 sztywne stringi).
2. **Executorzy** (per pod-zadanie): retrieval + wyciągnięcie skupionego ustalenia
   cząstkowego (nie surowe chunki).
3. **Syntezator/QA** składa finalną odpowiedź z ustaleń cząstkowych.

Endpointy: `/plan` (rozbicie) i `/extract` w query-processor lub generation.
Budżet LLM: 1 (plan) + k×(extract) + 1 (synteza).

---

## 3. MADAM-RAG — debata + sędzia

Plik: `services/orchestrator/app/pipelines/madam_rag.py`

Obecnie: trzy perspektywy + detekcja konfliktu + ostrożny prompt + jedna generacja.
Zmiana na realną debatę:

1. 2 agentów, każdy retrieval ze swojego kąta + kandydująca odpowiedź.
2. **1 runda debaty**: każdy agent widzi odpowiedź drugiego i rewiduje własną.
3. **Sędzia** syntetyzuje konsensus z (zrewidowanych) odpowiedzi obu agentów.

Endpointy: `/debate_turn` i `/judge` (lub reużycie `/generate` z odpowiednimi
promptami). Budżet LLM: 2 (kandydaci) + 2 (rewizje) + 1 (sędzia) ≈ 5.

---

## 4. RARE-RAG — dołożyć set-wise MMR, uporządkować grounding

Plik: `services/orchestrator/app/pipelines/rare_rag.py` (+ `base.py`)

1. **Set-wise MMR selection** (ch3 §3.4, wzory eq:setwise / eq:comp) — realna
   implementacja, ~35 linii, **bez LLM**. Wpięta po reranku, przed generacją.
   Parametry: λ = 0.5, m = 3.
2. **Router** — zostaje routing do wielu trybów (nie binarny). Zaktualizować
   opis w ch3, żeby zgadzał się z kodem.
3. **Grounding verifier** — claim-level (ekstrakcja twierdzeń + per-claim check),
   ale **próg τ = 0.3** (bez zmian względem obecnego), żeby nie wywołać masowej
   abstencji (por. analiza: τ=0.5 → ~27% abstencji, 58% na L5).

Uwaga: RARE routuje do przepisanych Iterative/Multi-Agent/MADAM, więc jego wyniki
zmienią się także pośrednio — re-run RARE **po** pozostałych.

---

## Re-run (odpala użytkownik u siebie)

Wymagania: postawiony stack (docker compose), zaseedowane projekty DDI + HotpotQA,
JWT, budżet API.

DDI (najpierw):
```
./scripts/run_ddi_benchmark.sh <PROJECT_ID> <JWT> \
  --modes iterative_multihop,multi_agent,madam_rag,rare_rag
python scripts/analyze_ddi.py --input results/ddi_results.json --project-id <PROJECT_ID>
```

HotpotQA (po akceptacji wyników DDI): analogicznie przez runner HotpotQA
z tym samym `--modes`.

## Downstream w pracy (po re-runie)

Do regeneracji / przepisania (nie da się pominąć):
- Tabele: `tab:results_full`, `tab:ddi_results`, `tab:ddi_difficulty`.
- Figury: wszystkie DDI + HotpotQA (`scripts/thesis_figures.py`).
- Narracja ch6/ch7: winner-per-level, rank bump, Pareto, „dlaczego MADAM",
  „RARE wygrywa na L5", hipotezy H1/H2.
- Opisy trybów w ch2 (rodziny) i tabela `tab:mode_descriptions` w ch6 — teraz
  będą zgodne z kodem, usunąć zastrzeżenia „simplified/approximation".

## Osobny wątek (P0) — ROZWIĄZANY

Faithfulness dla rare_rag i self_reflection na DDI był w `ddi_results.json` wpisany
jako stała (0.76 / 0.714), bo eksport zgubił wartości (None) i ktoś załatał je
średnią. Zweryfikowano w MongoDB `eval_results` (projekt "Drug Interactions"
= 6a26774166042cbcf3f8e9b5): **prawdziwe per-pytaniowe wartości ISTNIEJĄ**,
rozkład min=0/max=1. Prawdziwe średnie: rare_rag 0.765 (n=103),
self_reflection 0.717 (n=102) — pokrywają się z raportowanymi (0.760 / 0.714).
Liczby w pracy są więc rzetelne; problem był tylko w eksporcie JSON.

Realne ryzyko abstencji RARE (z prawdziwego rozkładu faithfulness):
τ=0.3 → ~10% (10/103); τ=0.5 → ~21% (22/103). Potwierdza wybór τ=0.3.

TODO przy re-eksporcie wyników: pobierać faithfulness z Mongo, nie z załatanego JSON.
