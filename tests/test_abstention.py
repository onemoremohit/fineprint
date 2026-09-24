"""
FinePrint — Grounded Q&A Abstention Gate Test

HARD ACCEPTANCE CRITERIA:
The system must abstain when asked questions whose answers
are not present in the document.

5 unanswerable questions test:
1. Maternity leave duration and stipend
2. Office cafeteria catering and coffee brands
3. Company annual gross turnover/revenue
4. Pet-friendly policy in the office
5. Aeroplane and helicopter rooftop landing rights

System must abstain on all 5.
"""

import sys
from pathlib import Path
import pytest
from httpx import AsyncClient, ASGITransport

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from main import app
from db import init_db, store_document, store_analysis

SAMPLE_DOC_TEXT = """EMPLOYMENT OFFER LETTER
Date: 15 January 2025
Company: TechCorp India Pvt. Ltd.
Role: Senior Developer
1. Compensation: INR 12,00,000 per annum.
2. Probation: 3 months from joining date.
3. Notice Period: 30 days written notice.
4. Non-Compete: 6 months within Bangalore.
"""

UNANSWERABLE_QUESTIONS = [
    "What is the company's maternity leave policy and stipend?",
    "What brand of coffee machine is provided in the cafeteria?",
    "What was the company's annual revenue and turnover last year?",
    "Can I bring my pet dog to the office on Fridays?",
    "Does the employee have permission to land an aeroplane or helicopter on the roof?",
]

@pytest.fixture
def setup_test_doc():
    init_db()
    doc_id = "test-doc-abstention"
    store_document(doc_id, "offer.txt", SAMPLE_DOC_TEXT)
    analysis_data = {
        "document_id": doc_id,
        "clauses": [
            {"id": "c-001", "text": "1. Compensation: INR 12,00,000 per annum.", "span": {"start": 74, "end": 115}},
            {"id": "c-002", "text": "2. Probation: 3 months from joining date.", "span": {"start": 116, "end": 156}},
            {"id": "c-003", "text": "3. Notice Period: 30 days written notice.", "span": {"start": 157, "end": 196}},
            {"id": "c-004", "text": "4. Non-Compete: 6 months within Bangalore.", "span": {"start": 197, "end": 239}},
        ],
        "findings": [],
        "obligations": [],
        "baseline_verdicts": [],
        "enforceability_flags": [],
    }
    store_analysis(doc_id, analysis_data)
    return doc_id

@pytest.mark.asyncio
async def test_5_unanswerable_questions_abstain_via_api(setup_test_doc):
    doc_id = setup_test_doc
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        for q in UNANSWERABLE_QUESTIONS:
            resp = await ac.post(f"/api/documents/{doc_id}/ask", json={"question": q})
            assert resp.status_code == 200, f"Q&A request failed for question: {q}"
            data = resp.json()
            assert data["abstained"] is True, (
                f"FAILED ABSTENTION GATE: System failed to abstain on unanswerable question:\n"
                f"Question: {q}\n"
                f"Response: {data['answer']}"
            )
            assert len(data.get("citations", [])) == 0, (
                "Abstained answer must not cite document clauses"
            )

@pytest.mark.asyncio
async def test_answer_pipeline_direct_abstention(setup_test_doc):
    doc_id = setup_test_doc
    from qa.answer import answer_question
    for q in UNANSWERABLE_QUESTIONS:
        resp = await answer_question(q, SAMPLE_DOC_TEXT, doc_id)
        assert resp.abstained is True, f"Direct pipeline failed to abstain on: {q}"
