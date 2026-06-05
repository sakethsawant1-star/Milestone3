"""
eval_phase4_e2e.py — End-to-End Evaluation for Phase 4

Tests that a single pipeline execution:
  1. Reads review data
  2. Produces a valid FinalReport
  3. Appends the report to a Google Doc via MCP
  4. Creates a Gmail draft via MCP
  5. Requires zero manual intervention

Usage:
    python phase4_e2e/eval_phase4_e2e.py
"""

import sys
import os
import asyncio
from dotenv import load_dotenv

load_dotenv()

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from phase4_e2e.orchestrator import PipelineOrchestrator

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


async def run_e2e_test():
    """Run the full end-to-end pipeline and validate results."""

    # Get required inputs from environment or prompt
    doc_id = os.environ.get("TARGET_DOC_ID")
    email_to = os.environ.get("TARGET_EMAIL")

    if not doc_id:
        doc_id = input("\n📄 Enter Google Document ID for testing: ").strip()
    if not email_to:
        email_to = input("📧 Enter recipient email for testing: ").strip()

    if not doc_id or not email_to:
        print("❌ Cannot run E2E test without doc_id and email_to.")
        sys.exit(1)

    # ── Test Group 1: Pipeline Execution ──
    print("\n--- Test Group 1: Full Pipeline Execution ---")

    orchestrator = PipelineOrchestrator(
        doc_id=doc_id,
        email_to=email_to,
    )

    try:
        result = await orchestrator.run()
        record("Pipeline executed without crash", True)
    except Exception as e:
        record("Pipeline executed without crash", False, str(e))
        return  # Can't test further if pipeline crashed

    # ── Test Group 2: Report Validation ──
    print("\n--- Test Group 2: Report Validation ---")

    report = orchestrator.report
    record("FinalReport object generated", report is not None)

    if report:
        record("Themes ≤ 5", len(report.themes) <= 5, f"Got {len(report.themes)}")
        record("Quotes == 3", len(report.quotes) == 3, f"Got {len(report.quotes)}")
        record("Action ideas == 3", len(report.action_ideas) == 3, f"Got {len(report.action_ideas)}")

        word_count = len(report.text_body.split())
        record("Text body ≤ 250 words", word_count <= 250, f"Got {word_count} words")

    # ── Test Group 3: MCP Tool Execution ──
    print("\n--- Test Group 3: MCP Tool Execution ---")

    record(
        "Google Doc appended successfully",
        orchestrator.doc_result is not None,
        str(orchestrator.doc_result)[:100] if orchestrator.doc_result else "No result"
    )
    record(
        "Gmail draft created successfully",
        orchestrator.email_result is not None,
        str(orchestrator.email_result)[:100] if orchestrator.email_result else "No result"
    )

    # ── Test Group 4: Zero Manual Intervention ──
    print("\n--- Test Group 4: Autonomy ---")
    record(
        "Pipeline status is 'success'",
        result.get("status") == "success",
        f"Got: {result.get('status')}"
    )


def main():
    print("\n" + "=" * 60)
    print("  Phase 4 Evaluation: End-to-End Pipeline")
    print("=" * 60)

    asyncio.run(run_e2e_test())

    print("\n" + "=" * 60)
    total = len(results)
    passed = sum(1 for _, p in results if p)
    failed = total - passed
    print(f"  RESULTS: {passed}/{total} passed, {failed} failed")

    if failed == 0:
        print("  >>> Phase 4 EXIT CRITERIA MET — Full pipeline operational!")
    else:
        print("  >>> Phase 4 BLOCKED — Fix failing tests:")
        for name, p in results:
            if not p:
                print(f"      ✗ {name}")

    print("=" * 60 + "\n")
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
