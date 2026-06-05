"""
report_formatter.py — Formats the Phase 2 FinalReport into publishable content.

Produces:
  1. A formatted text string for appending to a Google Doc.
  2. An email summary string for drafting in Gmail.
"""

from datetime import datetime
from phase2_agent.schemas import FinalReport


def format_doc_report(report: FinalReport) -> str:
    """
    Formats the FinalReport into a clean, readable document body
    suitable for appending to a Google Doc.

    Args:
        report: Validated FinalReport from Phase 2.

    Returns:
        Formatted string with sections for themes, quotes, ideas, and narrative.
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = []

    lines.append(f"{'=' * 50}")
    lines.append(f"  GROWW APP REVIEW ANALYSIS REPORT")
    lines.append(f"  Generated: {timestamp}")
    lines.append(f"{'=' * 50}")
    lines.append("")

    # --- Themes ---
    lines.append("THEMES IDENTIFIED")
    lines.append("-" * 30)
    for i, theme in enumerate(report.themes, 1):
        lines.append(f"  {i}. {theme.name} ({theme.sentiment})")
        lines.append(f"     {theme.description}")
        lines.append(f"     Reviews mentioning this: {theme.review_count}")
        lines.append("")

    # --- Quotes ---
    lines.append("TOP USER QUOTES")
    lines.append("-" * 30)
    for i, quote in enumerate(report.quotes, 1):
        stars = "★" * quote.rating + "☆" * (5 - quote.rating)
        lines.append(f'  {i}. "{quote.text}"')
        lines.append(f"     Rating: {stars}  |  Theme: {quote.theme}")
        lines.append("")

    # --- Action Ideas ---
    lines.append("ACTIONABLE PRODUCT IDEAS")
    lines.append("-" * 30)
    for i, idea in enumerate(report.action_ideas, 1):
        lines.append(f"  {i}. {idea.title}")
        lines.append(f"     {idea.description}")
        lines.append(f"     Addresses: {idea.target_theme}")
        lines.append("")

    # --- Narrative ---
    lines.append("EXECUTIVE SUMMARY")
    lines.append("-" * 30)
    lines.append(report.text_body)
    lines.append("")
    lines.append(f"{'=' * 50}")
    lines.append(f"  End of Report")
    lines.append(f"{'=' * 50}")

    return "\n".join(lines)


def format_email_summary(report: FinalReport, doc_url: str = None) -> dict:
    """
    Creates an email subject and body summarizing the report.

    Args:
        report: Validated FinalReport from Phase 2.
        doc_url: Optional Google Doc URL to link in the email.

    Returns:
        Dict with 'subject' and 'body' keys.
    """
    date_str = datetime.now().strftime("%B %d, %Y")

    subject = f"Groww App Review Analysis — {date_str}"

    body_lines = []
    body_lines.append(f"Hi Team,")
    body_lines.append("")
    body_lines.append(f"The latest Groww App Review Analysis has been completed. "
                      f"Here is a quick summary of the findings:")
    body_lines.append("")

    # Top themes
    body_lines.append("KEY THEMES:")
    for i, theme in enumerate(report.themes, 1):
        body_lines.append(f"  {i}. {theme.name} — {theme.description}")
    body_lines.append("")

    # Action ideas
    body_lines.append("TOP ACTION ITEMS:")
    for i, idea in enumerate(report.action_ideas, 1):
        body_lines.append(f"  {i}. {idea.title} — {idea.description}")
    body_lines.append("")

    if doc_url:
        body_lines.append(f"Full report: {doc_url}")
        body_lines.append("")

    body_lines.append("Best regards,")
    body_lines.append("Groww Review Analyst (Automated)")

    return {
        "subject": subject,
        "body": "\n".join(body_lines),
    }
