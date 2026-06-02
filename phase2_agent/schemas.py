"""
schemas.py — Pydantic Output Models for Phase 2 LLM Responses

Defines strict schemas that the Groq LLM must conform to:
  - BatchAnalysisResult: partial output from each batch analysis call
  - FinalReport: the merged synthesis output (≤5 themes, 3 quotes, 3 ideas, ≤250 words)

These models are used to validate JSON responses from Groq before further processing.
"""

from typing import List
from pydantic import BaseModel, Field, field_validator


class Theme(BaseModel):
    """A single user-complaint or feedback theme."""
    name: str = Field(..., description="Short theme label, e.g. 'KYC Delays'")
    description: str = Field(..., description="1-2 sentence summary of the theme")
    review_count: int = Field(..., ge=0, description="Number of reviews in this theme")
    sentiment: str = Field(
        ..., description="Overall sentiment: 'negative', 'mixed', or 'positive'"
    )


class Quote(BaseModel):
    """A real user quote extracted verbatim from the reviews."""
    text: str = Field(..., description="Exact quote from a user review")
    rating: int = Field(..., ge=1, le=5, description="Star rating of the review")
    theme: str = Field(..., description="Theme this quote belongs to")


class ActionIdea(BaseModel):
    """An actionable product improvement idea derived from the reviews."""
    title: str = Field(..., description="Short title for the idea")
    description: str = Field(..., description="1-2 sentence explanation of what to do")
    target_theme: str = Field(..., description="Theme this idea addresses")


class BatchAnalysisResult(BaseModel):
    """
    Partial analysis result from a single batch of reviews.
    Pass 1 output — later merged in the synthesis step.
    """
    themes: List[Theme] = Field(
        ..., max_length=5, description="Up to 5 themes found in this batch"
    )
    quotes: List[Quote] = Field(
        ..., description="Top 3-5 representative quotes from this batch"
    )
    action_ideas: List[ActionIdea] = Field(
        ..., description="2-3 actionable product ideas from this batch"
    )
    review_count: int = Field(..., ge=0, description="Total reviews analyzed in batch")
    summary: str = Field(
        ..., description="Brief 2-3 sentence summary of this batch's findings"
    )

    @field_validator("themes")
    @classmethod
    def max_five_themes(cls, v):
        if len(v) > 5:
            raise ValueError(f"Maximum 5 themes allowed, got {len(v)}")
        return v


class FinalReport(BaseModel):
    """
    The consolidated output from the synthesis pass.
    This is the final deliverable sent to Google Docs.

    Constraints:
      - themes: ≤ 5
      - quotes: exactly 3
      - action_ideas: exactly 3
      - text_body: ≤ 250 words
    """
    themes: List[Theme] = Field(
        ..., max_length=5, description="Top 5 consolidated themes across all batches"
    )
    quotes: List[Quote] = Field(
        ..., min_length=3, max_length=3, description="Exactly 3 representative quotes"
    )
    action_ideas: List[ActionIdea] = Field(
        ..., min_length=3, max_length=3,
        description="Exactly 3 actionable product improvement ideas"
    )
    text_body: str = Field(
        ..., description="Full report narrative, maximum 250 words"
    )

    @field_validator("themes")
    @classmethod
    def max_five_themes(cls, v):
        if len(v) > 5:
            raise ValueError(f"Maximum 5 themes allowed, got {len(v)}")
        return v

    @field_validator("text_body")
    @classmethod
    def max_250_words(cls, v):
        word_count = len(v.split())
        if word_count > 250:
            raise ValueError(
                f"text_body must be ≤ 250 words, got {word_count}"
            )
        return v
