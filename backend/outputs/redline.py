"""
FinePrint — Redline Generation

Generates suggested clause changes and a negotiation email draft.
Only targets clauses with risk ≥ 4 or verdict stricter_than_usual/unusual.
Tone: professional, non-adversarial, non-accusatory.
"""

from __future__ import annotations

import json
import logging

from schemas import RedlineResponse, Redline

logger = logging.getLogger(__name__)


async def generate_redlines(
    analysis: dict, full_text: str
) -> RedlineResponse:
    """
    Generate redlines and a negotiation email for high-risk clauses.

    Args:
        analysis: Full analysis response dict
        full_text: Full document text

    Returns:
        RedlineResponse with suggested changes and email draft
    """
    from llm.client import complete_with_retry
    from llm.prompts.redline import SYSTEM, build_user

    clauses = analysis.get("clauses", [])
    baseline_verdicts = analysis.get("baseline_verdicts", [])

    # Build verdict lookup
    verdict_map = {
        bv["clause_id"]: bv.get("verdict", "standard")
        for bv in baseline_verdicts
    }

    # Filter to high-risk clauses
    high_risk = []
    for clause in clauses:
        risk = clause.get("risk_score", 1)
        clause_id = clause.get("id", "")
        verdict = verdict_map.get(clause_id, "standard")

        if risk >= 4 or verdict in ("stricter_than_usual", "unusual"):
            high_risk.append(clause)

    if not high_risk:
        return RedlineResponse(
            redlines=[],
            email_draft="No significant issues were identified that warrant a negotiation email.",
        )

    user_msg = build_user(high_risk, baseline_verdicts)

    try:
        result = await complete_with_retry(SYSTEM, user_msg, retries=2)

        if isinstance(result, str):
            text = result.strip()
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            result = json.loads(text.strip())

        redlines = []
        for item in result.get("redlines", []):
            redlines.append(Redline(
                clause_id=item.get("clause_id", ""),
                current_text=item.get("current_text", ""),
                suggested_text=item.get("suggested_text", ""),
                rationale=item.get("rationale", ""),
            ))

        return RedlineResponse(
            redlines=redlines,
            email_draft=result.get("email_draft", ""),
        )

    except Exception as e:
        logger.error(f"Redline generation failed: {e}")
        return RedlineResponse(
            redlines=[],
            email_draft=f"Redline generation encountered an error: {str(e)}",
        )
