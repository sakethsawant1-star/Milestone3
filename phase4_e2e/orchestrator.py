"""
orchestrator.py — Phase 4 End-to-End Pipeline Orchestrator

Stitches the full autonomous pipeline:
  1. Ingest & sanitize reviews (Phase 1)
  2. Analyze with Groq LLM (Phase 2)
  3. Publish to Google Docs & draft Gmail via MCP (Phase 3)

A single call to `run_pipeline()` executes the entire workflow
with zero manual intervention.
"""

import os
import sys
import json
import asyncio
import logging
from typing import Optional
from dotenv import load_dotenv

# Ensure project root is in path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from phase2_agent.agent import GrowwReviewAgent
from phase2_agent.schemas import FinalReport
from phase3_mcp.mcp_client import GrowwMCPClient
from phase4_e2e.report_formatter import format_doc_report, format_email_summary

load_dotenv()

logger = logging.getLogger(__name__)


class PipelineOrchestrator:
    """
    End-to-end orchestrator for the Groww Review Analyst pipeline.

    Usage:
        orchestrator = PipelineOrchestrator(
            doc_id="your-google-doc-id",
            email_to="pm@example.com",
        )
        result = asyncio.run(orchestrator.run())
    """

    def __init__(
        self,
        doc_id: str,
        email_to: str,
        data_path: Optional[str] = None,
        groq_api_key: Optional[str] = None,
        mcp_server_url: Optional[str] = None,
    ):
        """
        Args:
            doc_id: Google Document ID to append the report to.
            email_to: Recipient email address for the Gmail draft.
            data_path: Path to the cleaned reviews JSON. Defaults to Phase 1 output.
            groq_api_key: Groq API key. Reads from env if not provided.
            mcp_server_url: MCP server URL. Reads from env if not provided.
        """
        self.doc_id = doc_id
        self.email_to = email_to
        self.data_path = data_path or os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "phase1_ingestion", "data", "groww_reviews_clean.json"
        )
        self.groq_api_key = groq_api_key
        self.mcp_server_url = mcp_server_url or os.environ.get("MCP_SERVER_URL")

        # Pipeline state
        self.report: Optional[FinalReport] = None
        self.doc_result = None
        self.email_result = None

    async def run(self) -> dict:
        """
        Execute the full end-to-end pipeline.

        Returns:
            dict with keys: 'report', 'doc_result', 'email_result', 'status'
        """
        print("\n" + "=" * 60)
        print("  GROWW REVIEW ANALYST - End-to-End Pipeline")
        print("=" * 60)

        # ── Step 1: Ingest Data (Phase 1) ──
        print("\n[Step 1] Loading cleaned review data...")
        reviews = self._load_data()
        print(f"   Loaded {len(reviews)} reviews from {os.path.basename(self.data_path)}")

        # ── Step 2: Analyze with Groq LLM (Phase 2) ──
        print("\n[Step 2] Running Groq LLM analysis...")
        self.report = self._analyze(reviews)
        print(f"   Analysis complete: {len(self.report.themes)} themes, "
              f"{len(self.report.quotes)} quotes, "
              f"{len(self.report.action_ideas)} ideas")

        # ── Step 3: Publish via MCP (Phase 3) ──
        print("\n[Step 3] Publishing via MCP server...")
        await self._publish_via_mcp()

        # ── Summary ──
        status = "success" if self.doc_result and self.email_result else "partial"
        print("\n" + "=" * 60)
        print(f"  Pipeline Complete! Status: {status.upper()}")
        print(f"  * Google Doc: {'[OK] Appended' if self.doc_result else '[FAIL] Failed'}")
        print(f"  * Gmail Draft: {'[OK] Created' if self.email_result else '[FAIL] Failed'}")
        print("=" * 60 + "\n")

        return {
            "status": status,
            "report": self.report.model_dump(),
            "doc_result": self.doc_result,
            "email_result": self.email_result,
        }

    def _load_data(self) -> list:
        """Load reviews from the Phase 1 cleaned JSON."""
        if not os.path.exists(self.data_path):
            raise FileNotFoundError(
                f"Review data not found at {self.data_path}. "
                "Run Phase 1 first to generate cleaned data."
            )

        with open(self.data_path, "r", encoding="utf-8") as f:
            reviews = json.load(f)

        if not reviews:
            raise ValueError("No reviews found in the data file.")

        return reviews

    def _analyze(self, reviews: list) -> FinalReport:
        """Run the Phase 2 Groq agent on the reviews."""
        agent = GrowwReviewAgent(api_key=self.groq_api_key)
        return agent.analyze_reviews(reviews, batch_size=150)

    async def _publish_via_mcp(self):
        """Connect to MCP server and publish the report + email draft."""
        # Format the report for Google Docs
        doc_content = format_doc_report(self.report)

        # Format the email summary
        doc_url = f"https://docs.google.com/document/d/{self.doc_id}/edit"
        email_data = format_email_summary(self.report, doc_url=doc_url)

        # Connect to MCP and execute tools
        async with GrowwMCPClient(sse_url=self.mcp_server_url) as client:
            print(f"   Connected to MCP server")

            # ── 3a: Append report to Google Doc ──
            print(f"   Appending report to Google Doc ({self.doc_id[:20]}...)...")
            try:
                result = await client.call_tool("append_doc", {
                    "doc_id": self.doc_id,
                    "content": doc_content,
                })
                
                if getattr(result, "isError", False):
                    error_msg = result.content[0].text if result.content else "Unknown error"
                    logger.error(f"MCP Server returned an error: {error_msg}")
                    print(f"   [FAIL] Document update failed: {error_msg}")
                    self.doc_result = None
                else:
                    self.doc_result = str(result)
                    print(f"   [OK] Document updated successfully")
            except Exception as e:
                logger.error(f"Failed to connect or append to Google Doc: {e}")
                print(f"   [FAIL] Document update network failure: {e}")
                self.doc_result = None

            # ── 3b: Create Gmail draft ──
            print(f"   Creating Gmail draft to {self.email_to}...")
            try:
                result = await client.call_tool("create_draft", {
                    "to": self.email_to,
                    "subject": email_data["subject"],
                    "body": email_data["body"],
                })
                
                if getattr(result, "isError", False):
                    error_msg = result.content[0].text if result.content else "Unknown error"
                    logger.error(f"MCP Server returned an error: {error_msg}")
                    print(f"   [FAIL] Email draft failed: {error_msg}")
                    self.email_result = None
                else:
                    self.email_result = str(result)
                    print(f"   [OK] Email draft created successfully")
            except Exception as e:
                logger.error(f"Failed to connect or create Gmail draft: {e}")
                print(f"   [FAIL] Email draft network failure: {e}")
                self.email_result = None


async def run_pipeline(
    doc_id: str,
    email_to: str,
    data_path: Optional[str] = None,
) -> dict:
    """
    Convenience function to run the full end-to-end pipeline.

    Args:
        doc_id: Google Document ID.
        email_to: Recipient email for the draft.
        data_path: Optional path to cleaned reviews JSON.

    Returns:
        Pipeline result dict.
    """
    orchestrator = PipelineOrchestrator(
        doc_id=doc_id,
        email_to=email_to,
        data_path=data_path,
    )
    return await orchestrator.run()
