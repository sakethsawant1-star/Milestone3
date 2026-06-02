# 🧠 Architecture & Business Decision Record (ADR)

This document tracks all major technical and business decisions made during the development of the Groww App Review Analyst.

## Decision 1: Adopting Model Context Protocol (MCP) over Raw APIs
*   **Date:** 2026-05-18
*   **Context:** We need to interact with Google Docs and Gmail. Historically, this meant integrating `google-api-python-client`, handling OAuth 2.0 flows, token refresh logic, and writing custom wrappers for the LLM to use.
*   **Decision:** We will exclusively use the **Google Docs MCP Server** and **Gmail MCP Server**.
*   **Rationale:** 
    *   Abstracts away API plumbing; the LLM natively understands MCP tool schemas.
    *   Security is decoupled: The MCP host manages credentials, keeping the agent pure and stateless.
    *   Future-proofing: If we want to switch to Notion or Slack later, we just swap the MCP server rather than rewriting our API integration layer.

## Decision 2: Local Stdio Connection for MCP Servers
*   **Date:** 2026-05-18
*   **Context:** The MCP specification allows clients to connect to servers via local Standard IO (`stdio`) or over the network using Server-Sent Events (`SSE`).
*   **Decision:** The primary deployment will utilize **local `stdio` subprocesses** to spin up the Google Docs and Gmail MCP servers alongside the agent.
*   **Rationale:** Simplifies local development and security. By running servers as child processes, we eliminate network latency, avoid exposing MCP ports to the public internet, and completely bypass internal network auth headaches.

## Decision 3: Pre-LLM PII Sanitization Layer
*   **Date:** 2026-05-18
*   **Context:** Frustrated users often include phone numbers, email addresses, or transaction IDs in public App Store reviews.
*   **Decision:** Implement a strict, regex-based PII redaction layer in Phase 1 that scrubs data *before* it is ever sent to the LLM.
*   **Rationale:** Data privacy compliance (e.g., GDPR, DPDP Act). Relying on the LLM to "ignore" PII is risky. Scrubbing it locally guarantees that no sensitive user data is transmitted to external API providers (like Google GenAI or OpenAI).

## Decision 4: Deterministic vs. ReAct Tool Orchestration
*   **Date:** 2026-05-18
*   **Context:** We need the agent to create a Google Doc, format text, and then draft an email. Should the agent autonomously decide the order of these operations (ReAct loop), or should it be hardcoded?
*   **Decision:** Implement a **Hybrid Sequential Pipeline**. The LLM performs the unstructured analysis autonomously, but the execution sequence of MCP tools (Analysis -> Create Doc -> Append Text -> Draft Email) is deterministically scripted in Python.
*   **Rationale:** Prevents "infinite loops" where an autonomous agent might get stuck trying to draft an email before creating the document, or failing to format correctly. Deterministic scripting guarantees a reliable, predictable pipeline for business use.

## Decision 5: Enforcing Pydantic Structured Outputs
*   **Date:** 2026-05-18
*   **Context:** The LLM must return exactly 3 quotes, exactly 3 action ideas, and a maximum of 5 themes. Parsing plain Markdown text to verify these constraints is fragile.
*   **Decision:** Use **Structured Outputs** (JSON schemas mapped to Python Pydantic models) for the Phase 2 thematic analysis.
*   **Rationale:** Guarantees absolute schema adherence. The evaluation scripts can programmatically assert `len(response.themes) <= 5` and `len(response.quotes) == 3` without writing complex regex parsers.

## Decision 6: Phase-Wise Evaluation Strategy (TDD)
*   **Date:** 2026-05-18
*   **Context:** AI systems can fail silently due to hallucinations or missed constraints. 
*   **Decision:** Every implementation phase must have an accompanying `eval_phaseX.py` script.
*   **Rationale:** Enforces Test-Driven Development (TDD) for AI. We cannot proceed to MCP integration (Phase 3) if the LLM cannot consistently adhere to the word count constraint (Phase 2). Exit criteria provide objective go/no-go gates.

## Decision 7: Max 5 Themes & 250-Word Limit
*   **Date:** 2026-05-18
*   **Context:** Stakeholders (Product, Support, Leadership) need a quick weekly pulse. Long, verbose reports are often ignored.
*   **Decision:** Hard constraints applied to the generated output: Maximum of 5 core themes, exactly 3 user quotes, exactly 3 action ideas, and a strict ≤ 250-word count overall.
*   **Rationale:** Forces the AI to prioritize the most critical issues (e.g., KYC failures, app crashes) rather than summarizing everything. Ensures high scannability for busy executives.

## Decision 8: Local CSV/JSON File Ingestion Strategy
*   **Date:** 2026-05-18
*   **Context:** Real-time web scraping of App Stores is unreliable and often blocked.
*   **Decision:** Rely on officially exported public review data (CSV/JSON) spanning the last 8-12 weeks.
*   **Rationale:** Ensures system stability and repeatable testing without being blocked by anti-bot measures. Product teams already have access to these raw exports via the Google Play Console / App Store Connect.
