"""
FinePrint — Segmentation & Offset Assertion Tests

Validates:
1. Rule-first segmentation detects standard legal headings
2. CRITICAL INVARIANT: full_text[clause.span.start:clause.span.end] == clause.text
3. Clause IDs, headings, and indices are well-formed
"""

import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from schemas import Clause
from segment.clauses import segment_clauses, _verify_offset

SAMPLE_OFFER_LETTER = """EMPLOYMENT OFFER LETTER

Date: 15th January 2025

Dear Candidate,

We are pleased to offer you the position of Software Engineer at TechCorp India Pvt. Ltd.

1. Compensation
The Company shall pay the Employee a gross annual salary of INR 8,00,000 (Rupees Eight Lakhs Only), payable in twelve equal monthly instalments.

2. Probation Period
The Employee shall be on probation for a period of six (6) months from the date of joining. Either party may terminate with 15 days notice.

3. Notice Period
After confirmation, either party may terminate this agreement by giving ninety (90) days written notice or three months salary in lieu thereof.

4. Training Bond
The Employee agrees to serve the Company for a minimum period of two (2) years from the date of completion of any training programme. Liquidated damages INR 3,00,000.

5. Non-Compete
For a period of twelve (12) months following the termination of employment, the Employee shall not work for any competitor within India.

6. Confidentiality
The Employee shall not disclose confidential information without prior written consent.

Yours sincerely,
TechCorp India Pvt. Ltd.
"""

SAMPLE_AGREEMENT_ROMAN = """SERVICES AGREEMENT

ARTICLE I: SCOPE OF SERVICES
The Consultant agrees to provide software advisory services as specified in Exhibit A.

ARTICLE II: TERM AND TERMINATION
This Agreement shall commence on the Effective Date and continue for a period of one (1) year.

ARTICLE III: INTELLECTUAL PROPERTY
All work product developed under this agreement shall belong exclusively to the Client.
"""

@pytest.mark.asyncio
async def test_segment_offer_letter():
    clauses = await segment_clauses(SAMPLE_OFFER_LETTER)
    assert len(clauses) >= 5, f"Expected at least 5 clauses, got {len(clauses)}"
    
    # Check the offset invariant on EVERY single clause
    for clause in clauses:
        assert clause.span.start >= 0
        assert clause.span.end <= len(SAMPLE_OFFER_LETTER)
        assert clause.span.start < clause.span.end
        extracted = SAMPLE_OFFER_LETTER[clause.span.start:clause.span.end]
        assert extracted == clause.text, (
            f"Offset mismatch for clause {clause.id} ({clause.heading}):\n"
            f"Expected: {clause.text[:40]!r}\n"
            f"Extracted: {extracted[:40]!r}"
        )

@pytest.mark.asyncio
async def test_segment_article_headings():
    clauses = await segment_clauses(SAMPLE_AGREEMENT_ROMAN)
    assert len(clauses) >= 3
    for clause in clauses:
        extracted = SAMPLE_AGREEMENT_ROMAN[clause.span.start:clause.span.end]
        assert extracted == clause.text

def test_verify_offset_raises_on_corrupt_span():
    text = "Clause 1: Confidentiality obligation."
    clause = Clause(
        id="c-001",
        index=0,
        text="Confidentiality obligation.",
        span={"start": 0, "end": 5}, # Incorrect span
    )
    # _verify_offset searches for clause.text if idx != -1, or raises ValueError
    # If text is not anywhere in the document, it must raise ValueError
    clause.text = "This phrase is completely absent from the text."
    with pytest.raises(ValueError) as excinfo:
        _verify_offset(text, clause)
    assert "CRITICAL: Offset mismatch" in str(excinfo.value)
