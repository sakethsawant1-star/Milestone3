"""
preprocessor.py — Aggressive Pre-LLM Data Reduction for Phase 2

Filters the Phase 1 sanitized output (~1,663 reviews, ~38K tokens) down to
~400 actionable reviews (~15K tokens) using ZERO LLM calls.

Pipeline:
  1. Low-signal filter: Remove reviews < 5 words or matching generic patterns
  2. Spam & gibberish filter: Drop all-caps rants, nonsensical text
  3. Rating-stratified selection: Keep all 1-2★, keep 3-5★ only if ≥ 10 words
  4. Chunk into batches of ~200 for Groq's 12K TPM limit
"""

import re
import math
from typing import List, Dict, Tuple

# ---------------------------------------------------------------------------
# Generic positive patterns (case-insensitive exact or prefix match)
# These are low-signal reviews that add no analytical value
# ---------------------------------------------------------------------------
GENERIC_PATTERNS = [
    r"^good\s*app?\.?$",
    r"^nice\.?$",
    r"^best\.?$",
    r"^best\s+app\.?$",
    r"^good\.?$",
    r"^great\.?$",
    r"^great\s+app\.?$",
    r"^excellent\.?$",
    r"^awesome\.?$",
    r"^love\s+it\.?$",
    r"^easy\s+to\s+use\.?$",
    r"^very\s+good\.?$",
    r"^very\s+nice\.?$",
    r"^very\s+good\s+app\.?$",
    r"^super\.?$",
    r"^superb\.?$",
    r"^ok\.?$",
    r"^okay\.?$",
]

_GENERIC_RE = [re.compile(p, re.IGNORECASE) for p in GENERIC_PATTERNS]

# Minimum word counts
MIN_WORDS_OVERALL = 5          # Absolute minimum to keep any review
MIN_WORDS_POSITIVE = 15        # Minimum for 3-5★ reviews (rating-stratified)
MAX_POSITIVE_REVIEWS = 150     # Cap on 3-5★ reviews to keep token budget tight

# Spam detection thresholds
SPAM_UPPERCASE_RATIO = 0.50    # If > 50% uppercase chars → potential spam

# Actionable keywords that rescue a review from the spam filter
# (even if it's mostly uppercase, if it mentions these it's probably real feedback)
ACTIONABLE_KEYWORDS = [
    "kyc", "upi", "payment", "crash", "bug", "glitch", "refund", "withdraw",
    "support", "customer", "charge", "fee", "brokerage", "error", "login",
    "otp", "sip", "mutual fund", "order", "stuck", "pending", "delay",
    "hang", "slow", "lag", "freeze", "update", "notification", "alert",
    "chart", "portfolio", "statement", "download", "money", "deduct",
]

# Target batch size (reviews per batch) to stay within 12K TPM
BATCH_SIZE = 200


def _is_generic(text: str) -> bool:
    """Check if text matches a known generic/low-signal pattern."""
    stripped = text.strip()
    return any(pat.match(stripped) for pat in _GENERIC_RE)


def _is_spam(text: str) -> bool:
    """
    Detect spam/gibberish using uppercase ratio heuristic.
    A review is spam if >50% of its alpha characters are uppercase
    AND it contains no actionable keywords.
    """
    alpha_chars = [c for c in text if c.isalpha()]
    if len(alpha_chars) < 10:
        return False  # Too short to judge

    upper_ratio = sum(1 for c in alpha_chars if c.isupper()) / len(alpha_chars)
    if upper_ratio <= SPAM_UPPERCASE_RATIO:
        return False

    # Check for actionable keywords before marking as spam
    text_lower = text.lower()
    has_actionable = any(kw in text_lower for kw in ACTIONABLE_KEYWORDS)
    return not has_actionable


def _word_count(text: str) -> int:
    """Count words in text."""
    return len(text.split())


def filter_low_signal(reviews: List[Dict]) -> Tuple[List[Dict], int]:
    """
    Remove reviews that are too short (< 5 words) or match
    generic positive patterns.

    Returns:
        (filtered_reviews, removed_count)
    """
    kept = []
    removed = 0
    for review in reviews:
        text = review.get("text", "")
        if _word_count(text) < MIN_WORDS_OVERALL:
            removed += 1
            continue
        if _is_generic(text):
            removed += 1
            continue
        kept.append(review)
    return kept, removed


def filter_spam(reviews: List[Dict]) -> Tuple[List[Dict], int]:
    """
    Remove spam/gibberish reviews (all-caps rants, nonsensical text).

    Returns:
        (filtered_reviews, removed_count)
    """
    kept = []
    removed = 0
    for review in reviews:
        text = review.get("text", "")
        if _is_spam(text):
            removed += 1
            continue
        kept.append(review)
    return kept, removed


def filter_by_rating_stratified(reviews: List[Dict]) -> Tuple[List[Dict], int]:
    """
    Rating-stratified selection:
      - Keep ALL 1-2★ reviews (richest actionable content)
      - Keep 3-5★ reviews only if they have ≥ 15 words (substantive feedback)
      - Cap 3-5★ reviews at MAX_POSITIVE_REVIEWS to keep token budget tight

    Returns:
        (filtered_reviews, removed_count)
    """
    import random

    negative = []
    positive_candidates = []
    removed = 0

    for review in reviews:
        rating = review.get("rating", 5)
        if isinstance(rating, str):
            try:
                rating = int(rating)
            except ValueError:
                rating = 5

        text = review.get("text", "")
        if rating <= 2:
            # Keep all negative reviews
            negative.append(review)
        elif _word_count(text) >= MIN_WORDS_POSITIVE:
            # Candidate positive/neutral review
            positive_candidates.append(review)
        else:
            removed += 1

    # Cap positive reviews to keep token budget manageable
    if len(positive_candidates) > MAX_POSITIVE_REVIEWS:
        random.seed(42)  # Deterministic for reproducibility
        sampled = random.sample(positive_candidates, MAX_POSITIVE_REVIEWS)
        removed += len(positive_candidates) - MAX_POSITIVE_REVIEWS
        positive_candidates = sampled

    kept = negative + positive_candidates
    return kept, removed


def deduplicate_reviews(reviews: List[Dict]) -> Tuple[List[Dict], int]:
    """
    Remove near-duplicate reviews based on normalized text.
    Two reviews are duplicates if their lowercase stripped text is identical.

    Returns:
        (deduplicated_reviews, removed_count)
    """
    seen = set()
    unique = []
    removed = 0
    for review in reviews:
        # Normalize: lowercase, strip whitespace and punctuation
        text = review.get("text", "").lower().strip()
        text_key = "".join(c for c in text if c.isalnum() or c.isspace())
        if text_key in seen:
            removed += 1
            continue
        seen.add(text_key)
        unique.append(review)
    return unique, removed


def estimate_tokens(text: str) -> int:
    """Estimate token count using char/4 heuristic."""
    return max(1, len(text) // 4)


def estimate_review_tokens(review: Dict) -> int:
    """Estimate tokens for a single review (text + JSON overhead)."""
    text = review.get("text", "")
    # ~20 tokens for JSON keys/formatting per review
    return estimate_tokens(text) + 20


def chunk_reviews(reviews: List[Dict], batch_size: int = BATCH_SIZE) -> List[List[Dict]]:
    """
    Split reviews into batches of `batch_size` for rate-limit-safe
    sequential Groq API calls.

    Returns:
        List of review batches.
    """
    return [
        reviews[i : i + batch_size]
        for i in range(0, len(reviews), batch_size)
    ]


def run_preprocessing(
    reviews: List[Dict],
    batch_size: int = BATCH_SIZE,
) -> Tuple[List[List[Dict]], Dict]:
    """
    Full pre-processing pipeline:
      1. Low-signal filter
      2. Spam filter
      3. Rating-stratified selection
      4. Chunk into batches

    Args:
        reviews: Phase 1 sanitized review list.
        batch_size: Max reviews per batch.

    Returns:
        (batches, stats) where stats is a dict of pipeline metrics.
    """
    stats = {"input_count": len(reviews)}

    print(f"\n{'='*60}")
    print(f"  Phase 2: Pre-Processing Pipeline")
    print(f"{'='*60}")
    print(f"[0] Input: {len(reviews)} reviews from Phase 1")

    # Step 1: Low-signal filter
    reviews, removed = filter_low_signal(reviews)
    stats["low_signal_removed"] = removed
    print(f"[1] Low-signal filter: removed {removed}, kept {len(reviews)}")

    # Step 2: Spam filter
    reviews, removed = filter_spam(reviews)
    stats["spam_removed"] = removed
    print(f"[2] Spam filter: removed {removed}, kept {len(reviews)}")

    # Step 3: Deduplication
    reviews, removed = deduplicate_reviews(reviews)
    stats["duplicates_removed"] = removed
    print(f"[3] Deduplication: removed {removed}, kept {len(reviews)}")

    # Step 4: Rating-stratified selection
    reviews, removed = filter_by_rating_stratified(reviews)
    stats["rating_filter_removed"] = removed
    print(f"[4] Rating-stratified: removed {removed}, kept {len(reviews)}")

    # Stats
    total_tokens = sum(estimate_review_tokens(r) for r in reviews)
    stats["output_count"] = len(reviews)
    stats["estimated_tokens"] = total_tokens
    stats["reduction_pct"] = round(
        (1 - len(reviews) / max(stats["input_count"], 1)) * 100, 1
    )

    print(f"[5] Final: {len(reviews)} reviews, ~{total_tokens} est. tokens")
    print(f"    Reduction: {stats['reduction_pct']}%")

    # Step 5: Chunk into batches
    batches = chunk_reviews(reviews, batch_size)
    stats["batch_count"] = len(batches)
    stats["batch_sizes"] = [len(b) for b in batches]
    print(f"[6] Chunked into {len(batches)} batches: {stats['batch_sizes']}")
    print(f"{'='*60}\n")

    return batches, stats
