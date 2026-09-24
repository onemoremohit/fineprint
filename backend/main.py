"""
FinePrint — FastAPI Application

All routes are defined here. The app serves fixture data in MOCK_LLM=1 mode
and real analysis data when connected to an LLM provider.
"""

from __future__ import annotations

import json
import os
import sys
import uuid
import logging
from pathlib import Path
from typing import Optional

# Ensure backend directory is in sys.path
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(Path(__file__).parent.parent / ".env")

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

from schemas import (
    AnalysisResponse,
    QARequest,
    QAResponse,
    RedlineResponse,
    UploadResponse,
    PageMapEntry,
)
from db import init_db, store_document, get_document, store_analysis, get_analysis

# ─── Setup ───────────────────────────────────────────────────────

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MOCK_LLM = os.getenv("MOCK_LLM", "0") == "1"
FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"
DATA_DIR = Path(__file__).parent.parent / "data"

app = FastAPI(
    title="FinePrint — Legal AI Assistant",
    description="Analyzes legal documents and produces grounded Position Reports",
    version="0.1.0",
)

# CORS for frontend dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup():
    """Initialize database and load knowledge bases on startup."""
    init_db()
    logger.info("FinePrint API started")
    if MOCK_LLM:
        logger.info("⚠️  Running in MOCK_LLM mode — returning fixture data")


# ─── Helper to load fixtures ─────────────────────────────────────

def _load_fixture(name: str) -> dict:
    path = FIXTURES_DIR / f"{name}.json"
    if not path.exists():
        raise HTTPException(500, f"Fixture {name} not found")
    return json.loads(path.read_text(encoding="utf-8"))


# ─── Routes ───────────────────────────────────────────────────────

@app.post("/api/documents", response_model=UploadResponse)
async def upload_document(file: UploadFile = File(...)):
    """
    Upload a legal document (PDF, DOCX, TXT, or image).
    Returns document_id, extracted full_text, and page map.
    """
    if not file.filename:
        raise HTTPException(400, "No file provided")

    # Validate file type
    allowed_extensions = {
        ".pdf", ".docx", ".doc", ".txt", ".text",
        ".png", ".jpg", ".jpeg", ".tiff", ".bmp",
    }
    ext = Path(file.filename).suffix.lower()
    if ext not in allowed_extensions:
        raise HTTPException(
            400,
            f"Unsupported file type: {ext}. Accepted: {', '.join(allowed_extensions)}"
        )

    doc_id = f"doc-{uuid.uuid4().hex[:8]}"
    content = await file.read()

    # Extract text from uploaded document
    from ingest.extract import extract_text

    full_text, page_map = await extract_text(content, ext)
    if not full_text or not full_text.strip():
        raise HTTPException(
            400,
            "Could not extract readable text from the uploaded document. Please check the file."
        )

    pages = [
        PageMapEntry(page_no=p, start=s, end=e) for p, s, e in page_map
    ]

    store_document(doc_id, file.filename, full_text)

    return UploadResponse(
        document_id=doc_id,
        full_text=full_text,
        pages=pages,
    )


@app.post("/api/documents/{doc_id}/analyze", response_model=AnalysisResponse)
async def analyze_document(doc_id: str):
    """
    Run the full analysis pipeline on an uploaded document.
    Returns clauses, baseline verdicts, enforceability flags,
    obligations, and findings.
    """
    doc = get_document(doc_id)
    if not doc:
        raise HTTPException(404, f"Document {doc_id} not found")

    # Real analysis pipeline
    from segment.clauses import segment_clauses
    from analyze.classify import classify_clauses
    from analyze.baseline import compare_baselines
    from analyze.statute import check_enforceability
    from analyze.obligations import extract_obligations
    from outputs.report import assemble_findings
    from analyze.verify import verify_findings

    full_text = doc["full_text"]

    # Phase 1: Segment clauses
    clauses = await segment_clauses(full_text)

    # Phase 2: Classify clauses
    clauses = await classify_clauses(clauses, full_text)

    # Phase 3: Baseline + Statute
    baseline_verdicts = await compare_baselines(clauses)
    enforceability_flags = await check_enforceability(clauses)

    # Phase 4: Obligations + Report + Verify
    obligations = await extract_obligations(clauses, full_text)
    findings = assemble_findings(
        clauses, baseline_verdicts, enforceability_flags, obligations, full_text
    )
    findings = await verify_findings(findings, full_text)

    result = AnalysisResponse(
        document_id=doc_id,
        clauses=clauses,
        baseline_verdicts=baseline_verdicts,
        enforceability_flags=enforceability_flags,
        obligations=obligations,
        findings=findings,
    )

    store_analysis(doc_id, result.model_dump())
    return result


@app.post("/api/documents/{doc_id}/ask", response_model=QAResponse)
async def ask_question(doc_id: str, body: QARequest):
    """
    Grounded Q&A over the uploaded document.
    Returns an answer with citations, or abstains when the document
    does not contain the answer.
    """
    doc = get_document(doc_id)
    if not doc:
        raise HTTPException(404, f"Document {doc_id} not found")

    # Real Q&A pipeline
    from qa.answer import answer_question

    result = await answer_question(body.question, doc["full_text"], doc_id)
    return result


@app.get("/api/documents/{doc_id}/brief.pdf")
async def get_lawyer_brief(doc_id: str):
    """
    Generate and download the Lawyer Prep Brief PDF.
    """
    doc = get_document(doc_id)
    if not doc:
        raise HTTPException(404, f"Document {doc_id} not found")

    analysis = get_analysis(doc_id)
    if not analysis:
        raise HTTPException(400, "Document has not been analyzed yet. Run /analyze first.")

    from outputs.lawyer_brief import generate_brief_pdf

    pdf_path = generate_brief_pdf(doc_id, doc["full_text"], analysis)
    return FileResponse(
        pdf_path,
        media_type="application/pdf",
        filename=f"lawyer_brief_{doc_id}.pdf",
    )


@app.post("/api/documents/{doc_id}/redline", response_model=RedlineResponse)
async def generate_redline(doc_id: str):
    """
    Generate suggested redlines and a negotiation email draft
    for high-risk clauses.
    """
    doc = get_document(doc_id)
    if not doc:
        raise HTTPException(404, f"Document {doc_id} not found")

    analysis = get_analysis(doc_id)
    if not analysis:
        raise HTTPException(400, "Document has not been analyzed yet. Run /analyze first.")

    from outputs.redline import generate_redlines

    result = await generate_redlines(analysis, doc["full_text"])
    return result


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "mock_mode": MOCK_LLM}


# ─── Production Frontend Static Serving ────────────────────────────
from fastapi.staticfiles import StaticFiles

# Look for built frontend in static/ or frontend/dist
DIST_DIR = Path(__file__).parent.parent / "static"
if not DIST_DIR.exists():
    DIST_DIR = Path(__file__).parent.parent / "frontend" / "dist"

if DIST_DIR.exists():
    app.mount("/", StaticFiles(directory=str(DIST_DIR), html=True), name="static")

    @app.exception_handler(404)
    async def spa_404_handler(request, exc):
        """Fallback to index.html for client-side routing on non-API routes."""
        if not request.url.path.startswith("/api"):
            index_file = DIST_DIR / "index.html"
            if index_file.exists():
                return FileResponse(index_file)
        return JSONResponse({"detail": "Not Found"}, status_code=404)

