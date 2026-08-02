import re

from app.schemas.generation_schemas import Citation, ContextChunk

# Padding a model may slip inside the brackets of a citation marker: ordinary
# whitespace, markdown emphasis (`[**SOURCE_2**]`), and the zero-width family
# (`[​SOURCE_3]`) — note that `\s` does NOT match zero-width characters.
# Missing any of these dropped *every* citation of the answer, so keep the class
# permissive; the surrounding brackets and the SOURCE keyword carry the meaning.
_PAD = r"[\s*_~`​‌‍⁠﻿]*"

#: One `SOURCE_n` reference, however the model chose to punctuate it.
_ONE = rf"SOURCE{_PAD}[-_\s]?{_PAD}\d+"
#: What may sit between grouped references: `, ` `; ` ` and ` `&` `+` `/`.
_SEP = rf"{_PAD}(?:[,;&+/]|and)?{_PAD}"

# A marker is one or more references inside a single bracket. Models group them
# as `[SOURCE_3, SOURCE_5]` — and sometimes drop the keyword on the second one,
# `[SOURCE_3, 5]` — which a single-reference pattern fails to match at all,
# taking every citation in that bracket with it.
CITATION_RX = re.compile(
    rf"[\[(【]{_PAD}{_ONE}(?:{_SEP}(?:{_ONE}|\d+))*{_PAD}[\])】]",
    re.IGNORECASE,
)

_DIGITS_RX = re.compile(r"\d+")


def extract_citations(answer: str, chunks: list[ContextChunk]) -> list[Citation]:
    """Extract [SOURCE_N] references from the answer and map them to chunks."""
    cited_indices: set[int] = set()
    for match in CITATION_RX.finditer(answer):
        # One bracket may carry several references.
        for raw in _DIGITS_RX.findall(match.group()):
            idx = int(raw)
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
                n=idx,
                filename=chunk.filename,
                page=chunk.page,
                snippet=snippet,
                relevance=round(chunk.score, 4) if chunk.score else None,
            )
        )
    return citations
