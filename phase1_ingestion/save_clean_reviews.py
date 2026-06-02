"""
save_clean_reviews.py - Run the full pipeline and persist the clean output.

Saves the final PII-sanitized, English-only, filtered reviews as JSON
for downstream consumption by Phase 2 (Agent/LLM).

Usage:
    python -m phase1_ingestion.save_clean_reviews
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from phase1_ingestion.ingest import run_ingestion_pipeline

OUTPUT_PATH = os.path.join(
    os.path.dirname(__file__), "data", "groww_reviews_clean.json"
)


def main():
    data_path = os.path.join(
        os.path.dirname(__file__), "data", "groww_reviews_raw.csv"
    )

    if not os.path.exists(data_path):
        print("[ERROR] Raw reviews not found. Run fetch_reviews.py first.")
        sys.exit(1)

    clean = run_ingestion_pipeline(data_path)

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(clean, f, indent=2, ensure_ascii=False)

    print(f"\nSaved {len(clean)} clean reviews to: {OUTPUT_PATH}")

    # Print a few samples to verify
    print("\n--- Verification (first 5 reviews) ---")
    for r in clean[:5]:
        print(f"  [{r['rating']}*] {r['date']} | {r['text'][:90]}...")
        print()


if __name__ == "__main__":
    main()
