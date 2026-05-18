import re

from app.schemas.generation_schemas import Citation, ContextChunk


def extract_citations(answer: str, chunks: list[ContextChunk]) -> list[Citation]:
    """Extract [SOURCE_N] references from the answer and map them to chunks."""
    cited_indices: set[int] = set()
    for match in re.finditer(r"[\[【]\s*SOURCE_(\d+)\s*[\]】]", answer):
        idx = int(match.group(1))
        if 1 <= idx <= len(chunks):
            cited_indices.add(idx)

    citations: list[Citation] = []
    for idx in sorted(cited_indices):
        chunk = chunks[idx - 1]
        snippet = chunk.content[:200].rstrip()
        if len(chunk.content) > 200:
            snippet += "…"
        citations.append(
            Citation(
                chunk_id=chunk.chunk_id,
                filename=chunk.filename,
                page=chunk.page,
                snippet=snippet,
            )
        )
    return citations
