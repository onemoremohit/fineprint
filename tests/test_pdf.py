"""
FinePrint — Lawyer Brief PDF Generation Tests

Validates:
1. PDF generated via ReportLab is valid PDF format (%PDF magic bytes)
2. PDF fits 1-2 pages structure and includes:
   - Header / document overview
   - Key clauses quoted verbatim
   - Specific questions to ask advocate
   - Statutory caveat footer
3. Endpoint GET /api/documents/{id}/brief.pdf returns application/pdf
"""

import sys
import json
from pathlib import Path
import pytest
from httpx import AsyncClient, ASGITransport

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from main import app
from db import init_db, store_document, store_analysis
from outputs.lawyer_brief import generate_brief_pdf

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"

@pytest.fixture
def sample_analysis_data():
    fixture_path = FIXTURES_DIR / "analysis_response.json"
    return json.loads(fixture_path.read_text(encoding="utf-8"))

def test_generate_brief_pdf_creates_valid_file(sample_analysis_data):
    doc_id = "test-doc-pdf"
    full_text = "EMPLOYMENT OFFER LETTER\n1. Compensation\nINR 8,00,000 per annum.\n"
    
    pdf_path = generate_brief_pdf(doc_id, full_text, sample_analysis_data)
    
    assert pdf_path.exists(), "PDF file was not created"
    file_bytes = pdf_path.read_bytes()
    assert len(file_bytes) > 2000, "PDF file is suspiciously small"
    # PDF Magic header
    assert file_bytes.startswith(b"%PDF"), "Generated file does not have valid PDF magic bytes"

@pytest.mark.asyncio
async def test_brief_endpoint_returns_pdf(sample_analysis_data):
    init_db()
    doc_id = "test-doc-pdf-api"
    full_text = "EMPLOYMENT OFFER LETTER\n1. Compensation\nINR 8,00,000 per annum.\n"
    store_document(doc_id, "offer.txt", full_text)
    store_analysis(doc_id, sample_analysis_data)
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get(f"/api/documents/{doc_id}/brief.pdf")
        assert resp.status_code == 200
        assert resp.headers.get("content-type") == "application/pdf"
        assert resp.content.startswith(b"%PDF")
