# Thesis Writing Plan — medRAG

**Title:** Retrieval-Augmented Generation for Improving Large Language Models:
Technology Analysis and Design of an Experimental Advisory System

**Author:** inż. Tomasz Makowski
**Supervisor:** prof. dr hab. inż. Antoni Ligęza
**Institution:** AGH University of Science and Technology, Kraków
**Deadline:** end of June 2026 (writing July–August 2026)
**Target length:** 70–80 pages

---

## Structure overview

| # | Chapter | Target pages | Status |
|---|---------|-------------|--------|
| 1 | Introduction | 6–8 | TODO |
| 2 | Background & Literature Review | 18–22 | TODO |
| 3 | RARE-RAG: Proposed Architecture | 10–12 | TODO |
| 4 | System Design | 14–16 | TODO |
| 5 | Implementation | 8–10 | TODO |
| 6 | Experimental Evaluation | 14–16 | TODO |
| 7 | Conclusions & Future Work | 5–6 | TODO |
| — | Abstract (EN + PL), Acknowledgements | 2 | TODO |

**Total estimate: 77–90 pages** (trim if needed; chapters 3 and 5 are most flexible)

---

## Chapter 1 — Introduction (~7 pages)

### Goal
Motivate the problem, state the research questions, summarise the contribution.

### Key sections
1.1 **Motivation** — Polypharmacy problem: patients with multiple conditions, multiple prescribing doctors, no unified view of drug interactions. Gap in clinical decision support.

1.2 **Problem Statement** — Three questions to answer:
  - Which RAG architecture achieves the best trade-off between answer quality and latency?
  - Does a routing-aware, evidence-selection approach (RARE-RAG) outperform single-path architectures on faithfulness?
  - Can a RAG-based system serve as a reliable technology demonstrator for drug interaction advisory?

1.3 **Research Scope** — What is in scope (technology analysis, benchmark, demonstrator) and out of scope (clinical validation, production deployment, regulatory compliance).

1.4 **Thesis Organisation** — One paragraph per chapter.

1.5 **Contributions** — Bullet list:
  - Comparative study of 8 RAG architecture families on HotpotQA (n=1000 per mode, 9 modes)
  - Design and implementation of RARE-RAG (Risk-Aware Routed Evidence-graph RAG)
  - Open-source microservice system: 14 services, configurable RAG strategy per project
  - Empirical finding: RARE-RAG achieves highest faithfulness (0.976) among evaluated modes

### Tone notes
Personal but academic. Start with a concrete scenario (patient taking 7 drugs). Avoid generic "AI is transforming everything" opener.

---

## Chapter 2 — Background & Literature Review (~20 pages)

### Goal
Survey the state-of-the-art; build vocabulary for chapters 3–6; position thesis in the literature.

### Key sections

2.1 **From Language Models to RAG** (2 pages)
  - LLMs: strengths (fluency, reasoning) and weaknesses (hallucination, knowledge staleness, opacity)
  - Parametric vs. non-parametric knowledge
  - Original RAG paper: Lewis et al. (2020) — retrieve-then-generate baseline

2.2 **Retrieval Foundations** (3 pages)
  - Sparse retrieval: BM25 / SPLADE v2
  - Dense retrieval: DPR, Contriever
  - Late interaction: ColBERT / ColBERTv2
  - Hybrid search: linear interpolation of scores (alpha parameter)
  - Cross-encoder reranking: BGE-reranker-v2-m3

2.3 **RAG Architecture Families** (10 pages — core of the chapter)
  Table at the start: 8 families × columns (year, key idea, retrieval, generation, eval benchmark, weakness)

  | Family | Key paper | Core idea |
  |--------|-----------|-----------|
  | Vanilla RAG | Lewis et al. 2020 | retrieve → generate |
  | HyDE / Query Rewriting | Gao et al. 2022 | embed hypothetical answer |
  | Self-RAG | Asai et al. 2023 | reflection tokens for self-critique |
  | CRAG / Corrective RAG | Yan et al. 2024 | correctness evaluation, web fallback |
  | Graph / Hierarchical RAG | GraphRAG 2024, RAPTOR 2024 | knowledge graph or tree summaries |
  | Iterative Multi-hop RAG | Chain-of-Retrieval 2025 | multi-step evidence chaining |
  | Agentic / Multi-Agent RAG | Agentic RAG Survey 2025 | planner + executor agents |
  | RARE-RAG (this work) | — | routing + hybrid + set-wise selection + grounding check |

  For each family: 1–2 paragraphs covering mechanism, strengths, benchmarks, limitations.

2.4 **Evaluation of RAG Systems** (3 pages)
  - End-to-end metrics: Token F1, Exact Match, ROUGE-L
  - RAGAS metrics: Faithfulness, Answer Relevance, Context Recall, Context Precision
  - Benchmarks: HotpotQA, BEIR, CRAG, RAGBench
  - Latency and cost as first-class metrics

2.5 **Related Work in Medical / Clinical NLP** (2 pages)
  - Clinical decision support systems
  - Drug interaction detection: rule-based vs. ML vs. LLM approaches
  - Trustability, explainability, and hallucination in high-stakes domains

### Key references (BibTeX keys to use)
- `lewis2020rag` — original RAG paper
- `gao2022hyde` — HyDE
- `asai2023selfrag` — Self-RAG
- `yan2024crag` — Corrective RAG
- `edge2024graphrag` — GraphRAG (Microsoft)
- `sarthi2024raptor` — RAPTOR hierarchical
- `wang2025chain` — Chain-of-Retrieval
- `singh2025agenticrag` — Agentic RAG survey
- `du2026arag` — A-RAG hierarchical retrieval interfaces
- `chen2026jade` — JADE strategic-operational gap
- `es2023ragas` — RAGAS framework (Shahul Es et al.)
- `yang2018hotpotqa` — HotpotQA dataset

### Diagrams for this chapter
- **Figure 2.1** — Timeline: RAG evolution 2020–2026 (TikZ timeline)
- **Figure 2.2** — Taxonomy tree of RAG architectures (TikZ tree)
- **Figure 2.3** — Vanilla RAG pipeline (TikZ block diagram)
- **Figure 2.4** — Self-RAG with reflection tokens (TikZ flow)
- **Figure 2.5** — RAGAS metric decomposition (TikZ)

---

## Chapter 3 — RARE-RAG: Proposed Architecture (~11 pages)

### Goal
Present the novel contribution. Describe the design rationale, architecture, and expected properties.
This is the most original chapter — write with precision and defend every design decision.

### Key sections

3.1 **Motivation for RARE-RAG** (1 page)
  - Gap in the literature: existing architectures fix retrieval strategy regardless of query complexity and risk
  - RARE-RAG hypothesis: routing by complexity + evidence-set selection + grounding check = better faithfulness

3.2 **Architecture Overview** (2 pages)
  - Component diagram (TikZ)
  - Four pillars:
    1. **Risk & Complexity Router** — classify query as simple / complex / high-stakes
    2. **Hybrid Evidence Retrieval** — BM25 + vector search, late interaction reranking
    3. **Set-wise Evidence Selection** — rank evidence as a set (SETR-inspired), not individually
    4. **Grounding Verifier with Abstention** — check if answer is supported; abstain if not

3.3 **Query Routing** (2 pages)
  - Input: query text
  - Classifier: lightweight LLM call with few-shot examples
  - Routes: `fast` (single-hop, no reranking), `standard` (hybrid + cross-encoder), `deep` (multi-hop + graph expansion)
  - Design trade-off: classifier latency vs. downstream quality gain

3.4 **Evidence Selection** (2 pages)
  - Why list-wise reranking is not enough: individual scores miss inter-document complementarity
  - Set-wise scoring: SETR approach — score subsets, not individual chunks
  - Implementation: approximate greedy selection over top-20 candidates

3.5 **Grounding Verifier** (2 pages)
  - Claim extraction from generated answer
  - Per-claim grounding check against retrieved context
  - Abstention logic: if grounding score < threshold → "I cannot reliably answer this question based on available evidence"

3.6 **Expected Properties and Hypothesis** (1 page)
  - Hypothesis H1: RARE-RAG achieves higher faithfulness than all single-path architectures
  - Hypothesis H2: RARE-RAG achieves comparable or higher Token F1 than vanilla despite higher latency
  - Hypothesis H3: routing reduces average latency compared to always-deep processing

### Diagrams for this chapter
- **Figure 3.1** — RARE-RAG component architecture (TikZ, detailed)
- **Figure 3.2** — Routing decision tree (TikZ)
- **Figure 3.3** — Set-wise evidence selection algorithm (TikZ or pseudocode)
- **Figure 3.4** — Grounding verifier flow (TikZ)

---

## Chapter 4 — System Design (~15 pages)

### Goal
Document the full microservice architecture, data models, and API contracts. This chapter doubles as a design appendix — future maintainers should be able to rebuild from it.

### Key sections

4.1 **Design Principles** (1 page)
  - Strategy pattern per project (chunking, embedding, RAG mode configurable at runtime)
  - Event-driven ingestion vs. synchronous query pipeline
  - Non-root Docker containers, structured JSON logging, distributed trace IDs

4.2 **System Context (C4 Level 1)** (1 page)
  - Figure: user, admin, system boundary, external LLM API, external embedding API
  - (TikZ or refined PlantUML → include as PNG)

4.3 **Container Architecture (C4 Level 2)** (3 pages)
  - All 14 services table (port, responsibility, key dependencies)
  - Figure: container diagram showing ingestion pipeline and query pipeline separately
  - Key design decision: why microservices vs. monolith (ADR reference)

4.4 **Query Pipeline Design** (3 pages)
  - Synchronous REST + SSE streaming
  - Sequence diagram: gateway → auth → orchestrator → query-processor → retrieval → reranker → generation → SSE to client
  - RAG mode switching in orchestrator: how strategy pattern works
  - Conversation persistence in MongoDB

4.5 **Ingestion Pipeline Design** (2 pages)
  - Async event-driven via RabbitMQ
  - Sequence: upload → parse → chunk → embed → index → status update
  - Content-hash deduplication
  - Chunking strategy comparison (fixed/recursive/semantic)

4.6 **Data Model** (3 pages)
  - MongoDB collections: users, projects, documents, chunks, conversations, eval_results
  - Weaviate schema: MedRAGChunk (text, embedding, project_id, doc_id, chunk_index, strategy)
  - Key decisions: why MongoDB for metadata + Weaviate for vectors (not single DB)

4.7 **Security Design** (1 page)
  - JWT flow, role-based access (admin vs. user)
  - Project-scoped retrieval (cannot query another project's documents)

### Diagrams for this chapter
- **Figure 4.1** — C4 Level 1: System Context
- **Figure 4.2** — C4 Level 2: Container Diagram (the big one — 14 services)
- **Figure 4.3** — Query pipeline sequence diagram
- **Figure 4.4** — Ingestion pipeline sequence diagram
- **Figure 4.5** — MongoDB data model (UML class-style, TikZ)
- **Figure 4.6** — RAG strategy switching class diagram

---

## Chapter 5 — Implementation (~9 pages)

### Goal
Describe non-trivial implementation decisions. Not a code tour — pick 4-5 interesting technical challenges.

### Key sections

5.1 **Technology Stack** (1 page)
  - Python 3.12, FastAPI, uv, pydantic-settings
  - Next.js 15, TypeScript, Tailwind, shadcn/ui
  - Docker multi-stage, non-root, docker-compose

5.2 **Embedding Provider Abstraction** (1.5 pages)
  - Strategy interface: `embed_texts(texts) → List[List[float]]`
  - Three providers: local BGE-M3 (sentence-transformers), Cohere Embed v3, OpenAI text-embedding-3
  - Tradeoff: local GPU vs. API cost vs. quality

5.3 **Hybrid Search and Alpha Tuning** (2 pages)
  - Weaviate hybrid query: `alpha` parameter balances BM25 and vector score
  - RRF fusion formula
  - Results: alpha=0.5 as default (empirical tuning on dev split)
  - Why hybrid beats pure vector on HotpotQA (entity-heavy questions)

5.4 **Streaming (SSE) Architecture** (1.5 pages)
  - FastAPI StreamingResponse + generator pattern
  - Token-by-token forwarding from Anthropic SDK `.stream()`
  - Citation injection after stream completion
  - Frontend EventSource handling

5.5 **Evaluation Service and RAGAS Integration** (2 pages)
  - Async consumer of `query.completed` RabbitMQ events
  - RAGAS pipeline: faithfulness (NLI), answer relevance (cosine sim), context recall (coverage)
  - LLM-as-judge calls for faithfulness — cost implications
  - Storing per-question metrics in MongoDB

5.6 **Docker and CI/CD** (1 page)
  - Multi-stage build, non-root user, health checks
  - GitHub Actions: lint (ruff) + typecheck (mypy) + pytest + docker build smoke test

### Diagrams for this chapter
- **Figure 5.1** — Embedding provider strategy class diagram (TikZ UML)
- **Figure 5.2** — Hybrid search alpha sweep chart (seaborn, if data available)
- **Figure 5.3** — SSE streaming sequence (TikZ)
- **Figure 5.4** — RAGAS evaluation pipeline flow (TikZ)

---

## Chapter 6 — Experimental Evaluation (~15 pages)

### Goal
Present benchmark results, interpret findings, validate or reject hypotheses from Chapter 3.

### Benchmark data available
- Dataset: HotpotQA (1000 questions per RAG mode, 9 modes = 9000 total evaluations)
- Metrics: Token F1, Exact Match, ROUGE-L, Faithfulness, Answer Relevance, Context Recall
- Latency: mean, median, p95 (ms)
- Est. cost: ~$60 total API spend

### Final results table (summary_table.csv, n=1000 each)

| Mode | Token F1 | EM | Faithfulness | Ctx Recall | Latency (ms) |
|------|----------|-----|-------------|------------|--------------|
| vanilla | 0.537 | 0.316 | 0.939 | 0.971 | 9,144 |
| hyde | 0.541 | 0.315 | 0.971 | 0.975 | 22,715 |
| query_rewriting | 0.537 | 0.312 | 0.964 | 0.958 | 22,722 |
| self_reflection | **0.545** | **0.329** | 0.974 | 0.972 | 19,952 |
| multi_agent | 0.525 | 0.309 | 0.967 | 0.970 | 10,170 |
| corrective_rag | 0.539 | 0.323 | 0.973 | 0.968 | 11,818 |
| iterative_multihop | 0.533 | 0.314 | 0.969 | 0.953 | 26,009 |
| madam_rag | 0.487 | 0.282 | 0.950 | 0.926 | 28,953 |
| **rare_rag** | 0.543 | 0.320 | **0.976** | 0.969 | 30,845 |

### Key sections

6.1 **Experimental Setup** (2 pages)
  - Dataset description: HotpotQA — multi-hop reasoning, 2-doc evidence, diverse topics
  - Why HotpotQA: multi-hop nature stresses retrieval quality; widely used RAG benchmark
  - Infrastructure: API calls to claude-sonnet-4-6, local BGE-M3 embeddings, Weaviate
  - Metrics definition: Token F1 (token-level overlap), EM (exact match), RAGAS metrics
  - Evaluation cost and time: $60, ~45,000 seconds total

6.2 **Results: Answer Quality** (3 pages)
  - Token F1 and EM comparison (bar chart — seaborn)
  - Self-reflection: best EM (0.329) — explicit reasoning tokens help factoid accuracy
  - RARE-RAG: competitive F1 (0.543) despite most complex pipeline
  - MADAM-RAG: weakest performance — debate overhead not suited to single-answer factoid QA
  - Statistical note: all modes evaluated on same 1000 questions → paired comparison valid

6.3 **Results: Faithfulness and Grounding** (3 pages)
  - Faithfulness comparison (bar chart + radar chart)
  - **Key finding: RARE-RAG achieves highest faithfulness (0.976)** — grounding verifier works
  - HyDE also high (0.971) — hypothetical document creates better-aligned context
  - Vanilla baseline surprisingly high (0.939) — well-prompted generation is mostly grounded
  - Answer relevance: all modes 0.51–0.53 except vanilla slightly higher absolute answer quality
  - Hypothesis H1 confirmed: RARE-RAG > all single-path architectures on faithfulness

6.4 **Results: Latency and Cost Trade-off** (3 pages)
  - Latency-vs-quality scatter plot (seaborn)
  - Pareto frontier analysis: vanilla and multi_agent dominate (good quality, low latency)
  - corrective_rag: best cost-quality ratio among enhanced modes (11.8s, F1=0.539)
  - RARE-RAG: highest latency (30.8s) — routing + set-wise selection + grounding adds cost
  - Hypothesis H3 partially confirmed: routing reduces max latency compared to always-deep, but absolute latency still high due to grounding verifier
  - Table: estimated cost per 1000 queries per mode

6.5 **Discussion** (2 pages)
  - Why faithfulness ≠ accuracy: a system can be faithful to wrong context
  - MADAM-RAG failure mode: debate architecture good for disambiguation, bad for factoid
  - RARE-RAG vs. self_reflection: different optimisation targets (faithfulness vs. EM)
  - Limitations: HotpotQA is English, Wikipedia domain — results may not generalise to medical domain
  - Why DDI benchmark is not yet evaluated (out of scope for current phase)

6.6 **Drug Interaction Advisory Use Case** (1 page)
  - System demonstration with synthetic queries
  - Qualitative examples: patient on warfarin + aspirin → detected interaction
  - Note on trustability: RARE-RAG's abstention mechanism fires correctly on unanswerable queries

### Figures for this chapter
- **Figure 6.1** — Bar chart: Token F1 + EM per mode (seaborn, horizontal bars, color-coded by architecture family)
- **Figure 6.2** — Bar chart: Faithfulness per mode with error bars
- **Figure 6.3** — Radar chart: 5 metrics per mode (all 9 modes)
- **Figure 6.4** — Scatter plot: Latency vs. Token F1 (bubble size = faithfulness)
- **Figure 6.5** — Heatmap: all metrics × all modes
- **Figure 6.6** — Latency CDF or box plot per mode

---

## Chapter 7 — Conclusions & Future Work (~5 pages)

### Key sections

7.1 **Summary of Findings** (1.5 pages)
  - Research questions revisited: answered yes/partially/no with evidence
  - Best architecture per use case: latency-critical → vanilla/multi_agent; accuracy-critical → self_reflection; safety-critical → rare_rag
  - RARE-RAG: highest faithfulness, acceptable accuracy, high latency — fits high-stakes advisory

7.2 **Contributions** (0.5 page)
  - Empirical comparison: 9 RAG modes × 1000 questions, open dataset, reproducible
  - RARE-RAG design: four-component architecture with grounding verifier
  - Open-source system: 14 microservices, configurable strategies

7.3 **Limitations** (1 page)
  - HotpotQA only (English, Wikipedia) — no medical domain validation
  - LLM-as-judge for RAGAS metrics: circular dependency on same model family
  - RARE-RAG implementation: set-wise selection is approximate greedy, not optimal
  - Small sample for some modes in early runs (see Appendix)

7.4 **Future Work** (2 pages)
  - DDI benchmark evaluation (DrugBank/OpenFDA corpus — scripts already in repo)
  - Medical domain fine-tuning: BGE-M3 on drug interaction literature
  - Graph-enhanced RARE-RAG: replace set-wise selection with knowledge graph expansion
  - Production concerns: latency optimisation (batching, caching), compliance, audit logs
  - Human evaluation: cardiologist / pharmacist in-the-loop assessment

---

## Diagrams to create (master list)

### TikZ (LaTeX-native, vector, beautiful)
| ID | Chapter | Description | Status |
|----|---------|-------------|--------|
| Fig 2.1 | 2 | RAG timeline 2020–2026 | TODO |
| Fig 2.2 | 2 | RAG architecture taxonomy tree | TODO |
| Fig 2.3 | 2 | Vanilla RAG pipeline | TODO |
| Fig 2.4 | 2 | Self-RAG reflection tokens | TODO |
| Fig 3.1 | 3 | RARE-RAG component architecture | TODO |
| Fig 3.2 | 3 | Query routing decision tree | TODO |
| Fig 3.3 | 3 | Set-wise evidence selection | TODO |
| Fig 3.4 | 3 | Grounding verifier flow | TODO |
| Fig 4.1 | 4 | C4 Level 1: System Context | TODO |
| Fig 4.2 | 4 | C4 Level 2: Container Diagram | TODO |
| Fig 4.3 | 4 | Query pipeline sequence | TODO |
| Fig 4.4 | 4 | Ingestion pipeline sequence | TODO |
| Fig 4.5 | 4 | MongoDB data model | TODO |
| Fig 5.1 | 5 | Embedding strategy class diagram | TODO |
| Fig 5.3 | 5 | SSE streaming sequence | TODO |

### Seaborn/matplotlib (generate from CSV, save as PDF)
| ID | Chapter | Description | Status |
|----|---------|-------------|--------|
| Fig 6.1 | 6 | Token F1 + EM bar chart | TODO |
| Fig 6.2 | 6 | Faithfulness bar chart | TODO |
| Fig 6.3 | 6 | Radar chart (5 metrics, 9 modes) | TODO |
| Fig 6.4 | 6 | Latency vs. F1 scatter (bubble) | TODO |
| Fig 6.5 | 6 | Heatmap: metrics × modes | TODO |

---

## Key references (priority order for BibTeX)

1. Lewis et al. 2020 — RAG original (NeurIPS)
2. Es et al. 2023 — RAGAS (arXiv 2309.15217)
3. Asai et al. 2023 — Self-RAG (ICLR 2024)
4. Yan et al. 2024 — CRAG / Corrective RAG
5. Gao et al. 2022 — HyDE (arXiv 2212.10496)
6. Yang et al. 2018 — HotpotQA (EMNLP)
7. Edge et al. 2024 — GraphRAG (Microsoft)
8. Sarthi et al. 2024 — RAPTOR (arXiv)
9. Singh et al. 2025 — Agentic RAG Survey (arXiv 2501.09136)
10. Wang et al. 2025 — Chain-of-Retrieval (arXiv)
11. Du et al. 2026 — A-RAG (arXiv 2602.03442)
12. Chen et al. 2026 — JADE (arXiv 2601.21916)
13. Jeong et al. 2024 — Adaptive-RAG
14. Karpukhin et al. 2020 — DPR (EMNLP)
15. Khattab & Zaharia 2020 — ColBERT (SIGIR)

---

## Notes on writing style

- **No AI voice**: Avoid "In this paper, we present a comprehensive...", "Furthermore, it is worth noting that..."
- Preferred: direct statements. "RARE-RAG achieves higher faithfulness than all baselines (Table 6.1)."
- Use passive only for methods: "Queries were processed by...", "The system was evaluated on..."
- Every claim needs a citation or a pointer to a figure/table with data
- Figures: caption below, label `fig:figname`, always referenced in text before appearing
- Tables: caption above, use `booktabs` (\toprule, \midrule, \bottomrule)
- Numbers: always rounded to 3 decimal places in text, 4 in tables
