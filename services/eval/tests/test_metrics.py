from app.services.metrics import (
    citation_precision,
    cosine_similarity,
    exact_match,
    token_f1,
)


class TestTokenF1:
    def test_perfect_match(self):
        assert token_f1("the cat sat", "the cat sat") == 1.0

    def test_no_overlap(self):
        assert token_f1("dog runs fast", "cat sits slowly") == 0.0

    def test_partial_overlap(self):
        score = token_f1("warfarin increases bleeding risk", "warfarin causes bleeding")
        assert 0.0 < score < 1.0

    def test_case_and_punctuation_insensitive(self):
        assert token_f1("Aspirin!", "aspirin") == 1.0

    def test_empty_prediction(self):
        assert token_f1("", "gold answer") == 0.0

    def test_empty_gold(self):
        assert token_f1("some answer", "") == 0.0


class TestExactMatch:
    def test_identical(self):
        assert exact_match("hello world", "hello world") == 1.0

    def test_different(self):
        assert exact_match("foo", "bar") == 0.0

    def test_normalised_match(self):
        assert exact_match("Hello, World!", "hello world") == 1.0


class TestCitationPrecision:
    def test_all_cited(self):
        assert citation_precision(5, 5) == 1.0

    def test_none_cited(self):
        assert citation_precision(0, 20) == 0.0

    def test_partial(self):
        assert citation_precision(2, 10) == 0.2

    def test_zero_top_k(self):
        assert citation_precision(3, 0) == 0.0

    def test_capped_at_one(self):
        assert citation_precision(25, 20) == 1.0


class TestCosineSimilarity:
    def test_identical_vectors(self):
        v = [1.0, 0.0, 0.0]
        assert cosine_similarity(v, v) == 1.0

    def test_orthogonal_vectors(self):
        assert cosine_similarity([1.0, 0.0], [0.0, 1.0]) == 0.0

    def test_zero_vector(self):
        assert cosine_similarity([0.0, 0.0], [1.0, 0.0]) == 0.0

    def test_similar_direction(self):
        score = cosine_similarity([1.0, 1.0], [2.0, 2.0])
        assert abs(score - 1.0) < 1e-6
