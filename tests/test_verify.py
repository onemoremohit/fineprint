"""
FinePrint — Grounding Verification Tests

CRITICAL TESTS FOR SYSTEM SAFETY:
1. Corrupted citation test: quote != full_text[start:end] is caught and dropped
2. Imperative phrasing lint: "you should", "you must", "do not sign" in option tier are rejected
3. Dropped findings are logged to data/verification_log.jsonl
"""

import sys
import json
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from schemas import Finding, Citation, Span
from analyze.verify import verify_findings, _has_imperative, VERIFICATION_LOG

FULL_TEXT = """EMPLOYMENT AGREEMENT
1. Notice Period
The Employee shall give ninety (90) days written notice prior to resignation.
"""

@pytest.mark.asyncio
async def test_corrupted_citation_dropped():
    # Clear or prepare verification log
    if VERIFICATION_LOG.exists():
        VERIFICATION_LOG.unlink()

    # Valid span for: "The Employee shall give ninety (90) days written notice prior to resignation."
    start = FULL_TEXT.find("The Employee")
    end = start + len("The Employee shall give ninety (90) days written notice prior to resignation.")

    # Finding with corrupted quote
    corrupted_finding = Finding(
        id="f-bad-01",
        title="Notice Requirement",
        tier="document_says",
        body="Employee must provide 90 days notice.",
        clause_ids=["c-001"],
        citations=[
            Citation(
                kind="document",
                span=Span(start=start, end=end),
                quote="The Employee can leave whenever they feel like it with zero notice.", # Mismatch!
            )
        ],
    )

    verified = await verify_findings([corrupted_finding], FULL_TEXT)
    # The corrupted finding must be dropped
    assert len(verified) == 0, "Corrupted citation should have caused finding to be dropped"

    # Verification log must record the drop
    assert VERIFICATION_LOG.exists()
    log_content = VERIFICATION_LOG.read_text(encoding="utf-8")
    assert "f-bad-01" in log_content
    assert "citation_mismatch" in log_content or "no_valid_citations" in log_content

def test_imperative_detection():
    assert _has_imperative("You should request a reduction in notice period.")
    assert _has_imperative("You must clarify the training bond clauses.")
    assert _has_imperative("Do not sign this document until reviewed.")
    assert _has_imperative("You need to ask for written confirmation.")
    assert not _has_imperative("Employees frequently consider requesting a reduced notice period.")
    assert not _has_imperative("A legal advocate may assist with redlining.")

@pytest.mark.asyncio
async def test_imperative_in_option_tier_dropped():
    finding = Finding(
        id="f-opt-01",
        title="Negotiation Step",
        tier="option",
        body="You should refuse to sign the bond until terms are revised.", # Imperative!
        clause_ids=["c-001"],
        citations=[],
    )

    verified = await verify_findings([finding], FULL_TEXT)
    assert len(verified) == 0, "Imperative phrasing in option-tier finding must be dropped"

@pytest.mark.asyncio
async def test_valid_option_tier_accepted():
    finding = Finding(
        id="f-opt-02",
        title="Negotiation Step",
        tier="option",
        body="One potential consideration is discussing standard probation terms with HR.",
        clause_ids=["c-001"],
        citations=[],
    )

    verified = await verify_findings([finding], FULL_TEXT)
    assert len(verified) == 1
    assert verified[0].id == "f-opt-02"
