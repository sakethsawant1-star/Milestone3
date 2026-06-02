"""
sanitizer.py — PII Redaction Engine for Groww App Reviews

This module implements a multi-pattern regex pipeline to scrub Personally
Identifiable Information (PII) from raw review text BEFORE it reaches the LLM.

Covered patterns:
  - Email addresses (e.g. user@gmail.com)
  - Indian mobile numbers (10-digit, with optional +91 / 0 prefix)
  - PAN card numbers (e.g. ABCDE1234F)
  - Aadhaar numbers (12 digits, with optional dashes)
  - Bank account numbers (8-18 digit sequences preceded by context keywords)
  - UPI IDs (e.g. user@oksbi)
  - Generic user/order/ticket IDs (e.g. GRW-USR-44821, ORD-445566, TKT-90876)

Design Decision (see decision.md #3):
  PII is stripped at the data layer, not at the LLM layer, to guarantee
  zero sensitive data transmission to external API providers.
"""

import re
from typing import List, Dict

# ---------------------------------------------------------------------------
# Redaction tag
# ---------------------------------------------------------------------------
REDACTED = "[REDACTED]"

# ---------------------------------------------------------------------------
# Compiled regex patterns (order matters — more specific patterns first)
# ---------------------------------------------------------------------------

# Email addresses: user@domain.tld
_EMAIL_RE = re.compile(
    r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}",
    re.IGNORECASE,
)

# UPI IDs: user@bankhandle (e.g. myupi@oksbi, name@ybl)
_UPI_RE = re.compile(
    r"[a-zA-Z0-9.\-_]+@[a-zA-Z]{2,10}\b",
    re.IGNORECASE,
)

# Indian PAN: 5 letters + 4 digits + 1 letter (e.g. ABCDE1234F)
_PAN_RE = re.compile(
    r"\b[A-Z]{5}[0-9]{4}[A-Z]\b",
)

# Aadhaar: 12 digits optionally separated by dashes/spaces (e.g. 1234-5678-9012)
_AADHAAR_RE = re.compile(
    r"\b\d{4}[\s\-]?\d{4}[\s\-]?\d{4}\b",
)

# Indian mobile numbers: optional +91/0 prefix, then 10 digits
# Handles: 9876543210, +91-9123456789, 091 9876543210
_PHONE_RE = re.compile(
    r"(?:\+91[\s\-]?|0)?[6-9]\d{9}\b",
)

# Bank account numbers: 8-18 digit sequences near context words
# Context: "account", "acc", "a/c", "a]c" followed by optional punctuation then digits
_BANK_ACCOUNT_RE = re.compile(
    r"(?:account|acc|a/c|a\]c)[\s:.\-#]*(\d{8,18})\b",
    re.IGNORECASE,
)

# Generic platform IDs: GRW-USR-12345, ORD-445566, TKT-90876, USR-78654
_PLATFORM_ID_RE = re.compile(
    r"\b(?:GRW-)?(?:USR|ORD|TKT|ACC)[\-]?\d{4,10}\b",
    re.IGNORECASE,
)

# Standalone long digit sequences (8-18 digits) that may be account numbers
# Applied last to catch remaining numeric PII without over-matching ratings/amounts
_LONG_DIGITS_RE = re.compile(
    r"\b\d{10,18}\b",
)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def sanitize_text(text: str) -> str:
    """
    Apply all PII redaction patterns to a single review text string.

    Args:
        text: Raw review text that may contain PII.

    Returns:
        Sanitized text with all PII replaced by [REDACTED].
    """
    if not text or not isinstance(text, str):
        return text

    # Order: specific patterns first, then generic catch-all
    # 1. Emails (before UPI, since emails also match UPI pattern)
    text = _EMAIL_RE.sub(REDACTED, text)
    # 2. UPI IDs (after emails are already redacted)
    text = _UPI_RE.sub(REDACTED, text)
    # 3. PAN card numbers
    text = _PAN_RE.sub(REDACTED, text)
    # 4. Aadhaar numbers
    text = _AADHAAR_RE.sub(REDACTED, text)
    # 5. Phone numbers
    text = _PHONE_RE.sub(REDACTED, text)
    # 6. Bank accounts (contextual)
    text = _BANK_ACCOUNT_RE.sub(
        lambda m: m.group(0).replace(m.group(1), REDACTED), text
    )
    # 7. Platform IDs
    text = _PLATFORM_ID_RE.sub(REDACTED, text)
    # 8. Remaining long digit sequences (catch-all)
    text = _LONG_DIGITS_RE.sub(REDACTED, text)

    # Collapse multiple consecutive [REDACTED] tags into one
    text = re.sub(r"(\[REDACTED\]\s*){2,}", REDACTED + " ", text)

    return text.strip()


def sanitize_reviews(reviews: List[Dict]) -> List[Dict]:
    """
    Apply PII sanitization across all text fields in a list of review dicts.

    Sanitizes both 'title' and 'text' fields.

    Args:
        reviews: List of review dicts, each with keys: review_id, rating,
                 title, text, date.

    Returns:
        A new list of review dicts with sanitized title and text fields.
    """
    sanitized = []
    for review in reviews:
        sanitized_review = dict(review)  # shallow copy
        sanitized_review["title"] = sanitize_text(review.get("title", ""))
        sanitized_review["text"] = sanitize_text(review.get("text", ""))
        sanitized.append(sanitized_review)
    return sanitized
