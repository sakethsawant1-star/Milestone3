"""
eval_phase1.py - Phase 1 Exit Criteria Evaluation Script

This script validates the entire Phase 1 ingestion pipeline against
the exit criteria defined in Docs/phase_wise_implementation_plan.md:

  1. Reviews older than 12 weeks MUST be filtered out.
  2. PII (emails, phone numbers, PAN, Aadhaar, etc.) MUST be redacted
     and replaced with [REDACTED].
  3. Non-actionable reviews (< 3 words) MUST be removed.
  4. Output schema MUST match: [{review_id, rating, title, text, date}].

Run:  python -m phase1_ingestion.eval_phase1
"""

import os
import sys
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from phase1_ingestion.ingest import run_ingestion_pipeline
from phase1_ingestion.sanitizer import sanitize_text

REQUIRED_KEYS = {"review_id", "rating", "title", "text", "date"}
PASS = "[PASS]"
FAIL = "[FAIL]"

results = []


def record(test_name: str, passed: bool, detail: str = ""):
    """Record a test result."""
    status = PASS if passed else FAIL
    results.append((test_name, passed))
    msg = f"  {status}  {test_name}"
    if detail:
        msg += f" — {detail}"
    print(msg)


def main():
    print("\n" + "=" * 60)
    print("  Phase 1 Evaluation: Exit Criteria Tests")
    print("=" * 60 + "\n")

    data_path = os.path.join(
        os.path.dirname(__file__), "data", "sample_reviews.csv"
    )

    # Use a fixed reference date so tests are deterministic
    # Our sample data has reviews from 2024-01-15 to 2026-05-18
    # With ref date 2026-05-18, 12 weeks back = ~2026-02-23
    ref_date = datetime(2026, 5, 18)

    reviews = run_ingestion_pipeline(
        data_path,
        max_age_weeks=12,
        reference_date=ref_date,
    )

    # ------------------------------------------------------------------
    # TEST 1: Old reviews are filtered out
    # ------------------------------------------------------------------
    print("\n--- Test Group 1: Date Filtering ---")

    old_ids = {"R051", "R052"}  # 2024-01-15 and 2024-06-20
    remaining_ids = {r["review_id"] for r in reviews}
    old_present = old_ids & remaining_ids

    record(
        "Old reviews (2024) are filtered out",
        len(old_present) == 0,
        f"Still present: {old_present}" if old_present else "None leaked",
    )

    # Verify all remaining reviews are within 12 weeks
    cutoff = datetime(2026, 2, 23)
    all_recent = all(
        datetime.strptime(r["date"], "%Y-%m-%d") >= cutoff for r in reviews
    )
    record("All remaining reviews are within 12-week window", all_recent)

    # ------------------------------------------------------------------
    # TEST 2: PII is redacted
    # ------------------------------------------------------------------
    print("\n--- Test Group 2: PII Sanitization ---")

    all_text = " ".join(r["text"] + " " + r["title"] for r in reviews)

    # Check specific PII patterns that exist in sample data
    pii_checks = [
        ("Email: helpdesk@groww.in", "helpdesk@groww.in"),
        ("Email: rahul.sharma@gmail.com", "rahul.sharma@gmail.com"),
        ("Email: dev@groww.in", "dev@groww.in"),
        ("Email: mytaxmail@yahoo.com", "mytaxmail@yahoo.com"),
        ("Phone: 9876543210", "9876543210"),
        ("Phone: 9123456789", "9123456789"),
        ("Phone: 8899776655", "8899776655"),
        ("PAN: ABCDE1234F", "ABCDE1234F"),
        ("PAN: FGHIJ5678K", "FGHIJ5678K"),
    ]

    for label, pattern in pii_checks:
        found = pattern in all_text
        record(f"{label} is redacted", not found,
               "LEAKED in output!" if found else "Scrubbed")

    # Verify [REDACTED] tag exists (meaning sanitizer actually ran)
    has_redacted = "[REDACTED]" in all_text
    record("[REDACTED] tags are present in output", has_redacted)

    # ------------------------------------------------------------------
    # TEST 3: Non-actionable reviews filtered
    # ------------------------------------------------------------------
    print("\n--- Test Group 3: Non-Actionable Filtering ---")

    short_ids = {"R004", "R012", "R020"}  # "Good app", "Nice", "Best"
    short_present = short_ids & remaining_ids
    record(
        "Short reviews (< 3 words) are removed",
        len(short_present) == 0,
        f"Still present: {short_present}" if short_present else "All removed",
    )

    # ------------------------------------------------------------------
    # TEST 4: Output schema validation
    # ------------------------------------------------------------------
    print("\n--- Test Group 4: Output Schema ---")

    all_valid_schema = all(
        REQUIRED_KEYS.issubset(set(r.keys())) for r in reviews
    )
    record("All reviews have required keys", all_valid_schema)

    all_int_ratings = all(isinstance(r["rating"], int) for r in reviews)
    record("All ratings are integers", all_int_ratings)

    record("Output is a non-empty list", len(reviews) > 0,
           f"{len(reviews)} reviews")

    # ------------------------------------------------------------------
    # TEST 5: Standalone sanitizer unit tests
    # ------------------------------------------------------------------
    print("\n--- Test Group 5: Sanitizer Unit Tests ---")

    record(
        "sanitize_text strips email",
        "[REDACTED]" in sanitize_text("Contact me at user@test.com please"),
    )
    record(
        "sanitize_text strips phone",
        "[REDACTED]" in sanitize_text("Call 9876543210 now"),
    )
    record(
        "sanitize_text strips PAN",
        "[REDACTED]" in sanitize_text("PAN is ABCDE1234F"),
    )
    record(
        "sanitize_text strips Aadhaar",
        "[REDACTED]" in sanitize_text("Aadhaar 1234-5678-9012"),
    )
    record(
        "sanitize_text handles empty string",
        sanitize_text("") == "",
    )
    record(
        "sanitize_text handles None",
        sanitize_text(None) is None,
    )

    # ------------------------------------------------------------------
    # SUMMARY
    # ------------------------------------------------------------------
    print("\n" + "=" * 60)
    total = len(results)
    passed = sum(1 for _, p in results if p)
    failed = total - passed
    print(f"  RESULTS: {passed}/{total} passed, {failed} failed")

    if failed == 0:
        print("  >>> Phase 1 EXIT CRITERIA MET - Ready for Phase 2!")
    else:
        print("  >>> Phase 1 BLOCKED - Fix failing tests before proceeding.")

    print("=" * 60 + "\n")
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
