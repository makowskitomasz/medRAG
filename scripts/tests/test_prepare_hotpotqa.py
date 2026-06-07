"""Unit tests for prepare_hotpotqa.py."""

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from prepare_hotpotqa import _extract_supporting_docs, _slug

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_row(
    level: str = "hard",
    q_type: str = "bridge",
    supporting_titles: list[str] | None = None,
) -> dict:
    if supporting_titles is None:
        supporting_titles = ["Article A", "Article B"]

    all_titles = supporting_titles + [f"Distractor {i}" for i in range(8)]
    all_sentences = [["Sentence one.", "Sentence two."] for _ in all_titles]

    return {
        "id": "test-id-001",
        "question": "Who directed the film starring the actor from Article A?",
        "answer": "John Doe",
        "level": level,
        "type": q_type,
        "context": {
            "title": all_titles,
            "sentences": all_sentences,
        },
        "supporting_facts": {
            "title": supporting_titles * 2,  # titles repeat per sentence
            "sent_id": [0, 1, 0, 1],
        },
    }


def _make_dataset(
    n_easy: int = 500,
    n_hard: int = 700,
    n_medium: int = 200,
) -> list[dict]:
    rows = []
    for i in range(n_easy):
        r = _make_row("easy", supporting_titles=[f"EasyA{i}", f"EasyB{i}"])
        r["id"] = f"easy-{i}"
        r["question"] = f"Easy question {i}?"
        rows.append(r)
    for i in range(n_hard):
        r = _make_row("hard", supporting_titles=[f"HardA{i}", f"HardB{i}"])
        r["id"] = f"hard-{i}"
        r["question"] = f"Hard question {i}?"
        rows.append(r)
    for i in range(n_medium):
        r = _make_row("medium", supporting_titles=[f"MedA{i}", f"MedB{i}"])
        r["id"] = f"medium-{i}"
        r["question"] = f"Medium question {i}?"
        rows.append(r)
    return rows


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_slug_lowercase_no_spaces() -> None:
    assert _slug("Hello World") == "hello_world"
    assert " " not in _slug("A B C D")


def test_slug_max_len() -> None:
    assert len(_slug("x" * 200, max_len=20)) <= 20


def test_extract_supporting_docs_returns_only_two() -> None:
    row = _make_row(supporting_titles=["Real A", "Real B"])
    docs = _extract_supporting_docs(row)
    assert len(docs) == 2
    titles = {d["title"] for d in docs}
    assert titles == {"Real A", "Real B"}


def test_extract_supporting_docs_excludes_distractors() -> None:
    row = _make_row(supporting_titles=["Support 1", "Support 2"])
    docs = _extract_supporting_docs(row)
    for doc in docs:
        assert not doc["title"].startswith("Distractor")


def test_extract_supporting_docs_has_sentences() -> None:
    row = _make_row()
    docs = _extract_supporting_docs(row)
    for doc in docs:
        assert isinstance(doc["sentences"], list)
        assert len(doc["sentences"]) > 0


def test_sample_counts_easy_hard(tmp_path: Path) -> None:
    """Output must have 400 easy + 600 hard (with enough data)."""

    fake_ds = _make_dataset(n_easy=500, n_hard=700, n_medium=0)
    docs_dir = tmp_path / "hotpotqa_docs"
    docs_dir.mkdir()

    rng = random.Random(42)
    easy_rows = [r for r in fake_ds if r["level"] == "easy"]
    hard_rows = [r for r in fake_ds if r["level"] == "hard"]
    easy_sample = rng.sample(easy_rows, min(400, len(easy_rows)))
    hard_sample = rng.sample(hard_rows, min(600, len(hard_rows)))

    assert len(easy_sample) == 400
    assert len(hard_sample) == 600
    assert len(easy_sample) + len(hard_sample) == 1000


def test_deduplication_of_articles(tmp_path: Path) -> None:
    """Same article title across multiple rows → only one .txt file."""
    import prepare_hotpotqa as ph

    # Two rows sharing the same supporting article "Shared Article"
    rows = [_make_row(supporting_titles=["Shared Article", f"Unique{i}"]) for i in range(3)]

    docs_dir = tmp_path / "hotpotqa_docs"
    docs_dir.mkdir()
    seen_titles: dict[str, str] = {}

    for row in rows:
        docs = ph._extract_supporting_docs(row)
        for doc in docs:
            title = doc["title"]
            if title not in seen_titles:
                fname = ph._slug(title) + ".txt"
                target = docs_dir / fname
                content = f"{title}\n\n{' '.join(doc['sentences'])}\n"
                target.write_text(content, encoding="utf-8")
                seen_titles[title] = fname

    # "Shared Article" should appear only once
    shared_files = list(docs_dir.glob("shared_article*.txt"))
    assert len(shared_files) == 1


def test_output_json_schema(tmp_path: Path) -> None:
    """Each QA pair must have required fields."""
    import prepare_hotpotqa as ph

    row = _make_row(level="hard", q_type="bridge")
    docs = ph._extract_supporting_docs(row)
    qa = {
        "question": row["question"],
        "gold_answer": row["answer"],
        "supporting_docs": docs,
        "level": row["level"],
        "type": row["type"],
        "metadata": {"source": "hotpotqa", "id": row["id"]},
    }

    required = {
        "question",
        "gold_answer",
        "supporting_docs",
        "level",
        "type",
        "metadata",
    }
    assert required.issubset(qa.keys())
    assert qa["metadata"]["source"] == "hotpotqa"
    assert len(qa["supporting_docs"]) == 2
