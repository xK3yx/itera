"""
Fuzzy keyword matching for progress log validation.
Used as a secondary signal alongside ChromaDB cosine similarity.
"""
from difflib import SequenceMatcher


def fuzzy_keyword_match(log_text: str, topic_kb: dict) -> dict:
    """
    Check how many validation_keywords from the KB appear in the student's log.
    Uses direct substring match first, then SequenceMatcher fuzzy ratio for single words,
    and sliding-window comparison for multi-word keywords.

    Returns:
        match_percentage: float (0-100)
        matched_keywords: list of keywords that matched
        unmatched_keywords: list of keywords that didn't match
        total_keywords: int
        matched_count: int
    """
    log_lower = log_text.lower()
    log_words = log_lower.split()

    knowledge = topic_kb.get("knowledge", {})
    keywords = knowledge.get("validation_keywords", [])

    # Fallback: try legacy format (old KB had "keywords" field at topic level)
    if not keywords:
        keywords = topic_kb.get("keywords", [])

    matched = []
    unmatched = []

    for keyword in keywords:
        kw_lower = keyword.lower().strip()
        if not kw_lower:
            continue

        # 1. Direct substring match (fastest, most reliable)
        if kw_lower in log_lower:
            matched.append(keyword)
            continue

        kw_words = kw_lower.split()
        best_ratio = 0.0

        if len(kw_words) == 1:
            # Single-word keyword: check ratio against every word in the log
            for word in log_words:
                ratio = SequenceMatcher(None, kw_lower, word).ratio()
                if ratio > best_ratio:
                    best_ratio = ratio
        else:
            # Multi-word keyword: check sliding windows of same length
            window_size = len(kw_words)
            for i in range(max(1, len(log_words) - window_size + 1)):
                window = " ".join(log_words[i:i + window_size])
                ratio = SequenceMatcher(None, kw_lower, window).ratio()
                if ratio > best_ratio:
                    best_ratio = ratio

        if best_ratio >= 0.85:
            matched.append(keyword)
        else:
            unmatched.append(keyword)

    total = len(keywords)
    match_pct = round(len(matched) / total * 100, 1) if total > 0 else 0.0

    return {
        "match_percentage": match_pct,
        "matched_keywords": matched,
        "unmatched_keywords": unmatched,
        "total_keywords": total,
        "matched_count": len(matched),
    }
