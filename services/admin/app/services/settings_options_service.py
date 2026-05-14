from pathlib import Path

from app.schemas.project_schemas import (
    EnumOption,
    FieldConstraint,
    PromptSlot,
    SettingsOptions,
)

_GENERATION_PROMPTS = Path("/app/generation_prompts")
_QP_PROMPTS = Path("/app/query_processor_prompts")

_RAG_MODES: list[EnumOption] = [
    EnumOption(value="vanilla", label="Classic RAG", description="Baseline: retrieve → generate."),
    EnumOption(
        value="hyde",
        label="HyDE",
        description="Hypothetical Document Embeddings: generate a passage, embed it, retrieve.",
    ),
    EnumOption(
        value="query_rewriting",
        label="Query Rewriting",
        description="LLM rewrites the query for better retrieval coverage.",
    ),
    EnumOption(
        value="self_reflection",
        label="Self-Reflection (Self-RAG)",
        description="Scores the answer, retries retrieval if grounding is insufficient.",
    ),
    EnumOption(
        value="multi_agent",
        label="Multi-Agent",
        description="Three parallel agents with different retrieval perspectives, deduplicated.",
    ),
    EnumOption(
        value="corrective_rag",
        label="Corrective RAG",
        description="Checks chunk relevance; falls back to BM25-heavy search when low.",
    ),
    EnumOption(
        value="iterative_multihop",
        label="Iterative Multi-Hop",
        description="Decomposes complex questions into sub-questions, retrieves for each.",
    ),
    EnumOption(
        value="madam_rag",
        label="MADAM-RAG",
        description="Detects conflicting evidence, generates cautious multi-perspective answer.",
    ),
    EnumOption(
        value="rare_rag",
        label="RARE-RAG (auto-router)",
        description="LLM triages the query, delegates to best pipeline; abstains when uncertain.",
    ),
]

_CHUNKING_STRATEGIES: list[EnumOption] = [
    EnumOption(
        value="fixed_512",
        label="Fixed 512",
        description="Split into fixed 512-token windows with overlap.",
    ),
    EnumOption(
        value="recursive",
        label="Recursive (default)",
        description="RecursiveCharacterTextSplitter — respects paragraph/sentence boundaries.",
    ),
    EnumOption(
        value="semantic",
        label="Semantic",
        description="Splits at semantic boundaries using embedding similarity.",
    ),
]

_EMBEDDING_PROVIDERS: list[EnumOption] = [
    EnumOption(
        value="local_bge",
        label="BGE-m3 (local)",
        description="Local sentence-transformers model, no API cost.",
    ),
    EnumOption(
        value="cohere",
        label="Cohere Embed v3",
        description="Cohere API — requires COHERE_API_KEY.",
    ),
    EnumOption(
        value="openai",
        label="OpenAI text-embedding-3",
        description="OpenAI API — requires OPENAI_API_KEY.",
    ),
]

_PROMPT_SLOT_DEFS = [
    {
        "slug": "generate_system",
        "label": "Generation — system prompt",
        "description": "Main answer generation. Variables: {{ specialty }}, {{ safety_note }}.",
        "path": _GENERATION_PROMPTS / "generate_system.j2",
    },
    {
        "slug": "evaluate_system",
        "label": "Evaluation — system prompt",
        "description": "Answer grounding evaluation. Variables: {{ strict_mode }}.",
        "path": _GENERATION_PROMPTS / "evaluate_system.j2",
    },
    {
        "slug": "detect_conflict_system",
        "label": "Conflict detection — system prompt",
        "description": "Evidence conflict detection. Variables: {{ topic_hint }}.",
        "path": _GENERATION_PROMPTS / "detect_conflict_system.j2",
    },
    {
        "slug": "rewrite_system",
        "label": "Query rewriting — system prompt",
        "description": "Query rewriting. Variables: {{ domain }}.",
        "path": _QP_PROMPTS / "rewrite_system.j2",
    },
    {
        "slug": "hyde_system",
        "label": "HyDE — system prompt",
        "description": "Hypothetical document generation. Variables: {{ domain }}.",
        "path": _QP_PROMPTS / "hyde_system.j2",
    },
    {
        "slug": "decompose_system",
        "label": "Decomposition — system prompt",
        "description": "Query decomposition. Variables: {{ max_sub_questions }}, {{ domain }}.",
        "path": _QP_PROMPTS / "decompose_system.j2",
    },
    {
        "slug": "triage_system",
        "label": "Triage — system prompt",
        "description": "RARE-RAG routing triage. Variables: {{ available_modes }}.",
        "path": _QP_PROMPTS / "triage_system.j2",
    },
]


def _read_template(path: Path) -> str:
    try:
        return path.read_text()
    except FileNotFoundError:
        return ""


def get_settings_options() -> SettingsOptions:
    return SettingsOptions(
        rag_modes=_RAG_MODES,
        chunking_strategies=_CHUNKING_STRATEGIES,
        embedding_providers=_EMBEDDING_PROVIDERS,
        hybrid_alpha=FieldConstraint(
            type="float",
            min=0.0,
            max=1.0,
            step=0.05,
            default=0.5,
            description="Weaviate hybrid search alpha. 0 = pure BM25, 1 = pure vector.",
        ),
        top_k=FieldConstraint(
            type="int",
            min=1,
            max=100,
            step=1,
            default=20,
            description="Number of chunks retrieved before reranking.",
        ),
        rerank_top_n=FieldConstraint(
            type="int",
            min=1,
            max=20,
            step=1,
            default=5,
            description="Number of chunks passed to generation after reranking.",
        ),
        prompt_slots=[
            PromptSlot(
                slug=s["slug"],
                label=s["label"],
                description=s["description"],
                default_template=_read_template(s["path"]),
            )
            for s in _PROMPT_SLOT_DEFS
        ],
    )
