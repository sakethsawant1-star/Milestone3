"""
main.py — Single entry-point for the Groww App Review Analyst.

Usage:
    python main.py

Requires the following environment variables (in .env):
    - GROQ_API_KEY: Groq Cloud API key
    - MCP_SERVER_URL: Railway MCP server URL (SSE endpoint)

Also requires command-line input for:
    - Google Document ID
    - Recipient email address
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from phase4_e2e.orchestrator import run_pipeline


def main():
    print("\n" + "=" * 60)
    print("  [ GROWW APP REVIEW ANALYST ]")
    print("  Autonomous Review -> Report -> Email Pipeline")
    print("=" * 60)

    # Validate environment
    if not os.environ.get("GROQ_API_KEY"):
        print("\n[Error] GROQ_API_KEY not set in .env")
        sys.exit(1)

    if not os.environ.get("MCP_SERVER_URL"):
        print("\n[Warning] MCP_SERVER_URL not set. Using local stdio mode.")

    # Get user inputs
    doc_id = input("\nEnter Google Document ID: ").strip()
    if not doc_id:
        print("[Error] Document ID is required.")
        sys.exit(1)

    email_to = input("Enter recipient email address: ").strip()
    if not email_to:
        print("[Error] Email address is required.")
        sys.exit(1)

    # Run the pipeline
    print(f"\n[ Starting pipeline... ]")
    print(f"   Doc ID: {doc_id}")
    print(f"   Email: {email_to}")

    result = asyncio.run(run_pipeline(doc_id=doc_id, email_to=email_to))

    if result["status"] == "success":
        print("\n[SUCCESS] Pipeline completed successfully!")
        print(f"   Check your Google Doc: https://docs.google.com/document/d/{doc_id}/edit")
        print(f"   Check your Gmail drafts for the summary email.")
    else:
        print("\n[WARNING] Pipeline completed with some issues. Check the logs above.")

    return result


if __name__ == "__main__":
    main()
