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


def build_messages(
    query: str,
    chunks: list[ContextChunk],
    conversation_history: list[dict],
    prompt_overrides: dict[str, str] | None = None,
) -> list[dict]:
    system = render(
        "generate_system.j2",
        override=(prompt_overrides or {}).get("generate_system"),
        specialty="drug interactions",
        safety_note=None,
    )
    context_block = build_context_block(chunks)
    user_message = f"Context:\n{context_block}\n\nQuestion: {query}"

    messages: list[dict] = [{"role": "system", "content": system}]
    messages.extend(conversation_history)
    messages.append({"role": "user", "content": user_message})
    return messages
