"""
prompts.py — System & Task Prompts for Groq LLM Calls

Contains all prompt templates for the 2-pass analysis pipeline:
  - SYSTEM_PROMPT: Persona definition (Expert Product Analyst for Groww)
  - BATCH_ANALYSIS_PROMPT: Pass 1 — extract themes, quotes, ideas from a batch
  - SYNTHESIS_PROMPT: Pass 2 — merge batch outputs into final consolidated report

All prompts instruct the LLM to output structured JSON matching the Pydantic
schemas defined in schemas.py.
"""

# ---------------------------------------------------------------------------
# System Prompt — Used in ALL Groq calls
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = """You are an Expert Product Analyst for Groww, India's leading stock trading and mutual fund investment app.

Your role:
- Analyze user reviews from the Google Play Store and Apple App Store.
- Identify recurring complaint themes and actionable product insights.
- Extract real user quotes that best represent each theme.
- Generate concrete, implementable product improvement ideas.

Rules:
- The reviews may be in English, Hindi, Hinglish (Hindi-English mix), or Marathi. Treat ALL languages equally during analysis, but produce your final output ONLY in English.
- Focus on actionable, specific feedback — not generic praise or rants.
- Be data-driven: ground every theme and idea in actual review evidence.
- You MUST respond with valid JSON only. No markdown, no explanations outside JSON."""

# ---------------------------------------------------------------------------
# Pass 1: Batch Analysis Prompt
# ---------------------------------------------------------------------------
BATCH_ANALYSIS_PROMPT = """Analyze the following batch of {review_count} Groww app user reviews.

YOUR TASK:
1. **Themes**: Identify up to 5 recurring complaint/feedback themes in this batch. For each theme, provide:
   - "name": A short label (e.g., "KYC Delays", "High Brokerage Charges")
   - "description": 1-2 sentence summary
   - "review_count": How many reviews in this batch relate to this theme
   - "sentiment": "negative", "mixed", or "positive"

2. **Quotes**: Extract 3-5 real, verbatim user quotes that best represent the key themes. For each quote:
   - "text": The exact quote from the review (do NOT paraphrase)
   - "rating": The star rating (1-5) of that review
   - "theme": Which theme this quote belongs to

3. **Action Ideas**: Suggest 2-3 actionable product improvement ideas based on this batch. For each:
   - "title": Short title
   - "description": 1-2 sentence explanation of what to do
   - "target_theme": Which theme this addresses

4. **Summary**: Write a brief 2-3 sentence summary of this batch's key findings.

5. **Review Count**: Set "review_count" to {review_count}.

RESPOND WITH THIS EXACT JSON STRUCTURE:
{{
  "themes": [...],
  "quotes": [...],
  "action_ideas": [...],
  "review_count": {review_count},
  "summary": "..."
}}

--- REVIEWS ---
{reviews_json}"""

# ---------------------------------------------------------------------------
# Pass 2: Synthesis Prompt
# ---------------------------------------------------------------------------
SYNTHESIS_PROMPT = """You are merging {batch_count} partial analysis results into ONE final consolidated report.

Each partial result contains themes, quotes, and action ideas from a different batch of Groww app reviews (total: {total_reviews} reviews analyzed).

YOUR TASK — Produce a FINAL consolidated report:

1. **Themes**: Merge overlapping themes across batches into at most 5 final themes. Combine similar themes (e.g., "KYC Issues" from Batch A and "KYC Delays" from Batch B become one). Sum their review counts. For each:
   - "name", "description", "review_count", "sentiment"

2. **Quotes**: Select the 3 BEST, most representative quotes from all batches combined. Pick quotes that:
   - Span different themes
   - Are specific and vivid (not generic complaints)
   - Each: "text", "rating", "theme"

3. **Action Ideas**: Select or synthesize the 3 BEST actionable product ideas. Prioritize ideas that address the highest-volume themes. For each:
   - "title", "description", "target_theme"

4. **Text Body**: Write a cohesive 200-250 word executive summary that a Groww Product Manager would read. Structure:
   - Opening: Overall sentiment snapshot (e.g., "Across X reviews from the last N weeks...")
   - Middle: Top 3 pain points with evidence
   - Closing: 1-sentence recommendation

   STRICT LIMIT: Maximum 250 words for text_body.

RESPOND WITH THIS EXACT JSON STRUCTURE:
{{
  "themes": [...],
  "quotes": [...],
  "action_ideas": [...],
  "text_body": "..."
}}

--- PARTIAL RESULTS ---
{partial_results_json}"""


def format_reviews_for_prompt(reviews: list) -> str:
    """
    Format a batch of reviews into a compact JSON string for the prompt.
    Only includes rating and text fields to minimize token usage.
    """
    compact = []
    for r in reviews:
        compact.append({
            "rating": r.get("rating", 0),
            "text": r.get("text", ""),
        })

    import json
    return json.dumps(compact, ensure_ascii=False, separators=(",", ":"))


def build_batch_prompt(reviews: list) -> str:
    """Build the complete batch analysis prompt with reviews embedded."""
    reviews_json = format_reviews_for_prompt(reviews)
    return BATCH_ANALYSIS_PROMPT.format(
        review_count=len(reviews),
        reviews_json=reviews_json,
    )


def build_synthesis_prompt(partial_results: list, total_reviews: int) -> str:
    """Build the complete synthesis prompt with partial results embedded."""
    import json
    partial_json = json.dumps(partial_results, ensure_ascii=False, indent=2)
    return SYNTHESIS_PROMPT.format(
        batch_count=len(partial_results),
        total_reviews=total_reviews,
        partial_results_json=partial_json,
    )
