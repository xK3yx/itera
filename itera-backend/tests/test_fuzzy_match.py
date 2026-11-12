from app.services.fuzzy_match import fuzzy_keyword_match


def _kb(keywords):
    return {"knowledge": {"validation_keywords": keywords}}


def test_exact_keywords_match():
    result = fuzzy_keyword_match(
        "Today I learned about list comprehensions and decorators in Python",
        _kb(["list comprehensions", "decorators"]),
    )
    assert result["matched_count"] == 2
    assert result["match_percentage"] == 100


def test_unrelated_log_does_not_match():
    result = fuzzy_keyword_match("I went for a walk", _kb(["recursion", "memoization"]))
    assert result["matched_count"] == 0


def test_legacy_keyword_format_is_supported():
    result = fuzzy_keyword_match("practiced recursion", {"keywords": ["recursion"]})
    assert result["matched_count"] == 1
