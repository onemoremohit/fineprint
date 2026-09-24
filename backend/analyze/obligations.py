"""
FinePrint — Obligations Extraction

Extracts dates, deadlines, notice windows, recurring duties,
and rupee amounts from classified clauses.

IMPORTANT: Resolves relative expressions into trigger + duration.
Never fabricates absolute dates from relative expressions.
"""

from __future__ import annotations

import json
import logging

from schemas import Clause, Obligation, Citation, Span

logger = logging.getLogger(__name__)


async def extract_obligations(
    clauses: list[Clause], full_text: str
) -> list[Obligation]:
    """
    Extract obligations from clauses using LLM.

    Args:
        clauses: Classified clauses
        full_text: Full document text for citation building

    Returns:
        List of Obligation objects with citations
    """
    from llm.client import complete_with_retry
    from llm.prompts.obligations import SYSTEM, build_user

    # Only send relevant clause types (skip purely administrative ones)
    relevant_types = {
        "compensation", "notice_period", "probation", "training_bond",
        "non_compete", "non_solicit", "confidentiality", "termination",
        "penalty_liquidated_damages", "indemnity", "working_hours",
        "leave", "benefits",
    }

    relevant_clauses = [
        c for c in clauses
        if c.type.value in relevant_types or c.risk_score >= 2
    ]

    if not relevant_clauses:
        relevant_clauses = clauses  # Fallback: use all

    clause_dicts = [{"id": c.id, "text": c.text} for c in relevant_clauses]
    user_msg = build_user(clause_dicts)

    try:
        result = await complete_with_retry(SYSTEM, user_msg, retries=2)

        if isinstance(result, str):
            result = _parse_json(result)

        if not isinstance(result, list):
            logger.warning("Obligations extraction returned non-list")
            return []

        # Build clause lookup for citation creation
        clause_map = {c.id: c for c in clauses}

        obligations: list[Obligation] = []
        for item in result:
            clause_id = item.get("clause_id", "")
            clause = clause_map.get(clause_id)

            # Build citation if we have the source clause
            citations = []
            if clause:
                citations.append(Citation(
                    kind="document",
                    span=Span(
                        start=clause.span.start,
                        end=clause.span.end,
                        page=clause.span.page,
                    ),
                    quote=clause.text,
                ))

            who = item.get("who", "user")
            if who not in ("user", "counterparty"):
                who = "user"

            obligation = Obligation(
                clause_id=clause_id,
                who=who,
                what=item.get("what", ""),
                due=item.get("due"),
                trigger=item.get("trigger"),
                amount_inr=_parse_amount(item.get("amount_inr")),
                citations=citations,
            )
            obligations.append(obligation)

        logger.info(f"Extracted {len(obligations)} obligations")
        return obligations

    except Exception as e:
        logger.error(f"Obligations extraction failed: {e}")
        return []


def _parse_amount(value) -> float | None:
    """Parse amount value, handling various formats."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        # Remove commas and currency symbols
        cleaned = value.replace(",", "").replace("₹", "").replace("INR", "").strip()
        try:
            return float(cleaned)
        except ValueError:
            return None
    return None


def _parse_json(text: str) -> list | dict:
    """Parse JSON from potentially markdown-wrapped response."""
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    return json.loads(text.strip())
