"""
FinePrint — Clause Classification

Classifies clauses by type, burden, and risk score.
Batches clauses (~10 per call) for efficiency.
Rejects invalid types and retries once before falling back to 'other'.
"""

from __future__ import annotations

import json
import logging

from schemas import Clause, ClauseType

logger = logging.getLogger(__name__)

VALID_TYPES = {t.value for t in ClauseType}
BATCH_SIZE = 10


async def classify_clauses(clauses: list[Clause], full_text: str) -> list[Clause]:
    """
    Classify each clause by type, burden, and risk level.

    Args:
        clauses: List of clauses from segmentation
        full_text: Full document text (not sent to LLM — only clause text is sent)

    Returns:
        Updated clauses with type, burden_on, risk_score, risk_reasons set
    """
    from llm.client import complete_with_retry
    from llm.prompts.classify import SYSTEM, build_user

    # Process in batches
    for i in range(0, len(clauses), BATCH_SIZE):
        batch = clauses[i : i + BATCH_SIZE]
        batch_dicts = [{"id": c.id, "text": c.text} for c in batch]

        user_msg = build_user(batch_dicts)

        try:
            result = await complete_with_retry(SYSTEM, user_msg, retries=2)

            if isinstance(result, str):
                result = _parse_json_response(result)

            if not isinstance(result, list):
                logger.warning(f"Classification returned non-list, skipping batch {i}")
                continue

            # Map results to clauses
            result_map = {item["clause_id"]: item for item in result if "clause_id" in item}

            for clause in batch:
                if clause.id in result_map:
                    item = result_map[clause.id]
                    _apply_classification(clause, item)

        except Exception as e:
            logger.error(f"Classification failed for batch {i}: {e}")
            # Leave clauses with defaults (type=other, risk=1)

    return clauses


def _apply_classification(clause: Clause, item: dict):
    """Apply classification results to a clause, with validation."""
    # Validate and set type
    clause_type = item.get("type", "other")
    if clause_type not in VALID_TYPES:
        logger.warning(
            f"Invalid type '{clause_type}' for clause {clause.id}, using 'other'"
        )
        clause_type = "other"
    clause.type = ClauseType(clause_type)

    # Validate and set burden
    burden = item.get("burden_on", "unclear")
    if burden not in ("user", "counterparty", "mutual", "unclear"):
        burden = "unclear"
    clause.burden_on = burden

    # Validate and set risk score
    risk_score = item.get("risk_score", 1)
    if isinstance(risk_score, (int, float)):
        risk_score = max(1, min(5, int(risk_score)))
    else:
        risk_score = 1
    clause.risk_score = risk_score

    # Set risk reasons
    risk_reasons = item.get("risk_reasons", [])
    if isinstance(risk_reasons, list):
        clause.risk_reasons = [str(r) for r in risk_reasons]
    else:
        clause.risk_reasons = []


def _parse_json_response(text: str) -> list | dict:
    """Parse JSON from potentially markdown-wrapped response."""
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    return json.loads(text.strip())
