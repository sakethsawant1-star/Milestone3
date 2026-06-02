"""
ingest.py - Data Ingestion Pipeline for Groww App Reviews

Pipeline steps:
  1. Load raw data from CSV/JSON
  2. Validate schema
  3. Filter by date (last N weeks)
  4. Remove non-actionable reviews (< 3 words)
  5. Sanitize PII via sanitizer.py
"""

import csv
import json
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional

from phase1_ingestion.sanitizer import sanitize_reviews

REQUIRED_FIELDS = {"review_id", "rating", "title", "text", "date"}
DEFAULT_MAX_AGE_WEEKS = 12
MIN_WORD_COUNT = 3
DATE_FORMAT = "%Y-%m-%d"


def load_raw_reviews(filepath: str) -> List[Dict]:
    """Load raw reviews from a CSV or JSON file."""
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Review data file not found: {filepath}")

    ext = os.path.splitext(filepath)[1].lower()
    if ext == ".csv":
        with open(filepath, "r", encoding="utf-8") as f:
            return [dict(row) for row in csv.DictReader(f)]
    elif ext == ".json":
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
        raise ValueError(f"Expected JSON array, got {type(data).__name__}")
    else:
        raise ValueError(f"Unsupported file format '{ext}'. Use .csv or .json")


def validate_schema(reviews: List[Dict]) -> List[Dict]:
    """Validate required fields, cast rating to int, check date format."""
    validated = []
    for i, review in enumerate(reviews):
        missing = REQUIRED_FIELDS - set(review.keys())
        if missing:
            print(f"[WARN] Row {i}: Missing fields {missing} — skipping.")
            continue
        try:
            review["rating"] = int(review["rating"])
        except (ValueError, TypeError):
            print(f"[WARN] Row {i}: Invalid rating — skipping.")
            continue
        try:
            datetime.strptime(review["date"], DATE_FORMAT)
        except ValueError:
            print(f"[WARN] Row {i}: Invalid date — skipping.")
            continue
        validated.append(review)
    return validated


def filter_by_date(
    reviews: List[Dict],
    max_age_weeks: int = DEFAULT_MAX_AGE_WEEKS,
    reference_date: Optional[datetime] = None,
) -> List[Dict]:
    """Keep only reviews from the last `max_age_weeks` weeks."""
    if reference_date is None:
        reference_date = datetime.now()
    cutoff = reference_date - timedelta(weeks=max_age_weeks)
    filtered = []
    for review in reviews:
        review_date = datetime.strptime(review["date"], DATE_FORMAT)
        if review_date >= cutoff:
            filtered.append(review)
        else:
            print(f"[INFO] Filtered old review {review['review_id']} ({review['date']})")
    return filtered


def filter_non_actionable(reviews: List[Dict]) -> List[Dict]:
    """Remove reviews with fewer than MIN_WORD_COUNT words in text."""
    actionable = []
    for review in reviews:
        word_count = len(review.get("text", "").split())
        if word_count >= MIN_WORD_COUNT:
            actionable.append(review)
        else:
            print(f"[INFO] Filtered non-actionable: {review['review_id']}")
    return actionable


def run_ingestion_pipeline(
    filepath: str,
    max_age_weeks: int = DEFAULT_MAX_AGE_WEEKS,
    reference_date: Optional[datetime] = None,
) -> List[Dict]:
    """
    Full Phase 1 pipeline: Load → Validate → Date Filter →
    Non-actionable Filter → PII Sanitization.
    """
    print(f"\n{'='*60}")
    print(f"  Phase 1: Data Ingestion & PII Sanitization")
    print(f"{'='*60}")

    raw = load_raw_reviews(filepath)
    print(f"[1] Loaded {len(raw)} raw reviews.")

    validated = validate_schema(raw)
    print(f"[2] {len(validated)} reviews passed validation.")

    recent = filter_by_date(validated, max_age_weeks, reference_date)
    print(f"[3] {len(recent)} reviews within date range.")

    actionable = filter_non_actionable(recent)
    print(f"[4] {len(actionable)} actionable reviews remain.")

    clean = sanitize_reviews(actionable)
    print(f"[5] Sanitization complete. {len(clean)} reviews ready.")

    print(f"{'='*60}\n")
    return clean


if __name__ == "__main__":
    import sys
    data_path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        os.path.dirname(__file__), "data", "sample_reviews.csv"
    )
    results = run_ingestion_pipeline(data_path)
    print(f"\n--- Sample Output (first 3) ---")
    for r in results[:3]:
        print(f"  [{r['rating']}*] {r['title']}")
        print(f"       {r['text'][:100]}...\n")
