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


def test_extracts_cjk_bracket_form():
    chunks = [_chunk("c1", "Content")]
    citations = extract_citations("Additive effect 【SOURCE_1】.", chunks)
    assert len(citations) == 1


def test_extracts_marker_wrapped_in_markdown_bold():
    """gpt-oss-120b emits `[**SOURCE_2**]`; this used to yield zero citations."""
    chunks = [_chunk("c1", "Content 1"), _chunk("c2", "Content 2")]
    citations = extract_citations("Bleeding risk rises [**SOURCE_2**].", chunks)
    assert [c.n for c in citations] == [2]


def test_extracts_marker_padded_with_zero_width_space():
    """`\\s` does not match U+200B, so this used to yield zero citations."""
    chunks = [_chunk(f"c{i}", f"Content {i}") for i in range(1, 6)]
    answer = "Risk is higher [​SOURCE_3] [​SOURCE_5]."
    citations = extract_citations(answer, chunks)
    assert [c.n for c in citations] == [3, 5]


def test_extracts_spaced_and_lowercase_variants():
    chunks = [_chunk(f"c{i}", f"Content {i}") for i in range(1, 4)]
    citations = extract_citations("See [source 2] and (SOURCE_3).", chunks)
    assert [c.n for c in citations] == [2, 3]


def test_extracts_grouped_sources_in_one_bracket():
    """`[SOURCE_3, SOURCE_5]` used to match nothing, losing both citations."""
    chunks = [_chunk(f"c{i}", f"Content {i}") for i in range(1, 6)]
    citations = extract_citations("Both agree [SOURCE_3, SOURCE_5].", chunks)
    assert [c.n for c in citations] == [3, 5]


def test_extracts_grouped_sources_with_keyword_dropped():
    chunks = [_chunk(f"c{i}", f"Content {i}") for i in range(1, 6)]
    citations = extract_citations("See [SOURCE_1, 4] and [SOURCE_2 and SOURCE_5].", chunks)
    assert [c.n for c in citations] == [1, 2, 4, 5]


def test_grouped_sources_respect_chunk_range():
    chunks = [_chunk("c1", "Content 1")]
    citations = extract_citations("Claim [SOURCE_1, SOURCE_9].", chunks)
    assert [c.n for c in citations] == [1]


def test_snippet_truncated_at_200_chars():
    long_content = "x" * 300
    chunks = [_chunk("c1", long_content)]
    answer = "See [SOURCE_1]."
    citations = extract_citations(answer, chunks)
    assert len(citations) == 1
    assert citations[0].snippet.endswith("…")
    assert len(citations[0].snippet) <= 201
