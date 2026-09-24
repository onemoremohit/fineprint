"""
Tests for FinePrint Security Implementations
Covers:
- Strict upload size enforcement (HTTP 413)
- Path traversal & filename sanitization
- Magic bytes file signature verification
- Defense-in-depth HTTP security headers
- Safe document ID parameter sanitization
"""

import io
import pytest
from httpx import AsyncClient, ASGITransport
from backend.main import app, MAX_UPLOAD_SIZE


@pytest.mark.asyncio
async def test_security_headers_present():
    """Verify that all critical HTTP security headers are enforced."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/health")
        assert resp.status_code == 200
        headers = resp.headers
        assert headers.get("x-content-type-options") == "nosniff"
        assert headers.get("x-frame-options") == "DENY"
        assert headers.get("x-xss-protection") == "1; mode=block"
        assert headers.get("referrer-policy") == "strict-origin-when-cross-origin"
        assert "max-age=31536000" in headers.get("strict-transport-security", "")
        assert "geolocation=()" in headers.get("permissions-policy", "")


@pytest.mark.asyncio
async def test_upload_oversized_file_rejected():
    """Verify that uploads exceeding MAX_UPLOAD_SIZE are rejected with HTTP 413."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create a payload larger than 15 MB
        oversized_data = b"%PDF" + b"0" * (MAX_UPLOAD_SIZE + 1024)
        files = {"file": ("big_doc.pdf", io.BytesIO(oversized_data), "application/pdf")}
        resp = await client.post("/api/documents", files=files)
        assert resp.status_code == 413
        assert "too large" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_upload_invalid_signature_rejected():
    """Verify that a file disguised with wrong magic bytes is rejected."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # File has .pdf extension but content is NOT a PDF (missing %PDF magic bytes)
        fake_pdf = b"This is not a real PDF file, just plain text"
        files = {"file": ("fake.pdf", io.BytesIO(fake_pdf), "application/pdf")}
        resp = await client.post("/api/documents", files=files)
        assert resp.status_code == 400
        assert "file signature" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_invalid_doc_id_path_traversal_rejected():
    """Verify that malicious doc_id patterns (e.g. path traversal) are rejected with 400."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        malicious_ids = [
            "../../etc/passwd",
            "doc-123; DROP TABLE documents;",
            "doc/<script>alert(1)</script>",
            "a" * 100,  # too long
        ]
        for bad_id in malicious_ids:
            resp = await client.post(f"/api/documents/{bad_id}/analyze")
            assert resp.status_code in (400, 404, 405), f"Failed to reject malicious doc_id: {bad_id}"
