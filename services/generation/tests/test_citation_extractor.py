from app.schemas.generation_schemas import ContextChunk
from app.services.citation_extractor import extract_citations


def _chunk(chunk_id: str, content: str, filename: str | None = None, page: int | None = None):
    return ContextChunk(chunk_id=chunk_id, content=content, filename=filename, page=page)


def test_extracts_single_citation():
    chunks = [
        _chunk("c1", "Aspirin inhibits COX enzymes.", filename="drug.pdf", page=1),
        _chunk("c2", "Warfarin is an anticoagulant.", filename="drug.pdf", page=2),
    ]
    answer = "Aspirin inhibits COX [SOURCE_1]. Warfarin acts differently."
    citations = extract_citations(answer, chunks)

    assert len(citations) == 1
    assert citations[0].chunk_id == "c1"
    assert citations[0].page == 1


def test_extracts_multiple_citations():
    chunks = [_chunk(f"c{i}", f"Content {i}") for i in range(1, 4)]
    answer = "See [SOURCE_1] and [SOURCE_3] for details."
    citations = extract_citations(answer, chunks)

    assert len(citations) == 2
    ids = {c.chunk_id for c in citations}
    assert ids == {"c1", "c3"}


def test_ignores_out_of_range_source():
    chunks = [_chunk("c1", "Content")]
    answer = "Reference [SOURCE_5] is invalid."
    citations = extract_citations(answer, chunks)
    assert citations == []


def test_deduplicates_same_source():
    chunks = [_chunk("c1", "Content")]
    answer = "[SOURCE_1] confirms it, and [SOURCE_1] again."
    citations = extract_citations(answer, chunks)
    assert len(citations) == 1


def test_snippet_truncated_at_200_chars():
    long_content = "x" * 300
    chunks = [_chunk("c1", long_content)]
    answer = "See [SOURCE_1]."
    citations = extract_citations(answer, chunks)
    assert len(citations) == 1
    assert citations[0].snippet.endswith("…")
    assert len(citations[0].snippet) <= 201
