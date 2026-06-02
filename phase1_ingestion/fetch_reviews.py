"""
fetch_reviews.py - Fetch real Groww reviews from Google Play Store

Fetches public reviews for the Groww app, filters for English-only,
removes emoji-heavy reviews, and stores clean data as JSON + CSV.

Usage:
    python -m phase1_ingestion.fetch_reviews
"""

import json
import csv
import os
import re
import unicodedata
from datetime import datetime, timedelta

from google_play_scraper import Sort, reviews
from langdetect import detect, LangDetectException

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
GROWW_APP_ID = "com.nextbillion.groww"
TARGET_REVIEW_COUNT = 10000     # Fetch enough to span 8-12 weeks of reviews
MAX_AGE_WEEKS = 12
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "data")
OUTPUT_JSON = os.path.join(OUTPUT_DIR, "groww_reviews_raw.json")
OUTPUT_CSV = os.path.join(OUTPUT_DIR, "groww_reviews_raw.csv")

# Emoji detection regex (covers most Unicode emoji ranges)
_EMOJI_RE = re.compile(
    "["
    "\U0001F600-\U0001F64F"  # emoticons
    "\U0001F300-\U0001F5FF"  # symbols & pictographs
    "\U0001F680-\U0001F6FF"  # transport & map
    "\U0001F1E0-\U0001F1FF"  # flags
    "\U00002702-\U000027B0"  # dingbats
    "\U000024C2-\U0001F251"  # misc
    "\U0001f926-\U0001f937"
    "\U00010000-\U0010ffff"
    "\u2640-\u2642"
    "\u2600-\u2B55"
    "\u200d"
    "\u23cf"
    "\u23e9"
    "\u231a"
    "\ufe0f"
    "\u3030"
    "]+",
    flags=re.UNICODE,
)


def _has_excessive_emojis(text: str, threshold: float = 0.15) -> bool:
    """Return True if emoji characters make up more than `threshold` of text."""
    if not text:
        return False
    emoji_chars = _EMOJI_RE.findall(text)
    total_emoji_len = sum(len(e) for e in emoji_chars)
    return (total_emoji_len / max(len(text), 1)) > threshold


def _is_english(text: str) -> bool:
    """Detect if text is English using langdetect. Returns False for
    Hinglish, Hindi, or any other non-English language."""
    if not text or len(text.strip()) < 10:
        return False
    try:
        lang = detect(text)
        return lang == "en"
    except LangDetectException:
        return False


def fetch_groww_reviews(count: int = TARGET_REVIEW_COUNT) -> list:
    """Fetch reviews from Google Play Store for the Groww app."""
    print(f"[1] Fetching up to {count} reviews from Play Store...")

    all_reviews = []
    continuation_token = None
    batch_size = min(200, count)

    while len(all_reviews) < count:
        result, continuation_token = reviews(
            GROWW_APP_ID,
            lang="en",
            country="in",
            sort=Sort.NEWEST,
            count=batch_size,
            continuation_token=continuation_token,
        )
        if not result:
            break
        all_reviews.extend(result)
        print(f"    Fetched {len(all_reviews)} reviews so far...")
        if not continuation_token:
            break

    print(f"    Total fetched: {len(all_reviews)}")
    return all_reviews


def process_reviews(raw_reviews: list) -> list:
    """Filter and structure raw Play Store reviews."""
    cutoff = datetime.now() - timedelta(weeks=MAX_AGE_WEEKS)
    print(f"[2] Filtering: cutoff date = {cutoff.strftime('%Y-%m-%d')}")

    processed = []
    stats = {"total": len(raw_reviews), "old": 0, "non_english": 0,
             "emoji_heavy": 0, "short": 0, "kept": 0}

    for i, r in enumerate(raw_reviews):
        # Extract date
        review_date = r.get("at")
        if not review_date:
            continue
        if isinstance(review_date, datetime):
            rdate = review_date
        else:
            continue

        # Filter old reviews
        if rdate < cutoff:
            stats["old"] += 1
            continue

        text = r.get("content", "").strip()
        title = ""  # Play Store reviews don't have separate titles

        # Filter short / empty reviews
        if len(text.split()) < 3:
            stats["short"] += 1
            continue

        # Filter non-English (Hinglish, Hindi, etc.)
        if not _is_english(text):
            stats["non_english"] += 1
            continue

        # Filter emoji-heavy reviews
        if _has_excessive_emojis(text):
            stats["emoji_heavy"] += 1
            continue

        processed.append({
            "review_id": r.get("reviewId", f"R{i:04d}"),
            "rating": r.get("score", 0),
            "title": title,
            "text": text,
            "date": rdate.strftime("%Y-%m-%d"),
        })
        stats["kept"] += 1

    print(f"[3] Filter stats:")
    print(f"    Total fetched:  {stats['total']}")
    print(f"    Old (>{MAX_AGE_WEEKS}wk): {stats['old']}")
    print(f"    Non-English:    {stats['non_english']}")
    print(f"    Emoji-heavy:    {stats['emoji_heavy']}")
    print(f"    Too short:      {stats['short']}")
    print(f"    KEPT:           {stats['kept']}")

    return processed


def save_reviews(reviews_list: list):
    """Save processed reviews as both JSON and CSV."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # JSON
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(reviews_list, f, indent=2, ensure_ascii=False)
    print(f"[4] Saved {len(reviews_list)} reviews to {OUTPUT_JSON}")

    # CSV
    if reviews_list:
        with open(OUTPUT_CSV, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=reviews_list[0].keys())
            writer.writeheader()
            writer.writerows(reviews_list)
        print(f"    Saved CSV to {OUTPUT_CSV}")


def main():
    print("\n" + "=" * 60)
    print("  Groww Review Fetcher (Google Play Store)")
    print("=" * 60 + "\n")

    raw = fetch_groww_reviews()
    clean = process_reviews(raw)
    save_reviews(clean)

    print(f"\n{'='*60}")
    print(f"  Done! {len(clean)} English-only reviews stored.")
    print(f"{'='*60}\n")

    # Print sample
    print("--- Sample (first 5) ---")
    for r in clean[:5]:
        print(f"  [{r['rating']}*] {r['date']}  {r['text'][:80]}...")
        print()


if __name__ == "__main__":
    main()
