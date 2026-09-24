"""
FinePrint — Report Assembly

Assembles Finding[] across three tiers:
- document_says: Direct quotes with citations
- general_law: Statute-based analysis
- option: Suggested actions (never imperative)
"""

from __future__ import annotations

import logging
from typing import Optional

from schemas import (
    Clause, BaselineVerdict, EnforceabilityFlag,
    Obligation, Finding, Citation, Span
)

logger = logging.getLogger(__name__)


def assemble_findings(
    clauses: list[Clause],
    baseline_verdicts: list[BaselineVerdict],
    enforceability_flags: list[EnforceabilityFlag],
    obligations: list[Obligation],
    full_text: str,
) -> list[Finding]:
    """
    Assemble findings from all analysis results.

    Three tiers:
    - document_says: What the document explicitly states
    - general_law: How Indian law treats these clauses
    - option: What the user might consider (never imperative)

    Returns:
        List of Finding objects ready for verification
    """
    findings: list[Finding] = []
    finding_counter = 0
    clause_map = {c.id: c for c in clauses}

    # ─── Tier 1: Document Says ─────────────────────────────────
    # Generate findings for high-risk clauses and notable baselines

    # High-risk clauses (risk ≥ 3)
    for clause in clauses:
        if clause.risk_score >= 3:
            finding_counter += 1

            # Find baseline verdict for this clause
            baseline = _find_baseline(clause.id, baseline_verdicts)
            verdict_text = ""
            if baseline and baseline.verdict != "no_baseline":
                verdict_label = baseline.verdict.replace("_", " ").title()
                verdict_text = f" This clause is assessed as **{verdict_label}** compared to standard agreements."

            body = (
                f"{clause.text}"
                f"{verdict_text}"
            )

            if clause.risk_reasons:
                body += "\n\nKey observations:\n"
                for reason in clause.risk_reasons:
                    body += f"- {reason}\n"

            findings.append(Finding(
                id=f"f-{finding_counter:03d}",
                title=_generate_title(clause),
                tier="document_says",
                body=body,
                clause_ids=[clause.id],
                citations=[
                    Citation(
                        kind="document",
                        span=Span(
                            start=clause.span.start,
                            end=clause.span.end,
                            page=clause.span.page,
                        ),
                        quote=clause.text,
                    )
                ],
                verified=False,
            ))

    # ─── Tier 2: General Law ──────────────────────────────────
    # Generate findings for enforceability flags

    for flag in enforceability_flags:
        finding_counter += 1
        clause = clause_map.get(flag.clause_id)

        citations: list[Citation] = []
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

        # Add statute citations
        for statute_id in flag.statute_ids:
            citations.append(Citation(
                kind="statute",
                span=None,
                statute_id=statute_id,
                quote=flag.explanation[:200],  # Will be replaced with actual statute text
            ))

        status_label = flag.status.replace("_", " ").title()
        body = (
            f"**Status: {status_label}** (Confidence: {flag.confidence})\n\n"
            f"{flag.explanation}\n\n"
            f"**Questions to discuss with a lawyer:**\n"
        )
        for question in flag.ask_a_lawyer:
            body += f"- {question}\n"

        findings.append(Finding(
            id=f"f-{finding_counter:03d}",
            title=_enforceability_title(flag, clause),
            tier="general_law",
            body=body,
            clause_ids=[flag.clause_id],
            citations=citations,
            verified=False,
        ))

    # ─── Tier 3: Options ──────────────────────────────────────
    # Generate suggestion findings for risky/unusual clauses
    # CRITICAL: Use option framing, never imperative

    risky_clauses = [
        c for c in clauses
        if c.risk_score >= 4
        or _find_baseline(c.id, baseline_verdicts) and
           _find_baseline(c.id, baseline_verdicts).verdict in ("stricter_than_usual", "unusual")
    ]

    if risky_clauses:
        finding_counter += 1
        points = []
        clause_ids = []

        for clause in risky_clauses[:5]:  # Top 5 at most
            clause_ids.append(clause.id)
            baseline = _find_baseline(clause.id, baseline_verdicts)
            heading = clause.heading or clause.type.value.replace("_", " ").title()

            point = f"**{heading} (Clause {clause.id})**: "
            if baseline and baseline.verdict == "unusual":
                point += f"This clause is unusual. One option is to request its removal or substantial modification."
            elif baseline and baseline.verdict == "stricter_than_usual":
                point += f"This clause is stricter than usual. One option is to negotiate more standard terms."
            elif clause.risk_score >= 5:
                point += f"This clause presents significant exposure. One option is to discuss its scope and limitations."
            else:
                point += f"This clause warrants attention. One option is to seek clarification on its practical application."

            points.append(point)

        body = "Based on the analysis, the following areas present the most significant considerations:\n\n"
        for i, point in enumerate(points, 1):
            body += f"{i}. {point}\n\n"
        body += (
            "These are options to consider, not directives. "
            "Confirm with a lawyer before making any requests or decisions."
        )

        findings.append(Finding(
            id=f"f-{finding_counter:03d}",
            title="Points to Consider",
            tier="option",
            body=body,
            clause_ids=clause_ids,
            citations=[],
            verified=False,
        ))

    # ─── Obligations Summary ──────────────────────────────────
    if obligations:
        finding_counter += 1
        body = "The document establishes the following key obligations:\n\n"

        user_obligations = [o for o in obligations if o.who == "user"]
        counterparty_obligations = [o for o in obligations if o.who == "counterparty"]

        if user_obligations:
            body += "**Your obligations:**\n"
            for ob in user_obligations:
                amount_text = f" (₹{ob.amount_inr:,.0f})" if ob.amount_inr else ""
                trigger_text = f" — Trigger: {ob.trigger}" if ob.trigger else ""
                body += f"- {ob.what}{amount_text}{trigger_text}\n"
            body += "\n"

        if counterparty_obligations:
            body += "**Employer obligations:**\n"
            for ob in counterparty_obligations:
                amount_text = f" (₹{ob.amount_inr:,.0f})" if ob.amount_inr else ""
                trigger_text = f" — Trigger: {ob.trigger}" if ob.trigger else ""
                body += f"- {ob.what}{amount_text}{trigger_text}\n"

        clause_ids = list(set(o.clause_id for o in obligations))
        citations = []
        for o in obligations:
            citations.extend(o.citations)

        findings.append(Finding(
            id=f"f-{finding_counter:03d}",
            title="Obligations Summary",
            tier="document_says",
            body=body,
            clause_ids=clause_ids,
            citations=citations[:5],  # Limit citations
            verified=False,
        ))

    return findings


def _find_baseline(
    clause_id: str, verdicts: list[BaselineVerdict]
) -> Optional[BaselineVerdict]:
    """Find baseline verdict for a clause."""
    for v in verdicts:
        if v.clause_id == clause_id:
            return v
    return None


def _generate_title(clause: Clause) -> str:
    """Generate a human-readable title for a document_says finding."""
    type_labels = {
        "notice_period": "Notice Period Terms",
        "training_bond": "Training Bond Requirements",
        "non_compete": "Non-Compete Restriction",
        "non_solicit": "Non-Solicitation Restriction",
        "confidentiality": "Confidentiality Obligation",
        "ip_assignment": "Intellectual Property Assignment",
        "termination": "Termination Provisions",
        "penalty_liquidated_damages": "Penalty / Liquidated Damages",
        "compensation": "Compensation Terms",
        "probation": "Probation Period",
        "indemnity": "Indemnity Clause",
    }
    return type_labels.get(clause.type.value, clause.heading or "Notable Clause")


def _enforceability_title(
    flag: EnforceabilityFlag, clause: Clause | None
) -> str:
    """Generate a title for an enforceability finding."""
    status_map = {
        "likely_unenforceable": "May Not Be Enforceable",
        "limited_enforceability": "Has Limited Enforceability",
        "likely_enforceable": "Is Likely Enforceable",
        "unclear": "Enforceability Is Unclear",
    }
    clause_label = ""
    if clause:
        clause_label = clause.heading or clause.type.value.replace("_", " ").title()
    status_text = status_map.get(flag.status, "Enforceability Assessment")
    return f"{clause_label} — {status_text}" if clause_label else status_text
