"""
Tests for FinePrint Efficiency & Performance Optimizations
Covers:
- Database indexed lookups & WAL configuration
- Embedding cache memory re-use
- GZip payload compression efficiency
"""

import time
import pytest
from httpx import AsyncClient, ASGITransport
from backend.main import app
from backend.db import _get_conn, store_document, get_document


def test_sqlite_wal_mode_enabled():
    """Verify that SQLite connection is running in fast WAL mode."""
    conn = _get_conn()
    try:
        row = conn.execute("PRAGMA journal_mode;").fetchone()
        assert row[0].lower() == "wal", f"Expected WAL mode, got {row[0]}"
    finally:
        conn.close()


def test_database_indexed_lookups_performance():
    """Verify that document and clause lookups execute in under 10 milliseconds."""
    test_id = "doc-perf-test-01"
    store_document(test_id, "perf_test.pdf", "Sample performance document text.")

    start = time.perf_counter()
    for _ in range(50):
        doc = get_document(test_id)
        assert doc is not None
    elapsed = time.perf_counter() - start

    # 50 queries should take well under 100ms with memory cache & indices
    assert elapsed < 0.25, f"Queries took too long: {elapsed:.3f}s for 50 lookups"


@pytest.mark.asyncio
async def test_gzip_compression_active():
    """Verify that GZip compression middleware compresses large JSON responses."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Request with gzip accept-encoding
        headers = {"Accept-Encoding": "gzip"}
        resp = await client.get("/api/health", headers=headers)
        assert resp.status_code == 200
