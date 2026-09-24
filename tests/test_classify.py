"""
FinePrint — Clause Classification Tests

Validates:
1. Valid types map to ClauseType enum
2. Invalid types safely fallback to ClauseType.OTHER
3. Risk score clamped to range 1-5
4. Burden_on validation ('user', 'counterparty', 'mutual', 'unclear')
"""

import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from schemas import Clause, ClauseType, Span
from analyze.classify import _apply_classification, VALID_TYPES

def make_dummy_clause(id: str = "c-001") -> Clause:
    return Clause(
        id=id,
        index=0,
        text="Sample clause text",
        span=Span(start=0, end=18),
        type=ClauseType.OTHER,
        burden_on="unclear",
        risk_score=1,
    )

def test_valid_classification():
    clause = make_dummy_clause()
    item = {
        "clause_id": "c-001",
        "type": "non_compete",
        "burden_on": "user",
        "risk_score": 5,
        "risk_reasons": ["Post-employment restriction across all India"],
    }
    _apply_classification(clause, item)
    assert clause.type == ClauseType.NON_COMPETE
    assert clause.burden_on == "user"
    assert clause.risk_score == 5
    assert len(clause.risk_reasons) == 1

def test_invalid_type_fallback():
    clause = make_dummy_clause()
    item = {
        "clause_id": "c-001",
        "type": "some_invented_invalid_legal_type",
        "burden_on": "user",
        "risk_score": 3,
    }
    _apply_classification(clause, item)
    assert clause.type == ClauseType.OTHER

def test_risk_score_clamping():
    clause_low = make_dummy_clause("c-002")
    _apply_classification(clause_low, {"risk_score": -10, "type": "compensation"})
    assert clause_low.risk_score == 1

    clause_high = make_dummy_clause("c-003")
    _apply_classification(clause_high, {"risk_score": 999, "type": "compensation"})
    assert clause_high.risk_score == 5

def test_invalid_burden_fallback():
    clause = make_dummy_clause()
    _apply_classification(clause, {"burden_on": "alien_party"})
    assert clause.burden_on == "unclear"
