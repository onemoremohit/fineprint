"""
FinePrint — Statute Loading & Enforceability Tests

Validates:
1. Hard constraint: Unverified statute entries are NEVER loaded
2. All production statute entries in contract_act.json are verified
3. Non-compete clauses match ICA Section 27
4. Enforceability flags always include non-empty ask_a_lawyer questions
"""

import sys
import json
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from schemas import Clause, ClauseType, Span
from analyze.statute import _is_verified, _load_statute_files, check_enforceability, STATUTES_DIR

def test_unverified_entries_rejected():
    assert not _is_verified({"id": "s-1", "verified_by": ""})
    assert not _is_verified({"id": "s-2", "verified_by": None})
    assert not _is_verified({"id": "s-3", "verified_by": "   "})
    assert not _is_verified({"id": "s-4"}) # missing key
    assert _is_verified({"id": "s-5", "verified_by": "Advocate Sharma"})

def test_all_production_statutes_have_verification():
    """Ensure all entries currently in data/statutes/*.json satisfy verified_by."""
    for json_path in STATUTES_DIR.glob("*.json"):
        data = json.loads(json_path.read_text(encoding="utf-8"))
        entries = data if isinstance(data, list) else [data]
        for entry in entries:
            assert _is_verified(entry), (
                f"Statute entry {entry.get('id')} in {json_path.name} is not verified!"
            )
            assert entry.get("verified_on"), (
                f"Statute entry {entry.get('id')} is missing verified_on timestamp"
            )

@pytest.mark.asyncio
async def test_non_compete_statute_enforceability():
    """Non-compete clause must flag ICA Section 27 as likely_unenforceable."""
    clause = Clause(
        id="c-005",
        index=4,
        heading="5. Non-Compete",
        text="The Employee shall not engage in or be employed by any business that competes with the Company within India for 12 months.",
        span=Span(start=0, end=115),
        type=ClauseType.NON_COMPETE,
        burden_on="user",
        risk_score=5,
    )
    flags = await check_enforceability([clause])
    assert len(flags) > 0
    flag = flags[0]
    assert flag.clause_id == "c-005"
    assert "ica-s27" in flag.statute_ids
    assert flag.status == "likely_unenforceable"
    assert len(flag.ask_a_lawyer) > 0, "ask_a_lawyer must never be empty"
