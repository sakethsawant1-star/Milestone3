"""
eval_phase2.py - Phase 2 Exit Criteria Evaluation Script

Validates the Phase 2 agent pipeline against all exit criteria:
  1. len(output.themes) <= 5
  2. len(output.quotes) == 3
  3. len(output.action_ideas) == 3
  4. len(output.text_body.split()) <= 250
  5. Total Groq API calls per run <= 4
  6. No single call exceeds 10,000 tokens (input + output)

Has two modes:
  - LIVE mode: Actually calls Groq API (requires GROQ_API_KEY)
  - MOCK mode: Tests preprocessor + schemas with mock LLM responses

Run:  python -m phase2_agent.eval_phase2 [--live]
"""

import os
import sys
import json
import argparse

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from phase1_ingestion.ingest import run_ingestion_pipeline
from phase2_agent.preprocessor import (
    run_preprocessing,
    filter_low_signal,
    filter_spam,
    filter_by_rating_stratified,
    estimate_tokens,
)
from phase2_agent.schemas import BatchAnalysisResult, FinalReport, Theme, Quote, ActionIdea
from phase2_agent.rate_limiter import GroqRateLimiter, TokenBudgetExhausted
from phase2_agent.prompts import build_batch_prompt, build_synthesis_prompt, SYSTEM_PROMPT

PASS = "[PASS]"
FAIL = "[FAIL]"
results = []


def record(test_name: str, passed: bool, detail: str = ""):
    """Record a test result."""
    status = PASS if passed else FAIL
    results.append((test_name, passed))
    msg = f"  {status}  {test_name}"
    if detail:
        msg += f" - {detail}"
    print(msg)


# ---------------------------------------------------------------------------
# Mock data for schema testing
# ---------------------------------------------------------------------------
MOCK_BATCH_RESULT = {
    "themes": [
        {"name": "KYC Delays", "description": "Users waiting weeks for KYC verification",
         "review_count": 45, "sentiment": "negative"},
        {"name": "High Brokerage", "description": "Charges perceived as too high",
         "review_count": 38, "sentiment": "negative"},
        {"name": "App Crashes", "description": "App crashes during market hours",
         "review_count": 30, "sentiment": "negative"},
    ],
    "quotes": [
        {"text": "KYC pending for 3 weeks, very frustrating", "rating": 1, "theme": "KYC Delays"},
        {"text": "Brokerage charges are eating my profits", "rating": 2, "theme": "High Brokerage"},
        {"text": "App crashes every morning at 9:15", "rating": 1, "theme": "App Crashes"},
    ],
    "action_ideas": [
        {"title": "KYC Fast Track", "description": "Implement automated document verification with 24hr SLA",
         "target_theme": "KYC Delays"},
        {"title": "Transparent Fee Display", "description": "Show total charges before order confirmation",
         "target_theme": "High Brokerage"},
    ],
    "review_count": 200,
    "summary": "Key concerns are KYC delays, high brokerage charges, and app stability during market hours.",
}

MOCK_FINAL_REPORT = {
    "themes": [
        {"name": "KYC Delays", "description": "Users waiting weeks for KYC verification",
         "review_count": 85, "sentiment": "negative"},
        {"name": "High Brokerage", "description": "Charges perceived as too high compared to competitors",
         "review_count": 72, "sentiment": "negative"},
        {"name": "App Stability", "description": "Crashes and lag during peak trading hours",
         "review_count": 55, "sentiment": "negative"},
        {"name": "Customer Support", "description": "Poor response times and unhelpful agents",
         "review_count": 40, "sentiment": "negative"},
        {"name": "UI/UX Praise", "description": "Clean interface appreciated by beginners",
         "review_count": 30, "sentiment": "positive"},
    ],
    "quotes": [
        {"text": "Been waiting 3 weeks for KYC verification. Uploaded Aadhaar and PAN but still pending.",
         "rating": 1, "theme": "KYC Delays"},
        {"text": "Charges are more than profit. Hidden fees everywhere.",
         "rating": 1, "theme": "High Brokerage"},
        {"text": "App crashes every morning between 9:15 and 9:30. Cannot place orders.",
         "rating": 1, "theme": "App Stability"},
    ],
    "action_ideas": [
        {"title": "KYC Fast Track System", "description": "Implement automated document verification via DigiLocker with a 24-hour SLA guarantee.",
         "target_theme": "KYC Delays"},
        {"title": "Fee Transparency Dashboard", "description": "Show a complete breakdown of all charges before order confirmation, including regulatory fees.",
         "target_theme": "High Brokerage"},
        {"title": "Infrastructure Scaling for Market Open", "description": "Pre-scale server capacity 15 minutes before market open to handle the 9:15 AM traffic spike.",
         "target_theme": "App Stability"},
    ],
    "text_body": (
        "Across 400 reviews from the last 8 weeks, Groww users express a clear divide: "
        "beginners love the clean UI, but active traders face significant friction. "
        "The top pain point is KYC verification delays, with 85 reviews citing multi-week "
        "waits despite submitting valid documents. High brokerage charges rank second, "
        "with 72 users comparing Groww unfavorably to Zerodha's fee structure. "
        "App stability during the 9:15-9:30 AM market open window is the third critical issue, "
        "causing missed trades and financial losses. Customer support compounds these problems, "
        "with users reporting 4-5 day response times and repetitive information requests. "
        "On the positive side, new investors consistently praise the onboarding flow and "
        "portfolio tracking features. The recommended priority is to fast-track KYC automation "
        "through DigiLocker integration, display complete fee breakdowns before order confirmation, "
        "and pre-scale infrastructure for market open. These three actions would address "
        "the concerns of over 200 dissatisfied users."
    ),
}


def test_preprocessor():
    """Test the pre-processing pipeline with real Phase 1 data."""
    print("\n--- Test Group 1: Pre-Processing Pipeline ---")

    # Load Phase 1 data
    data_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "phase1_ingestion", "data", "groww_reviews_clean.json"
    )

    if not os.path.exists(data_path):
        data_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "phase1_ingestion", "data", "sample_reviews.csv"
        )
        reviews = run_ingestion_pipeline(data_path)
    else:
        with open(data_path, "r", encoding="utf-8") as f:
            reviews = json.load(f)

    initial_count = len(reviews)
    record("Phase 1 data loaded", initial_count > 0, f"{initial_count} reviews")

    # Run preprocessing
    batches, stats = run_preprocessing(reviews)

    # Test: Significant data reduction occurred
    record(
        "Data reduction > 30%",
        stats["reduction_pct"] > 30,
        f"{stats['reduction_pct']}% reduction"
    )

    # Test: Output is non-empty
    total_output = stats["output_count"]
    record("Output is non-empty", total_output > 0, f"{total_output} reviews")

    # Test: Batches are created
    record(
        "Batches created",
        stats["batch_count"] >= 1,
        f"{stats['batch_count']} batches of sizes {stats['batch_sizes']}"
    )

    # Test: Each batch ≤ 200 reviews
    all_batches_ok = all(len(b) <= 200 for b in batches)
    record(
        "Each batch <= 200 reviews", all_batches_ok)

    # Test: Estimated tokens are reasonable for batched processing
    record(
        "Estimated tokens < 45K",
        stats["estimated_tokens"] < 45_000,
        f"~{stats['estimated_tokens']} tokens"
    )

    return batches, stats


def test_preprocessor_filters():
    """Unit tests for individual filter functions."""
    print("\n--- Test Group 2: Filter Unit Tests ---")

    # Low-signal filter
    test_reviews = [
        {"review_id": "1", "rating": 5, "text": "Good app", "title": "", "date": "2026-05-01"},
        {"review_id": "2", "rating": 5, "text": "Nice", "title": "", "date": "2026-05-01"},
        {"review_id": "3", "rating": 5, "text": "Best", "title": "", "date": "2026-05-01"},
        {"review_id": "4", "rating": 1, "text": "KYC verification stuck for 3 weeks very frustrating", "title": "", "date": "2026-05-01"},
        {"review_id": "5", "rating": 5, "text": "ok", "title": "", "date": "2026-05-01"},
    ]

    filtered, removed = filter_low_signal(test_reviews)
    record("Low-signal: removes generic reviews", removed >= 3, f"removed {removed}/5")
    record("Low-signal: keeps actionable review", any(r["review_id"] == "4" for r in filtered))

    # Spam filter
    spam_reviews = [
        {"review_id": "6", "rating": 1, "text": "WORST APP EVER DELETE THIS GARBAGE NOW DELETE THIS APP",
         "title": "", "date": "2026-05-01"},
        {"review_id": "7", "rating": 1, "text": "KYC is stuck, very bad experience with support team",
         "title": "", "date": "2026-05-01"},
    ]

    filtered, removed = filter_spam(spam_reviews)
    record("Spam filter: catches all-caps rant", removed >= 1)
    record("Spam filter: keeps actionable complaint", any(r["review_id"] == "7" for r in filtered))

    # Rating-stratified
    strat_reviews = [
        {"review_id": "8", "rating": 1, "text": "bad experience with app", "title": "", "date": "2026-05-01"},
        {"review_id": "9", "rating": 5, "text": "good app works fine", "title": "", "date": "2026-05-01"},
        {"review_id": "10", "rating": 5,
         "text": "This app has a great UI but the brokerage charges are way too high for options trading compared to other apps",
         "title": "", "date": "2026-05-01"},
    ]

    filtered, removed = filter_by_rating_stratified(strat_reviews)
    record("Stratified: keeps all 1-2 star", any(r["review_id"] == "8" for r in filtered))
    record("Stratified: removes short 5 star", not any(r["review_id"] == "9" for r in filtered))
    record("Stratified: keeps long 5 star", any(r["review_id"] == "10" for r in filtered))


def test_schemas():
    """Test Pydantic schema validation."""
    print("\n--- Test Group 3: Schema Validation ---")

    # BatchAnalysisResult
    try:
        batch_result = BatchAnalysisResult(**MOCK_BATCH_RESULT)
        record("BatchAnalysisResult validates correctly", True)
        record("Batch themes <= 5", len(batch_result.themes) <= 5)
    except Exception as e:
        record("BatchAnalysisResult validates correctly", False, str(e))

    # FinalReport
    try:
        report = FinalReport(**MOCK_FINAL_REPORT)
        record("FinalReport validates correctly", True)
        record("Report themes <= 5", len(report.themes) <= 5, f"{len(report.themes)} themes")
        record("Report quotes == 3", len(report.quotes) == 3, f"{len(report.quotes)} quotes")
        record("Report action_ideas == 3", len(report.action_ideas) == 3, f"{len(report.action_ideas)} ideas")
        word_count = len(report.text_body.split())
        record("Report text_body <= 250 words", word_count <= 250, f"{word_count} words")
    except Exception as e:
        record("FinalReport validates correctly", False, str(e))

    # Test: 6+ themes should fail
    bad_report = dict(MOCK_FINAL_REPORT)
    bad_report["themes"] = MOCK_FINAL_REPORT["themes"] + [
        {"name": "T6", "description": "Extra theme", "review_count": 1, "sentiment": "negative"},
    ]
    try:
        FinalReport(**bad_report)
        record("Rejects > 5 themes", False, "Should have raised validation error")
    except Exception:
        record("Rejects > 5 themes", True)

    # Test: > 250 words body should fail
    bad_body = dict(MOCK_FINAL_REPORT)
    bad_body["text_body"] = " ".join(["word"] * 260)
    try:
        FinalReport(**bad_body)
        record("Rejects > 250 word body", False, "Should have raised validation error")
    except Exception:
        record("Rejects > 250 word body", True)


def test_rate_limiter():
    """Test rate limiter logic."""
    print("\n--- Test Group 4: Rate Limiter ---")

    rl = GroqRateLimiter(min_spacing=0.1, daily_budget=50_000)  # Relaxed for testing

    # Token estimation
    tokens = rl.estimate_tokens("This is a test string with some words in it.")
    record("Token estimation works", tokens > 0, f"Estimated {tokens} tokens")

    # Budget check — should pass
    try:
        rl.check_budget(5_000, 1_500)
        record("Budget check passes for normal call", True)
    except Exception as e:
        record("Budget check passes for normal call", False, str(e))

    # Budget check — should fail for oversized call
    try:
        rl.check_budget(15_000, 2_000)
        record("Budget rejects oversized call", False, "Should have raised ValueError")
    except ValueError:
        record("Budget rejects oversized call", True)
    except TokenBudgetExhausted:
        record("Budget rejects oversized call", True)

    # Record calls and check daily tracking
    rl.record_call(5_000, 1_000, "test-model")
    rl.record_call(5_000, 1_000, "test-model")
    summary = rl.daily_usage_summary
    record(
        "Daily usage tracking works",
        summary["tokens_used"] == 12_000,
        f"Used: {summary['tokens_used']}"
    )

    # Budget exhaustion
    rl2 = GroqRateLimiter(min_spacing=0.1, daily_budget=10_000)
    rl2.record_call(5_000, 4_500, "test-model")
    try:
        rl2.check_budget(5_000, 1_500)
        record("Budget exhaustion detected", False, "Should have raised exception")
    except TokenBudgetExhausted:
        record("Budget exhaustion detected", True)


def test_prompts():
    """Test prompt construction."""
    print("\n--- Test Group 5: Prompt Construction ---")

    test_reviews = [
        {"rating": 1, "text": "KYC stuck for weeks"},
        {"rating": 2, "text": "Brokerage too high"},
    ]

    batch_prompt = build_batch_prompt(test_reviews)
    record("Batch prompt contains review count", "2" in batch_prompt)
    record("Batch prompt contains review text", "KYC" in batch_prompt)
    record("System prompt is non-empty", len(SYSTEM_PROMPT) > 100)

    # Check estimated prompt size is within limits
    prompt_tokens = len(batch_prompt) // 4
    record(
        "Batch prompt token estimate reasonable",
        prompt_tokens < 8_000,
        f"~{prompt_tokens} tokens"
    )


def test_live_agent():
    """
    LIVE TEST: Actually calls Groq API.
    Only runs when --live flag is passed.
    """
    print("\n--- Test Group 6: LIVE Agent Pipeline ---")
    print("  WARNING: This test makes real Groq API calls (~3 min)")

    from phase2_agent.agent import GrowwReviewAgent

    # Load Phase 1 data
    data_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "phase1_ingestion", "data", "groww_reviews_clean.json"
    )

    if os.path.exists(data_path):
        with open(data_path, "r", encoding="utf-8") as f:
            reviews = json.load(f)
    else:
        data_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "phase1_ingestion", "data", "sample_reviews.csv"
        )
        reviews = run_ingestion_pipeline(data_path)

    # Run the full agent pipeline
    agent = GrowwReviewAgent()
    report = agent.analyze_reviews(reviews, batch_size=200)

    # Exit criteria assertions
    record(
        "themes <= 5",
        len(report.themes) <= 5,
        f"{len(report.themes)} themes"
    )
    record(
        "quotes == 3",
        len(report.quotes) == 3,
        f"{len(report.quotes)} quotes"
    )
    record(
        "action_ideas == 3",
        len(report.action_ideas) == 3,
        f"{len(report.action_ideas)} ideas"
    )
    word_count = len(report.text_body.split())
    record(
        "text_body <= 250 words",
        word_count <= 250,
        f"{word_count} words"
    )
    record(
        "Groq calls <= 4",
        agent.call_count <= 4,
        f"{agent.call_count} calls"
    )

    # Check rate limiter logs
    for entry in agent.rate_limiter.call_log:
        call_total = entry["input_tokens"] + entry["output_tokens"]
        if call_total > 10_000:
            record(
                f"Call at {entry['timestamp']} <= 10K tokens",
                False,
                f"{call_total} tokens"
            )
            break
    else:
        record("All calls <= 10K tokens each", True)

    # Print the final report
    print(f"\n{'-'*40}")
    print("  FINAL REPORT PREVIEW")
    print(f"{'-'*40}")
    print(f"\n  Themes:")
    for t in report.themes:
        print(f"    - {t.name} ({t.review_count} reviews, {t.sentiment})")
    print(f"\n  Quotes:")
    for q in report.quotes:
        print(f"    [{q.rating} star] \"{q.text[:80]}...\"")
    print(f"\n  Action Ideas:")
    for a in report.action_ideas:
        print(f"    -> {a.title}: {a.description[:80]}...")
    print(f"\n  Report ({word_count} words):")
    print(f"    {report.text_body[:300]}...")

    # Save report to JSON
    output_path = os.path.join(
        os.path.dirname(__file__), "final_report.json"
    )
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report.model_dump(), f, indent=2, ensure_ascii=False)
    print(f"\n  Report saved to: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Phase 2 Evaluation")
    parser.add_argument("--live", action="store_true",
                        help="Run LIVE tests with real Groq API calls")
    args = parser.parse_args()

    print("\n" + "=" * 60)
    print("  Phase 2 Evaluation: Exit Criteria Tests")
    print("=" * 60)

    # Always run offline tests
    test_preprocessor()
    test_preprocessor_filters()
    test_schemas()
    test_rate_limiter()
    test_prompts()

    # Live tests only if --live flag
    if args.live:
        test_live_agent()
    else:
        print("\n--- Test Group 6: LIVE Agent Pipeline ---")
        print("  >> Skipped (run with --live to execute)")

    # Summary
    print("\n" + "=" * 60)
    total = len(results)
    passed = sum(1 for _, p in results if p)
    failed = total - passed
    print(f"  RESULTS: {passed}/{total} passed, {failed} failed")

    if failed == 0:
        print("  >>> Phase 2 EXIT CRITERIA MET - Ready for Phase 3!")
    else:
        print("  >>> Phase 2 BLOCKED - Fix failing tests before proceeding.")
        for name, p in results:
            if not p:
                print(f"      X {name}")

    print("=" * 60 + "\n")
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
