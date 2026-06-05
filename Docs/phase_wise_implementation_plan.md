# 📅 Phase-Wise Implementation Plan (Detailed)

This document outlines the step-by-step plan to implement the Groww App Review Analyst using the Model Context Protocol (MCP). 

**Testing Strategy:** Test-Driven Development (TDD) approach. For each phase, a dedicated evaluation file (`eval_phaseX.py`) will be created. A phase is only marked "Complete" when its respective evaluation script runs successfully against edge cases.

---

## Phase 1: Data Ingestion & PII Sanitization
**Objective:** Set up the foundational data pipeline to read, clean, structure, and anonymize public mobile reviews.
*   **Detailed Tasks:**
    *   Create a mocked dataset of ~50 App Store / Play Store reviews representing Groww issues (KYC, UPI, bugs).
    *   Build `ingest.py` with functions to load CSV/JSON files.
    *   Implement `sanitizer.py` utilizing regex to redact emails, 10-digit phone numbers, and common PAN card or Bank Account patterns.
    *   Filter out non-actionable reviews (e.g., "Good app", "Nice").
*   **Evaluation (`eval_phase1.py`):** 
    *   *Mock Data Input:* A test file with injected fake PII and dates spanning 2 years.
    *   *Assertions/Exit Criteria:* 
        *   Fails if reviews older than 12 weeks are not filtered out.
        *   Asserts that string matching `@gmail.com` or `9876543210` are scrubbed and replaced with `[REDACTED]`.
        *   Verifies the final returned list matches the required schema `[{rating, title, text, date}]`.

## Phase 2: Agent Design & Prompt Engineering
**Objective:** Develop the core LLM logic to categorize themes, extract quotes, and generate actionable ideas securely using **Groq**, while staying within strict rate limits.

### Groq Rate Limits (`llama-3.3-70b-versatile`)
| Limit | Value |
|---|---|
| Requests / minute | 30 |
| Requests / day | 1,000 |
| Tokens / minute | **12,000** (tightest constraint) |
| Tokens / day | 100,000 |

*   **Detailed Tasks:**
    *   **LLM Client Setup:**
        *   Install `groq` Python SDK (`pip install groq`).
        *   Configure the Groq client with `GROQ_API_KEY` from `.env`.
        *   Model: `llama-3.3-70b-versatile`.
    *   **Data Pre-Processing — `preprocessor.py` (Zero LLM Calls):**
        *   Filter the Phase 1 output (~1,663 reviews, ~38K tokens) down to **~400 actionable reviews (~15K tokens)** before any Groq call:
            *   **Low-signal filter:** Remove reviews < 5 words or matching generic patterns (`"good app"`, `"nice"`, `"best"`, etc.) — eliminates ~40% noise.
            *   **Spam/gibberish filter:** Remove all-caps rants, promotional content, nonsensical text (>50% uppercase + no actionable keywords).
            *   **Rating-stratified selection:** Keep **all** 1–2 star reviews. From 3–5 star, keep only those with ≥ 10 words (substantive feedback).
            *   **Language handling:** Dataset contains English, Hindi, Hinglish, and Marathi — system prompt instructs LLM to analyze all but output in English.
    *   **Rate Limiter — `rate_limiter.py`:**
        *   Pre-flight token counting (char/4 heuristic) before each call.
        *   Enforced **≥ 60-second spacing** between consecutive Groq calls.
        *   Exponential backoff on `429 Too Many Requests` (max 3 retries).
        *   Daily token budget tracker — aborts if cumulative usage approaches 90K.
    *   **Batched LLM Call Plan (3 Calls Total, ~3 min runtime):**
        *   **Pass 1 — Batch Analysis (2 calls, 60s apart):**
            *   Batch A: Reviews 1–200 → Groq → `partial_themes_A.json`
            *   Batch B: Reviews 201–400 → Groq → `partial_themes_B.json`
            *   Each batch: ~8,100 input tokens (7,600 reviews + 500 prompt) + ~1,500 output = **~9,600 tokens** (within 12K TPM).
        *   **Pass 2 — Synthesis (1 call, 60s after Pass 1):**
            *   Merge `partial_themes_A` + `partial_themes_B` → Groq → `final_report.json`
            *   Input: ~3,500 tokens (2 partial JSONs + prompt) + ~1,500 output = **~5,000 tokens**.
        *   **Total per run: ~24K tokens, 3 requests, ~3 minutes.**
        *   Allows **4 full runs/day** within 100K TPD and 1K RPD limits.
    *   **Prompt Engineering:**
        *   Draft system prompts detailing the persona: "Expert Product Analyst for Groww".
        *   Use Groq's `response_format` parameter with `{"type": "json_object"}` for structured JSON outputs.
        *   Batch prompt instructs: extract themes (≤5), top quotes, and ideas from this batch only.
        *   Synthesis prompt instructs: merge batch outputs into final consolidated report.
    *   **Output Schema:**
        *   Implement Pydantic models to guarantee the LLM returns exact fields: `themes` (list), `quotes` (list), `action_ideas` (list).
        *   Enforce a strict 250-word limit constraint programmatically or via prompt tuning.
*   **Evaluation (`eval_phase2.py`):** 
    *   *Mock Data Input:* The sanitized output from Phase 1.
    *   *Assertions/Exit Criteria:* 
        *   `len(output.themes) <= 5`
        *   `len(output.quotes) == 3`
        *   `len(output.action_ideas) == 3`
        *   `len(output.text_body.split()) <= 250`
        *   Total Groq API calls per run ≤ 4.
        *   No single call exceeds 10,000 tokens (input + output).
        *   Script raises an exception if any of these conditions fail over 5 consecutive test runs.

## Phase 3: MCP Server Setup & Client Integration
**Objective:** Install, configure, and connect to the Google Docs and Gmail MCP servers.
*   **Detailed Tasks:**
    *   Determine the deployment of the MCP servers (using community npx servers or building simple Python MCP servers).
    *   Set up Google Cloud Console OAuth 2.0 Desktop credentials, granting Docs and Gmail scopes.
    *   Create `mcp_client.py` using the official Python MCP SDK.
    *   Establish `stdio` connections to both MCP servers and successfully invoke `tools/list`.
*   **Evaluation (`eval_phase3.py`):** 
    *   *Mock Data Input:* Hardcoded dummy tool parameters.
    *   *Assertions/Exit Criteria:* 
        *   The client successfully connects and retrieves a list of tools including `create_document` and `create_draft`.
        *   A mock execution using `call_tool` to create a "Test Document" succeeds, returning a valid Document ID without crashing.

## Phase 4: End-to-End Workflow & Agentic Execution
**Objective:** Stitch the data, LLM reasoning, and MCP tool execution into a single, fully autonomous pipeline.
*   **Detailed Tasks:**
    *   Bind the fetched MCP tools to the LLM configuration (passing the JSON schemas to the LLM).
    *   Create the main loop:
        1. Read Data.
        2. Analyze (Phase 2).
        3. Agent invokes `create_document` -> LLM receives Doc ID.
        4. Agent invokes `append_text` with the formatted 250-word markdown.
        5. Agent invokes `create_draft` in Gmail linking the Google Doc.
    *   Handle LLM tool call loops (parsing the LLM tool request, executing via MCP client, and returning the result to the LLM).
*   **Evaluation (`eval_phase4_e2e.py`):** 
    *   *Mock Data Input:* Full raw review dataset.
    *   *Assertions/Exit Criteria:* 
        *   A single `python main.py` execution results in a newly created Google Doc with correct formatting.
        *   A new draft email appears in the target inbox linking to the exact Google Doc.
        *   Requires zero manual intervention between ingestion and email drafting.

## Phase 5: Hardening, Error Handling & Handoff
**Objective:** Finalize the project, add telemetry, and ensure robust error handling for edge cases.
*   **Detailed Tasks:**
    *   Add comprehensive `logging` (DEBUG, INFO, ERROR).
    *   Handle Google API rate limits or MCP connection drops (e.g., retries on `stdio` timeout).
    *   Handle **Groq rate limit errors** (`429`) with exponential backoff and daily token budget enforcement.
    *   Handle LLM hallucinations (e.g., trying to call a tool that doesn't exist).
    *   Log per-call token usage and cumulative daily totals for Groq budget monitoring.
    *   Write final run books.
*   **Evaluation (`eval_phase5.py`):** 
    *   *Mock Data Input:* Malformed data, forced network timeouts.
    *   *Assertions/Exit Criteria:* 
        *   The system fails gracefully with readable error logs rather than unhandled tracebacks.
        *   If the MCP server is unreachable, the system reports "Docs MCP Server offline" instead of generic tool failures.
        *   If Groq daily token limit is approached, the system aborts with "Daily Groq token budget exhausted" instead of hitting a 429.

## Phase 6: Automated Weekly Scheduler (GitHub Actions)
**Objective:** Automate the entire pipeline to run weekly with zero manual intervention, scraping fresh reviews from the Google Play Store.
*   **Detailed Tasks:**
    *   **Review Scraper (`phase1_ingestion/scraper.py`):**
        *   Use `google-play-scraper` Python library to fetch the latest Groww app reviews from the Play Store.
        *   Normalize scraped data to the Phase 1 schema: `{review_id, rating, title, text, date}`.
        *   Save output as timestamped JSON (e.g., `groww_reviews_20260605.json`).
        *   Default fetch: 500 reviews per run (configurable).
    *   **Non-Interactive Runner (`scheduled_run.py`):**
        *   Reads all configuration from environment variables (no `input()` prompts).
        *   Required env vars: `GROQ_API_KEY`, `MCP_SERVER_URL`, `TARGET_DOC_ID`, `TARGET_EMAIL`.
        *   Pipeline: Scrape -> Ingest/Sanitize -> Analyze (Groq) -> Publish (MCP/Railway).
        *   Graceful fallback: if scraping fails, uses existing cleaned data.
    *   **GitHub Actions Workflow (`.github/workflows/weekly_review.yml`):**
        *   **Cron Schedule:** Every Monday at 9:00 AM IST (`30 3 * * 1` UTC).
        *   **Manual Trigger:** `workflow_dispatch` with configurable `review_count` and `skip_scrape` inputs.
        *   **Secrets Required:** `GROQ_API_KEY`, `MCP_SERVER_URL`, `TARGET_DOC_ID`, `TARGET_EMAIL`, `GOOGLE_TOKEN_JSON`, `GOOGLE_CREDENTIALS_JSON`.
        *   **Artifact Upload:** Saves scraped review data as a GitHub Actions artifact (30-day retention).
*   **Evaluation:**
    *   Manual trigger of the GitHub Actions workflow from the Actions tab.
    *   *Assertions/Exit Criteria:*
        *   Workflow completes without errors.
        *   Google Doc is updated with a new timestamped report.
        *   Gmail draft is created with the summary email.
        *   Review data artifact is uploaded successfully.

## Phase 7: Web Front-End (Next.js + Vercel)
**Objective:** Build a beautiful, interactive web dashboard for the Groww Review Analyst, deployed on Vercel.
*   **Design Inspiration:** Google Stitch design language.
*   **Detailed Tasks:**
    *   **Dashboard Page:**
        *   Display the latest analysis report (themes, quotes, action ideas).
        *   Visual charts for theme distribution and sentiment breakdown.
        *   Timeline view of past weekly reports.
    *   **Manual Trigger Page:**
        *   Upload a custom CSV of reviews.
        *   Configure Google Doc ID and email address.
        *   "Run Analysis" button to trigger the pipeline.
        *   Real-time progress indicators.
    *   **Settings Page:**
        *   Configure schedule frequency.
        *   Manage API keys and MCP server URL.
    *   **API Backend:**
        *   Next.js API routes that wrap the Python pipeline.
        *   Or: call the Railway MCP server directly from the front-end.
*   **Deployment:** Vercel (auto-deploy from GitHub `main` branch).
*   **Evaluation:**
    *   *Assertions/Exit Criteria:*
        *   Dashboard loads and displays the latest report data.
        *   Manual trigger successfully runs the pipeline and shows results.
        *   Responsive design works on desktop and mobile.
