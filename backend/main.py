"""
FinePrint — FastAPI Application

Production-grade legal AI assistant backend.
Implements:
- Strict security controls (file size limits, path sanitization, magic bytes, security headers)
- High-efficiency GZip compression and asset caching
- Modern FastAPI lifespan context manager
- Grounded Position Report generation under Indian statutory law
"""

from __future__ import annotations

import json
import os
import re
import sys
import uuid
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

# Ensure backend directory is in sys.path
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(Path(__file__).parent.parent / ".env")

from fastapi import FastAPI, File, UploadFile, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from schemas import (
    AnalysisResponse,
    QARequest,
    QAResponse,
    RedlineResponse,
    UploadResponse,
    PageMapEntry,
)
from db import init_db, store_document, get_document, store_analysis, get_analysis

# ─── Setup & Lifespan ─────────────────────────────────────────────

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MOCK_LLM = os.getenv("MOCK_LLM", "0") == "1"
FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"
DATA_DIR = Path(__file__).parent.parent / "data"

# Maximum upload size: 15 Megabytes
MAX_UPLOAD_SIZE = 15 * 1024 * 1024
DOC_ID_REGEX = re.compile(r"^[a-zA-Z0-9_-]{3,64}$")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Modern lifespan handler: initialize DB and cache on startup."""
    init_db()
    logger.info("FinePrint API started")
    if MOCK_LLM:
        logger.info("⚠️  Running in MOCK_LLM mode — returning fixture data")
    yield


app = FastAPI(
    title="FinePrint — Legal AI Assistant",
    description="Analyzes legal documents and produces grounded Position Reports under Indian law",
    version="0.2.0",
    lifespan=lifespan,
)

# ─── Security & Efficiency Middleware ─────────────────────────────

# 1. GZip Compression Middleware (efficiency: compresses network payloads > 1000 bytes)
app.add_middleware(GZipMiddleware, minimum_size=1000)

# 2. CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


# 3. HTTP Security Headers & Cache-Control Middleware
@app.middleware("http")
async def security_and_cache_middleware(request: Request, call_next):
    """Enforce defense-in-depth HTTP security headers and asset caching."""
    response = await call_next(request)
    # Security headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

    # Static assets caching efficiency
    path = request.url.path
    if path.startswith("/assets/"):
        response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
    elif path == "/" or path.endswith(".html"):
        response.headers["Cache-Control"] = "no-cache, must-revalidate"

    return response


# ─── Helper Functions ─────────────────────────────────────────────

def _load_fixture(name: str) -> dict:
    path = FIXTURES_DIR / f"{name}.json"
    if not path.exists():
        raise HTTPException(500, f"Fixture {name} not found")
    return json.loads(path.read_text(encoding="utf-8"))


def _validate_doc_id(doc_id: str):
    """Ensure doc_id conforms to safe format to prevent injection attacks."""
    if not DOC_ID_REGEX.match(doc_id):
        raise HTTPException(400, "Invalid document ID format.")


def _validate_file_signature(content: bytes, ext: str) -> bool:
    """Validate magic bytes / file signature to prevent executable file disguises."""
    if not content:
        return False
    if ext == ".pdf":
        return content.startswith(b"%PDF")
    elif ext in (".jpg", ".jpeg"):
        return content.startswith(b"\xff\xd8\xff")
    elif ext == ".png":
        return content.startswith(b"\x89PNG\r\n\x1a\n")
    elif ext in (".docx", ".doc"):
        # DOCX is a zip file (PK\x03\x04), legacy DOC is OLE CFB (\xd0\xcf\x11\xe0)
        return content.startswith(b"PK\x03\x04") or content.startswith(b"\xd0\xcf\x11\xe0")
    elif ext in (".txt", ".text"):
        try:
            content[:1024].decode("utf-8")
            return True
        except UnicodeDecodeError:
            return False
    return True


# ─── API Routes ───────────────────────────────────────────────────

@app.post("/api/documents", response_model=UploadResponse)
async def upload_document(file: UploadFile = File(...)):
    """
    Securely upload a legal document (PDF, DOCX, TXT, or image).
    Validates file size (max 15MB), sanitizes filename, and checks magic bytes.
    """
    if not file.filename:
        raise HTTPException(400, "No file provided")

    # Sanitize filename against directory traversal
    safe_filename = re.sub(r"[^a-zA-Z0-9_.-]", "_", Path(file.filename).name)

    # Validate file type extension
    allowed_extensions = {
        ".pdf", ".docx", ".doc", ".txt", ".text",
        ".png", ".jpg", ".jpeg", ".tiff", ".bmp",
    }
    ext = Path(safe_filename).suffix.lower()
    if ext not in allowed_extensions:
        raise HTTPException(
            400,
            f"Unsupported file type: {ext}. Accepted: {', '.join(sorted(allowed_extensions))}"
        )

    # Enforce strict file size limit (15 MB)
    content = await file.read(MAX_UPLOAD_SIZE + 1)
    if len(content) > MAX_UPLOAD_SIZE:
        raise HTTPException(
            413,
            f"File too large. Maximum allowed size is {MAX_UPLOAD_SIZE // (1024 * 1024)} MB."
        )

    # Validate file magic bytes signature
    if not _validate_file_signature(content, ext):
        raise HTTPException(
            400,
            f"Corrupted or invalid file signature for {ext} format."
        )

    doc_id = f"doc-{uuid.uuid4().hex[:8]}"

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

    store_document(doc_id, safe_filename, full_text)

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
    obligations, and verified findings.
    """
    _validate_doc_id(doc_id)
    doc = get_document(doc_id)
    if not doc:
        raise HTTPException(404, f"Document {doc_id} not found")

    full_text = doc["full_text"]

    # In MOCK_LLM mode, return fixture data with correct doc_id
    if MOCK_LLM:
        fixture = _load_fixture("analysis_response")
        fixture["document_id"] = doc_id
        store_analysis(doc_id, fixture)
        return fixture

    # Real analysis pipeline
    from segment.clauses import segment_document
    from analyze.baseline import compare_baselines
    from analyze.statute import check_enforceability
    from analyze.obligations import extract_obligations
    from analyze.findings import synthesize_findings
    from analyze.verify import verify_findings
    from db import store_clauses

    clauses = await segment_document(full_text, doc_id)
    store_clauses(doc_id, clauses)

    baseline_verdicts = await compare_baselines(clauses)
    enforceability_flags = await check_enforceability(clauses)
    obligations = await extract_obligations(clauses, full_text)

    raw_findings = await synthesize_findings(
        clauses, baseline_verdicts, enforceability_flags, obligations, full_text
    )

    verified_findings = verify_findings(raw_findings, full_text, clauses)

    result = AnalysisResponse(
        document_id=doc_id,
        clauses=clauses,
        baseline_verdicts=baseline_verdicts,
        enforceability_flags=enforceability_flags,
        obligations=obligations,
        findings=verified_findings,
    )

    store_analysis(doc_id, result.model_dump())
    return result


@app.post("/api/documents/{doc_id}/ask", response_model=QAResponse)
async def ask_question(doc_id: str, body: QARequest):
    """
    Grounded Q&A: answer questions about a document using only its content.
    Abstains cleanly when the answer is not contained in the text.
    """
    _validate_doc_id(doc_id)
    doc = get_document(doc_id)
    if not doc:
        raise HTTPException(404, f"Document {doc_id} not found")

    from qa.answer import answer_question

    result = await answer_question(body.question, doc["full_text"], doc_id)
    return result


@app.get("/api/documents/{doc_id}/brief.pdf")
async def get_lawyer_brief(doc_id: str):
    """Generate and stream the Lawyer Prep Brief PDF."""
    _validate_doc_id(doc_id)
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
    """Generate suggested redlines and negotiation email draft for high-risk clauses."""
    _validate_doc_id(doc_id)
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
    """Health check endpoint with security status."""
    return {
        "status": "ok",
        "mock_mode": MOCK_LLM,
        "max_upload_mb": MAX_UPLOAD_SIZE // (1024 * 1024),
    }


# ─── Production Frontend Static Serving ────────────────────────────

# Look for built frontend in frontend/dist or static/
DIST_DIR = Path(__file__).parent.parent / "frontend" / "dist"
if not DIST_DIR.exists():
    DIST_DIR = Path(__file__).parent.parent / "static"

if DIST_DIR.exists():
    app.mount("/", StaticFiles(directory=str(DIST_DIR), html=True), name="static")

    @app.exception_handler(404)
    async def spa_404_handler(request: Request, exc):
        """Fallback to index.html for client-side routing on non-API routes."""
        if not request.url.path.startswith("/api"):
            index_file = DIST_DIR / "index.html"
            if index_file.exists():
                return FileResponse(index_file)
        return JSONResponse({"detail": "Not Found"}, status_code=404)
