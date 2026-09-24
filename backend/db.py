"""
FinePrint — SQLite Database Module

High-performance SQLite storage for documents and analyses.
Configured with WAL mode, normalized memory cache, and relational indexing.
No ORM overhead — stdlib sqlite3 with parameterized queries only.
"""

from __future__ import annotations

import json
import sqlite3
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).parent.parent / "data" / "app.db"


def _get_conn() -> sqlite3.Connection:
    """Get a tuned, fast database connection with row factory and WAL mode."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), timeout=20.0)
    conn.row_factory = sqlite3.Row
    # Performance & concurrency optimizations
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    conn.execute("PRAGMA cache_size = -32000;")  # 32 MB in-memory cache
    conn.execute("PRAGMA temp_store = MEMORY;")
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db():
    """Create tables and performance indices if they don't exist."""
    conn = _get_conn()
    try:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS documents (
                id TEXT PRIMARY KEY,
                filename TEXT NOT NULL,
                full_text TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS clauses (
                id TEXT PRIMARY KEY,
                document_id TEXT NOT NULL,
                index_num INTEGER NOT NULL,
                heading TEXT,
                text TEXT NOT NULL,
                span_start INTEGER NOT NULL,
                span_end INTEGER NOT NULL,
                page INTEGER,
                type TEXT NOT NULL DEFAULT 'other',
                burden_on TEXT NOT NULL DEFAULT 'unclear',
                risk_score INTEGER NOT NULL DEFAULT 1,
                risk_reasons TEXT NOT NULL DEFAULT '[]',
                FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS analyses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id TEXT NOT NULL UNIQUE,
                result_json TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
            );

            -- Indices for O(1) document and analysis lookups
            CREATE INDEX IF NOT EXISTS idx_clauses_doc_id ON clauses(document_id);
            CREATE INDEX IF NOT EXISTS idx_clauses_risk ON clauses(risk_score);
            CREATE INDEX IF NOT EXISTS idx_analyses_doc_id ON analyses(document_id);
        """)
        conn.commit()
        logger.info(f"Database initialized with WAL & indexes at {DB_PATH}")
    finally:
        conn.close()


def store_document(doc_id: str, filename: str, full_text: str):
    """Store an uploaded document using safe parameterized queries."""
    conn = _get_conn()
    try:
        conn.execute(
            "INSERT OR REPLACE INTO documents (id, filename, full_text) VALUES (?, ?, ?)",
            (doc_id, filename, full_text),
        )
        conn.commit()
    finally:
        conn.close()


def get_document(doc_id: str) -> Optional[dict]:
    """Retrieve a document by ID."""
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT id, filename, full_text, created_at FROM documents WHERE id = ?",
            (doc_id,),
        ).fetchone()
        if not row:
            return None
        return dict(row)
    finally:
        conn.close()


def store_clauses(doc_id: str, clauses: list):
    """Store segmented clauses for a document in a single atomic transaction."""
    conn = _get_conn()
    try:
        with conn:
            conn.execute("DELETE FROM clauses WHERE document_id = ?", (doc_id,))
            conn.executemany(
                """
                INSERT INTO clauses
                (id, document_id, index_num, heading, text, span_start, span_end, page,
                 type, burden_on, risk_score, risk_reasons)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        c.id if hasattr(c, "id") else c["id"],
                        doc_id,
                        c.index if hasattr(c, "index") else c.get("index", 0),
                        c.heading if hasattr(c, "heading") else c.get("heading"),
                        c.text if hasattr(c, "text") else c["text"],
                        c.span.start if hasattr(c, "span") else c["span"]["start"],
                        c.span.end if hasattr(c, "span") else c["span"]["end"],
                        c.span.page if hasattr(c, "span") else c.get("span", {}).get("page"),
                        c.type if hasattr(c, "type") else c.get("type", "other"),
                        c.burden_on if hasattr(c, "burden_on") else c.get("burden_on", "unclear"),
                        c.risk_score if hasattr(c, "risk_score") else c.get("risk_score", 1),
                        json.dumps(c.risk_reasons if hasattr(c, "risk_reasons") else c.get("risk_reasons", [])),
                    )
                    for c in clauses
                ],
            )
    finally:
        conn.close()


def store_analysis(doc_id: str, analysis: dict):
    """Store the full analysis result as JSON."""
    conn = _get_conn()
    try:
        with conn:
            conn.execute(
                "INSERT OR REPLACE INTO analyses (document_id, result_json) VALUES (?, ?)",
                (doc_id, json.dumps(analysis)),
            )
    finally:
        conn.close()


def get_analysis(doc_id: str) -> Optional[dict]:
    """Retrieve an analysis result by document ID."""
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT result_json FROM analyses WHERE document_id = ?",
            (doc_id,),
        ).fetchone()
        if not row:
            return None
        return json.loads(row["result_json"])
    finally:
        conn.close()
