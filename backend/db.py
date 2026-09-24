"""
FinePrint — SQLite Database Module

Simple SQLite storage for documents and analyses.
No ORM — stdlib sqlite3 only.
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
    """Get a database connection with row factory."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create tables if they don't exist."""
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
                FOREIGN KEY (document_id) REFERENCES documents(id)
            );

            CREATE TABLE IF NOT EXISTS analyses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id TEXT NOT NULL UNIQUE,
                result_json TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (document_id) REFERENCES documents(id)
            );
        """)
        conn.commit()
        logger.info(f"Database initialized at {DB_PATH}")
    finally:
        conn.close()


def store_document(doc_id: str, filename: str, full_text: str):
    """Store an uploaded document."""
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
            "SELECT id, filename, full_text FROM documents WHERE id = ?",
            (doc_id,),
        ).fetchone()
        if row:
            return {"id": row["id"], "filename": row["filename"], "full_text": row["full_text"]}
        return None
    finally:
        conn.close()


def store_analysis(doc_id: str, result: dict):
    """Store analysis results for a document."""
    conn = _get_conn()
    try:
        conn.execute(
            "INSERT OR REPLACE INTO analyses (document_id, result_json) VALUES (?, ?)",
            (doc_id, json.dumps(result)),
        )
        conn.commit()
    finally:
        conn.close()


def get_analysis(doc_id: str) -> Optional[dict]:
    """Retrieve analysis results for a document."""
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT result_json FROM analyses WHERE document_id = ?",
            (doc_id,),
        ).fetchone()
        if row:
            return json.loads(row["result_json"])
        return None
    finally:
        conn.close()
