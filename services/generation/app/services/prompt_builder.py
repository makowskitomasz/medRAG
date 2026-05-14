from app.schemas.generation_schemas import ContextChunk

_SYSTEM_PROMPT = """You are a medical advisory assistant specializing in drug interactions.
Answer the user's question using ONLY the provided context passages.
Each passage is labeled with [SOURCE_N] where N is the source index.
When you use information from a passage, cite it inline as [SOURCE_N].
If the context does not contain enough information, say so clearly.
Do not invent information not present in the context.
Be concise, accurate, and clinically precise."""


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
) -> list[dict]:
    context_block = build_context_block(chunks)
    user_message = f"Context:\n{context_block}\n\nQuestion: {query}"

    messages: list[dict] = [{"role": "system", "content": _SYSTEM_PROMPT}]
    messages.extend(conversation_history)
    messages.append({"role": "user", "content": user_message})
    return messages
