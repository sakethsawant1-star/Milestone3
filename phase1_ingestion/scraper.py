"""
scraper.py - Google Play Store Review Scraper for Groww App

Fetches the latest reviews from the Groww app on the Google Play Store
using the google-play-scraper library. Designed for weekly scheduled runs
via GitHub Actions.

Usage:
    python -m phase1_ingestion.scraper
    python -m phase1_ingestion.scraper --count 500 --output reviews_latest.json
"""

import json
import os
import argparse
import logging
from datetime import datetime
from typing import List, Dict

try:
    from google_play_scraper import Sort, reviews
except ImportError:
    raise ImportError(
        "google-play-scraper not installed. Run: pip install google-play-scraper"
    )

logger = logging.getLogger(__name__)

# Groww app package name on the Play Store
GROWW_PACKAGE = "com.nextbillion.groww"

# Default output directory
DEFAULT_OUTPUT_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "data"
)


def scrape_reviews(
    count: int = 500,
    sort: Sort = Sort.NEWEST,
    lang: str = "en",
    country: str = "in",
) -> List[Dict]:
    """
    Scrape reviews from the Google Play Store for the Groww app.

    Args:
        count: Number of reviews to fetch (max ~1000 per call).
        sort: Sort order (Sort.NEWEST or Sort.MOST_RELEVANT).
        lang: Language filter.
        country: Country filter.

    Returns:
        List of review dicts with standardized schema.
    """
    print(f"[Scraper] Fetching {count} reviews for {GROWW_PACKAGE}...")

    result, _ = reviews(
        GROWW_PACKAGE,
        lang=lang,
        country=country,
        sort=sort,
        count=count,
    )

    print(f"[Scraper] Fetched {len(result)} raw reviews from Play Store.")

    # Normalize to our standard schema
    normalized = []
    for i, r in enumerate(result):
        try:
            review_date = r.get("at")
            if isinstance(review_date, datetime):
                date_str = review_date.strftime("%Y-%m-%d")
            else:
                date_str = str(review_date)[:10] if review_date else "1970-01-01"

            normalized.append({
                "review_id": r.get("reviewId", f"play_{i}"),
                "rating": int(r.get("score", 0)),
                "title": r.get("content", "")[:80],  # Play Store has no title, use first 80 chars
                "text": r.get("content", ""),
                "date": date_str,
            })
        except Exception as e:
            logger.warning(f"[Scraper] Skipping review {i}: {e}")
            continue

    print(f"[Scraper] Normalized {len(normalized)} reviews to standard schema.")
    return normalized


def save_reviews(reviews_data: List[Dict], output_path: str) -> str:
    """
    Save scraped reviews to a JSON file.

    Args:
        reviews_data: List of normalized review dicts.
        output_path: Full path to save the JSON file.

    Returns:
        The output file path.
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(reviews_data, f, ensure_ascii=False, indent=2)

    print(f"[Scraper] Saved {len(reviews_data)} reviews to {output_path}")
    return output_path


def scrape_and_save(
    count: int = 500,
    output_dir: str = None,
    filename: str = None,
) -> str:
    """
    Full scrape pipeline: fetch from Play Store and save to JSON.

    Args:
        count: Number of reviews to fetch.
        output_dir: Directory to save the output file.
        filename: Output filename. Defaults to timestamped name.

    Returns:
        Path to the saved JSON file.
    """
    output_dir = output_dir or DEFAULT_OUTPUT_DIR

    if filename is None:
        date_str = datetime.now().strftime("%Y%m%d")
        filename = f"groww_reviews_{date_str}.json"

    output_path = os.path.join(output_dir, filename)

    scraped = scrape_reviews(count=count)

    if not scraped:
        raise ValueError("[Scraper] No reviews fetched. Check network or package name.")

    return save_reviews(scraped, output_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scrape Groww Play Store reviews")
    parser.add_argument("--count", type=int, default=500, help="Number of reviews to fetch")
    parser.add_argument("--output", type=str, default=None, help="Output filename")
    args = parser.parse_args()

    path = scrape_and_save(count=args.count, filename=args.output)
    print(f"\n[Done] Reviews saved to: {path}")
