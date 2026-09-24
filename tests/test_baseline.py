"""
FinePrint — Baseline ("Is This Normal?") Tests

Validates:
1. Baseline corpus integrity (employment.json entries and required fields)
2. Fallback to 'no_baseline' when no matching baseline exists
"""

import sys
import json
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from schemas import Clause, ClauseType, Span
from analyze.baseline import BASELINE_PATH, compare_baselines

def test_baseline_corpus_integrity():
    assert BASELINE_PATH.exists(), "employment.json baseline file must exist"
    data = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
    assert len(data) >= 40, f"Expected at least 40 baseline entries, found {len(data)}"
    
    required_keys = {"id", "clause_type", "canonical_text", "typical_range", "source_note"}
    clause_types_found = set()
    for entry in data:
        for k in required_keys:
            assert k in entry, f"Missing key {k} in baseline {entry.get('id')}"
        clause_types_found.add(entry["clause_type"])
    
    # Must cover standard employment clause types
    assert "compensation" in clause_types_found
    assert "probation" in clause_types_found
    assert "notice_period" in clause_types_found
    assert "non_compete" in clause_types_found
    assert "training_bond" in clause_types_found

@pytest.mark.asyncio
async def test_no_baseline_fallback():
    # A clause with type OTHER or an unusual type should return no_baseline if no matching entries
    clause = Clause(
        id="c-999",
        index=0,
        heading="Space Travel Authorization",
        text="Employee is authorized to pilot orbital spacecraft on alternate weekends.",
        span=Span(start=0, end=75),
        type=ClauseType.OTHER,
        burden_on="user",
        risk_score=1,
    )
    verdicts = await compare_baselines([clause])
    assert len(verdicts) == 1
    assert verdicts[0].clause_id == "c-999"
    assert verdicts[0].verdict == "no_baseline"
