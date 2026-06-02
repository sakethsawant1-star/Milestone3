"""
agent.py — Core Groq LLM Agent for Phase 2

Implements the 2-pass batched analysis pipeline:
  Pass 1: Batch Analysis (2+ calls, 60s apart) → partial_themes per batch
  Pass 2: Synthesis (1 call) → final consolidated report

Uses:
  - preprocessor.py for data reduction
  - rate_limiter.py for Groq API rate management
  - prompts.py for prompt templates
  - schemas.py for output validation

Total per run: ~24K tokens, 3 requests, ~3 minutes.
"""

import os
import json
import logging
from typing import List, Dict, Optional
from dotenv import load_dotenv

from phase2_agent.preprocessor import run_preprocessing
from phase2_agent.rate_limiter import GroqRateLimiter, TokenBudgetExhausted, RateLimitExceeded
from phase2_agent.prompts import (
    SYSTEM_PROMPT,
    build_batch_prompt,
    build_synthesis_prompt,
)
from phase2_agent.schemas import BatchAnalysisResult, FinalReport

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
DEFAULT_MODEL = "llama-3.3-70b-versatile"
ESTIMATED_OUTPUT_TOKENS = 1500  # Conservative estimate for output tokens


class GrowwReviewAgent:
    """
    The Groww App Review Analyst agent.

    Orchestrates the full Phase 2 pipeline:
      1. Pre-process reviews (zero LLM calls)
      2. Batch analysis via Groq (Pass 1)
      3. Synthesis via Groq (Pass 2)
      4. Validate output against Pydantic schemas
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = DEFAULT_MODEL,
        rate_limiter: Optional[GroqRateLimiter] = None,
    ):
        """
        Initialize the agent.

        Args:
            api_key: Groq API key. If None, reads from GROQ_API_KEY env var.
            model: Groq model name.
            rate_limiter: Optional custom rate limiter instance.
        """
        load_dotenv()

        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        if not self.api_key:
            raise ValueError(
                "GROQ_API_KEY not found. Set it in .env or pass api_key parameter."
            )

        self.model = model
        self.rate_limiter = rate_limiter or GroqRateLimiter()

        # Import groq here to fail fast if not installed
        try:
            from groq import Groq
            self._client = Groq(api_key=self.api_key)
        except ImportError:
            raise ImportError(
                "groq package not installed. Run: pip install groq"
            )

        # Track calls for eval assertions
        self._call_count = 0
        self._total_tokens = 0

    def _call_groq(self, messages: list) -> dict:
        """
        Make a single rate-limited Groq API call.

        Args:
            messages: List of message dicts (role, content).

        Returns:
            Parsed JSON dict from the LLM response.
        """
        # Pre-flight: estimate tokens and check budget
        estimated_input = self.rate_limiter.estimate_call_tokens(messages)
        self.rate_limiter.check_budget(estimated_input, ESTIMATED_OUTPUT_TOKENS)

        # Wait for rate limit spacing
        self.rate_limiter.wait_for_spacing()

        # Make the API call with retry logic
        def _api_call():
            return self._client.chat.completions.create(
                model=self.model,
                messages=messages,
                response_format={"type": "json_object"},
                temperature=0.3,  # Low temp for consistent structured output
                max_tokens=2000,
            )

        response = self.rate_limiter.execute_with_retry(_api_call)

        # Record actual usage
        usage = response.usage
        self.rate_limiter.record_call(
            input_tokens=usage.prompt_tokens,
            output_tokens=usage.completion_tokens,
            model=self.model,
        )
        self._call_count += 1
        self._total_tokens += usage.total_tokens

        # Parse response
        content = response.choices[0].message.content
        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Groq JSON response: {e}")
            logger.error(f"Raw response: {content[:500]}")
            raise ValueError(f"Groq returned invalid JSON: {e}")

    def _analyze_batch(self, batch: List[Dict], batch_index: int) -> dict:
        """
        Pass 1: Analyze a single batch of reviews.

        Args:
            batch: List of review dicts.
            batch_index: Batch number (for logging).

        Returns:
            Validated BatchAnalysisResult as a dict.
        """
        print(f"\n  [Pass 1] Analyzing Batch {batch_index + 1} ({len(batch)} reviews)...")

        user_prompt = build_batch_prompt(batch)
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]

        raw_result = self._call_groq(messages)

        # Validate against schema
        try:
            validated = BatchAnalysisResult(**raw_result)
            print(f"  [Pass 1] Batch {batch_index + 1} ✓ — "
                  f"{len(validated.themes)} themes, "
                  f"{len(validated.quotes)} quotes, "
                  f"{len(validated.action_ideas)} ideas")
            return validated.model_dump()
        except Exception as e:
            logger.warning(f"Batch {batch_index + 1} schema validation warning: {e}")
            # Return raw result if validation fails (synthesis will still work)
            print(f"  [Pass 1] Batch {batch_index + 1} ⚠ — partial validation: {e}")
            return raw_result

    def _synthesize(self, partial_results: list, total_reviews: int) -> FinalReport:
        """
        Pass 2: Merge partial batch results into final report.

        Args:
            partial_results: List of batch analysis result dicts.
            total_reviews: Total number of reviews analyzed across all batches.

        Returns:
            Validated FinalReport.
        """
        print(f"\n  [Pass 2] Synthesizing {len(partial_results)} batch results...")

        user_prompt = build_synthesis_prompt(partial_results, total_reviews)
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]

        raw_result = self._call_groq(messages)

        # Validate against final schema
        try:
            report = FinalReport(**raw_result)
            print(f"  [Pass 2] Synthesis ✓ — "
                  f"{len(report.themes)} themes, "
                  f"{len(report.quotes)} quotes, "
                  f"{len(report.action_ideas)} ideas, "
                  f"{len(report.text_body.split())} words")
            return report
        except Exception as e:
            logger.error(f"Synthesis schema validation failed: {e}")
            raise ValueError(
                f"Final report failed schema validation: {e}\n"
                f"Raw result: {json.dumps(raw_result, indent=2)[:1000]}"
            )

    def analyze_reviews(
        self,
        reviews: List[Dict],
        batch_size: int = 200,
    ) -> FinalReport:
        """
        Full Phase 2 pipeline: Pre-process → Batch Analysis → Synthesis.

        Args:
            reviews: Phase 1 sanitized review list.
            batch_size: Max reviews per batch (default 200 for 12K TPM safety).

        Returns:
            FinalReport with themes, quotes, action_ideas, and text_body.
        """
        print(f"\n{'='*60}")
        print(f"  Phase 2: Groww Review Analysis Agent")
        print(f"{'='*60}")

        # Reset call tracking
        self._call_count = 0
        self._total_tokens = 0

        # Step 1: Pre-processing (zero LLM calls)
        batches, preprocess_stats = run_preprocessing(reviews, batch_size)

        if not batches:
            raise ValueError("No actionable reviews after pre-processing.")

        total_reviews = preprocess_stats["output_count"]

        # Step 2: Pass 1 — Batch Analysis
        print(f"\n{'─'*40}")
        print(f"  Pass 1: Batch Analysis ({len(batches)} batches)")
        print(f"{'─'*40}")

        partial_results = []
        for i, batch in enumerate(batches):
            result = self._analyze_batch(batch, i)
            partial_results.append(result)

        # Step 3: Pass 2 — Synthesis
        print(f"\n{'─'*40}")
        print(f"  Pass 2: Synthesis")
        print(f"{'─'*40}")

        report = self._synthesize(partial_results, total_reviews)

        # Summary
        print(f"\n{'='*60}")
        print(f"  Phase 2 Complete!")
        print(f"  • LLM calls: {self._call_count}")
        print(f"  • Total tokens: {self._total_tokens}")
        print(f"  • Themes: {len(report.themes)}")
        print(f"  • Quotes: {len(report.quotes)}")
        print(f"  • Ideas: {len(report.action_ideas)}")
        print(f"  • Report length: {len(report.text_body.split())} words")
        usage = self.rate_limiter.daily_usage_summary
        print(f"  • Daily budget: {usage['tokens_used']}/{usage['tokens_budget']} "
              f"({usage['utilization_pct']}%)")
        print(f"{'='*60}\n")

        return report

    @property
    def call_count(self) -> int:
        """Number of Groq API calls made in the last run."""
        return self._call_count

    @property
    def total_tokens(self) -> int:
        """Total tokens used in the last run."""
        return self._total_tokens


def run_agent(
    reviews: List[Dict],
    api_key: Optional[str] = None,
    model: str = DEFAULT_MODEL,
    batch_size: int = 200,
) -> FinalReport:
    """
    Convenience function to run the full Phase 2 pipeline.

    Args:
        reviews: Phase 1 sanitized review list.
        api_key: Groq API key (optional, reads from .env).
        model: Groq model name.
        batch_size: Max reviews per batch.

    Returns:
        FinalReport with themes, quotes, action_ideas, and text_body.
    """
    agent = GrowwReviewAgent(api_key=api_key, model=model)
    return agent.analyze_reviews(reviews, batch_size=batch_size)
