from app.schemas.generation_schemas import ContextChunk
from app.services.prompt_loader import render


def build_context_block(chunks: list[ContextChunk]) -> str:
    parts: list[str] = []
    for i, chunk in enumerate(chunks, start=1):
        label = f"[SOURCE_{i}]"
        meta = f"(file: {chunk.filename or 'unknown'}"
        if chunk.page is not None:
            meta += f", page: {chunk.page}"
        meta += ")"
        parts.append(f"{label} {meta}\n{chunk.content}")
    return "\n\n".join(parts)


def build_notes_block(notes: list[str]) -> str:
    return "\n\n".join(f"[FINDING_{i}] {n}" for i, n in enumerate(notes, start=1))


def build_messages(
    query: str,
    chunks: list[ContextChunk],
    conversation_history: list[dict],
    prompt_overrides: dict[str, str] | None = None,
    evidence_notes: list[str] | None = None,
    task_instructions: str | None = None,
) -> list[dict]:
    system = render(
        "generate_system.j2",
        override=(prompt_overrides or {}).get("generate_system"),
        specialty="drug interactions",
        safety_note=None,
        task_instructions=task_instructions,
    )
    context_block = build_context_block(chunks)
    user_message = f"Context:\n{context_block}"
    if evidence_notes:
        # [FINDING_N] labels only index the notes below; only [SOURCE_N] is a citable source,
        # so citation extraction never sees a finding marker.
        user_message += (
            "\n\nIntermediate findings (internal notes — never cite a [FINDING_N] label "
            f"in your answer):\n{build_notes_block(evidence_notes)}"
        )
    user_message += f"\n\nQuestion: {query}"

    messages: list[dict] = [{"role": "system", "content": system}]
    messages.extend(conversation_history)
    messages.append({"role": "user", "content": user_message})
    return messages
