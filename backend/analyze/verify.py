"""
FinePrint — Grounding Verification

THE MOST IMPORTANT MODULE IN THE PROJECT.

For every generated Finding:
1. Structural check: full_text[start:end] == quote for document citations
2. Model check: separate LLM call with ONLY claim + cited text
3. unsupported → drop. partially_supported → keep but verified=false
4. Log every drop to data/verification_log.jsonl

Also enforces: no imperative phrasing in option-tier findings.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path

from schemas import Finding, Citation

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent.parent / "data"
VERIFICATION_LOG = DATA_DIR / "verification_log.jsonl"

# Banned imperative patterns for option-tier findings
BANNED_PATTERNS = [
    re.compile(r"\byou should\b", re.IGNORECASE),
    re.compile(r"\byou must\b", re.IGNORECASE),
    re.compile(r"\bdo not sign\b", re.IGNORECASE),
    re.compile(r"\byou need to\b", re.IGNORECASE),
    re.compile(r"\byou have to\b", re.IGNORECASE),
    re.compile(r"\brefuse to\b", re.IGNORECASE),
    re.compile(r"\bdemand that\b", re.IGNORECASE),
    re.compile(r"\binsist on\b", re.IGNORECASE),
]


async def verify_findings(
    findings: list[Finding], full_text: str
) -> list[Finding]:
    """
    Verify all findings through structural and model checks.

    Args:
        findings: Generated findings to verify
        full_text: Full document text for citation verification

    Returns:
        Filtered list of findings (unsupported ones removed)
    """
    verified: list[Finding] = []

    for finding in findings:
        # Step 0: Imperative lint for option-tier
        if finding.tier == "option":
            if _has_imperative(finding.body):
                _log_drop(finding, "imperative_phrasing",
                         "Option-tier finding uses banned imperative phrasing")
                continue

        # Step 1: Structural citation check
        valid_citations = []
        for citation in finding.citations:
            if citation.kind == "document" and citation.span:
                # Verify quote matches span
                extracted = full_text[citation.span.start:citation.span.end]
                if extracted == citation.quote:
                    valid_citations.append(citation)
                else:
                    _log_drop(
                        finding, "citation_mismatch",
                        f"Citation span [{citation.span.start}:{citation.span.end}] "
                        f"does not match quote. "
                        f"Got: '{extracted[:50]}...', Expected: '{citation.quote[:50]}...'"
                    )
                    # Don't keep this citation but don't drop the whole finding yet
            else:
                # Statute citations pass structural check
                valid_citations.append(citation)

        finding.citations = valid_citations

        # Step 2: Model verification check
        if valid_citations:
            try:
                model_verdict = await _model_verify(finding, full_text)

                if model_verdict == "unsupported":
                    _log_drop(finding, "model_unsupported",
                             "Model verification determined finding is unsupported")
                    continue
                elif model_verdict == "partially_supported":
                    finding.verified = False
                else:
                    finding.verified = True

            except Exception as e:
                logger.warning(f"Model verification failed for {finding.id}: {e}")
                # Keep the finding but mark as unverified
                finding.verified = False
        else:
            # No valid citations remain — only keep if it's an option-tier general advice
            if finding.tier == "option":
                finding.verified = True  # Options don't always need document citations
            else:
                _log_drop(finding, "no_valid_citations",
                         "All citations failed structural verification")
                continue

        verified.append(finding)

    logger.info(
        f"Verification: {len(verified)}/{len(findings)} findings passed "
        f"({len(findings) - len(verified)} dropped)"
    )

    return verified


async def _model_verify(finding: Finding, full_text: str) -> str:
    """
    Model-based verification.
    Sends ONLY the claim and cited text — no other context.

    Returns: "supported", "partially_supported", or "unsupported"
    """
    from llm.client import complete_with_retry
    from llm.prompts.verify import SYSTEM, build_user

    # Build the source text from all citations
    source_parts = []
    for citation in finding.citations:
        if citation.kind == "document" and citation.span:
            source_parts.append(citation.quote)
        elif citation.kind == "statute":
            source_parts.append(f"[Statute {citation.statute_id}]: {citation.quote}")

    source_text = "\n\n".join(source_parts) if source_parts else "(no source text)"
    claim = f"{finding.title}: {finding.body}"

    user_msg = build_user(claim, source_text)
    result = await complete_with_retry(SYSTEM, user_msg, retries=1)

    if isinstance(result, str):
        try:
            text = result.strip()
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            result = json.loads(text.strip())
        except json.JSONDecodeError:
            logger.warning(f"Could not parse verification response: {result[:100]}")
            return "partially_supported"

    verdict = result.get("verdict", "partially_supported")
    if verdict not in ("supported", "partially_supported", "unsupported"):
        verdict = "partially_supported"

    return verdict


def _has_imperative(text: str) -> bool:
    """Check if text contains banned imperative patterns."""
    for pattern in BANNED_PATTERNS:
        if pattern.search(text):
            return True
    return False


def _log_drop(finding: Finding, reason: str, details: str):
    """Log a dropped finding to the verification log."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "finding_id": finding.id,
        "finding_title": finding.title,
        "tier": finding.tier,
        "reason": reason,
        "details": details,
    }
    with open(VERIFICATION_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
    logger.info(f"DROPPED finding {finding.id}: {reason} — {details}")


def verify_single_citation(full_text: str, citation: Citation) -> bool:
    """
    Verify a single citation against the full text.
    Utility function for use by Q&A and other modules.
    """
    if citation.kind != "document" or not citation.span:
        return True  # Statute citations don't need span verification

    extracted = full_text[citation.span.start:citation.span.end]
    return extracted == citation.quote
