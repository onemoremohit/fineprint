import asyncio
import json
import sys
from pathlib import Path

# Add backend to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from httpx import AsyncClient, ASGITransport
from main import app
import pytest

@pytest.mark.asyncio
async def test_different_documents():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Document 1: gold-002 (Graduate Engineer Trainee with 3-year bond)
        g2 = json.loads(Path("eval/gold/gold-002.json").read_text(encoding="utf-8"))
        r1 = await client.post(
            "/api/documents",
            files={"file": ("vertex_offer.txt", g2["full_text"].encode("utf-8"), "text/plain")}
        )
        assert r1.status_code == 200, f"Upload 1 failed: {r1.text}"
        doc1_id = r1.json()["document_id"]
        
        a1_resp = await client.post(f"/api/documents/{doc1_id}/analyze")
        assert a1_resp.status_code == 200, f"Analyze 1 failed: {a1_resp.text}"
        a1 = a1_resp.json()

        # Document 2: gold-003 (Product Marketing Lead with no bond)
        g3 = json.loads(Path("eval/gold/gold-003.json").read_text(encoding="utf-8"))
        r2 = await client.post(
            "/api/documents",
            files={"file": ("apex_offer.txt", g3["full_text"].encode("utf-8"), "text/plain")}
        )
        assert r2.status_code == 200, f"Upload 2 failed: {r2.text}"
        doc2_id = r2.json()["document_id"]
        
        a2_resp = await client.post(f"/api/documents/{doc2_id}/analyze")
        assert a2_resp.status_code == 200, f"Analyze 2 failed: {a2_resp.text}"
        a2 = a2_resp.json()

        print(f"\n=================== DOCUMENT 1 (Vertex Tech) ===================")
        print(f"Document ID: {doc1_id}")
        print(f"Clause count: {len(a1['clauses'])}")
        print(f"Clause Types: {[c['type'] for c in a1['clauses']]}")
        print(f"Obligations count: {len(a1['obligations'])}")
        for ob in a1['obligations']:
            print(f"  - [{ob['who']}] {ob['what']} (Due: {ob['due']})")
        print(f"Findings count: {len(a1['findings'])}")

        print(f"\n=================== DOCUMENT 2 (Apex Digital) ===================")
        print(f"Document ID: {doc2_id}")
        print(f"Clause count: {len(a2['clauses'])}")
        print(f"Clause Types: {[c['type'] for c in a2['clauses']]}")
        print(f"Obligations count: {len(a2['obligations'])}")
        for ob in a2['obligations']:
            print(f"  - [{ob['who']}] {ob['what']} (Due: {ob['due']})")
        print(f"Findings count: {len(a2['findings'])}")

        # Redline test
        redline1 = (await client.post(f"/api/documents/{doc1_id}/redline")).json()
        redline2 = (await client.post(f"/api/documents/{doc2_id}/redline")).json()
        print(f"\nDoc 1 Redline count: {len(redline1['redlines'])}")
        print(f"Doc 2 Redline count: {len(redline2['redlines'])}")

        # Assertions
        assert a1['clauses'] != a2['clauses'], "Documents must produce different clauses!"
        assert a1['obligations'] != a2['obligations'], "Documents must produce different obligations!"
        assert a1['findings'] != a2['findings'], "Documents must produce different findings!"
        
        # Check that Vertex has a training bond obligation while Apex does not!
        vertex_types = [c['type'] for c in a1['clauses']]
        apex_types = [c['type'] for c in a2['clauses']]
        assert "training_bond" in vertex_types, "Vertex document should have a training bond"
        assert "training_bond" not in apex_types, "Apex document should NOT have a training bond"

        print("\n>>> ALL DIFFERENTIATION TESTS PASSED PERFECTLY! <<<")

if __name__ == "__main__":
    asyncio.run(test_different_documents())
