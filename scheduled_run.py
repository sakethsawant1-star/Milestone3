"""
scheduled_run.py - Non-interactive entry point for GitHub Actions / Cron.

Reads all configuration from environment variables (no terminal prompts).
Designed to be called by the GitHub Actions workflow.

Required Environment Variables:
    GROQ_API_KEY          - Groq Cloud API key
    MCP_SERVER_URL        - Railway MCP server SSE endpoint
    TARGET_DOC_ID         - Google Document ID to append report to
    TARGET_EMAIL          - Recipient email address for the draft

Optional:
    REVIEW_COUNT          - Number of reviews to scrape (default: 500)
    SKIP_SCRAPE           - Set to "true" to skip scraping and use existing data
"""

import asyncio
import os
import sys
import json
import logging
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from phase1_ingestion.scraper import scrape_and_save
from phase1_ingestion.ingest import run_ingestion_pipeline
from phase4_e2e.orchestrator import PipelineOrchestrator

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def validate_env():
    """Validate all required environment variables are set."""
    required = {
        "GROQ_API_KEY": "Groq Cloud API key",
        "MCP_SERVER_URL": "Railway MCP server URL",
        "TARGET_DOC_ID": "Google Document ID",
        "TARGET_EMAIL": "Recipient email address",
    }

    missing = []
    for var, desc in required.items():
        if not os.environ.get(var):
            missing.append(f"  - {var}: {desc}")

    if missing:
        print("[FATAL] Missing required environment variables:")
        print("\n".join(missing))
        sys.exit(1)


async def run_scheduled():
    """Execute the full scheduled pipeline."""
    print("\n" + "=" * 60)
    print("  GROWW REVIEW ANALYST - Scheduled Run")
    print(f"  Triggered: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    validate_env()

    doc_id = os.environ["TARGET_DOC_ID"]
    email_to = os.environ["TARGET_EMAIL"]
    review_count = int(os.environ.get("REVIEW_COUNT", "500"))
    skip_scrape = os.environ.get("SKIP_SCRAPE", "false").lower() == "true"

    # ── Step 1: Scrape fresh reviews ──
    if not skip_scrape:
        print("\n[Step 1] Scraping fresh reviews from Play Store...")
        try:
            scraped_path = scrape_and_save(count=review_count)
            print(f"   Scraped reviews saved to: {scraped_path}")
        except Exception as e:
            logger.error(f"Scraping failed: {e}")
            print(f"   [FAIL] Scraping failed: {e}")
            print("   Falling back to existing data...")
            scraped_path = None
    else:
        print("\n[Step 1] Skipping scrape (SKIP_SCRAPE=true)")
        scraped_path = None

    # ── Step 2: Run ingestion pipeline on scraped data ──
    if scraped_path:
        print("\n[Step 2] Running ingestion pipeline on scraped data...")
        try:
            clean_reviews = run_ingestion_pipeline(scraped_path)

            # Save the cleaned data for the orchestrator
            clean_path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                "phase1_ingestion", "data", "groww_reviews_clean.json"
            )
            with open(clean_path, "w", encoding="utf-8") as f:
                json.dump(clean_reviews, f, ensure_ascii=False, indent=2)

            print(f"   Cleaned {len(clean_reviews)} reviews saved to {clean_path}")
        except Exception as e:
            logger.error(f"Ingestion failed: {e}")
            print(f"   [FAIL] Ingestion failed: {e}")
            print("   Falling back to existing cleaned data...")

    # ── Step 3: Run the E2E pipeline ──
    print("\n[Step 3] Running analysis and publishing pipeline...")
    orchestrator = PipelineOrchestrator(
        doc_id=doc_id,
        email_to=email_to,
    )
    result = await orchestrator.run()

    # ── Summary ──
    if result["status"] == "success":
        print("\n[SUCCESS] Scheduled run completed successfully!")
        print(f"   Doc: https://docs.google.com/document/d/{doc_id}/edit")
        print(f"   Email draft sent to: {email_to}")
    else:
        print("\n[WARNING] Scheduled run completed with issues.")
        sys.exit(1)

    return result


if __name__ == "__main__":
    asyncio.run(run_scheduled())
