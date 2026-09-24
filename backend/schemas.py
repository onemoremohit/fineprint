"""
FinePrint — Core Data Schemas

All Pydantic v2 models that form the contract between every module.
Defined once in Phase 0 — every consumer depends on these.
"""

from __future__ import annotations

import enum
from typing import Literal

from pydantic import BaseModel, Field


# ─── Clause Taxonomy ─────────────────────────────────────────────

class ClauseType(str, enum.Enum):
    COMPENSATION = "compensation"
    NOTICE_PERIOD = "notice_period"
    PROBATION = "probation"
    TRAINING_BOND = "training_bond"
    NON_COMPETE = "non_compete"
    NON_SOLICIT = "non_solicit"
    CONFIDENTIALITY = "confidentiality"
    IP_ASSIGNMENT = "ip_assignment"
    TERMINATION = "termination"
    PENALTY_LIQUIDATED_DAMAGES = "penalty_liquidated_damages"
    INDEMNITY = "indemnity"
    DISPUTE_RESOLUTION = "dispute_resolution"
    JURISDICTION = "jurisdiction"
    ARBITRATION = "arbitration"
    WORKING_HOURS = "working_hours"
    LEAVE = "leave"
    BENEFITS = "benefits"
    AMENDMENT = "amendment"
    SEVERABILITY = "severability"
    OTHER = "other"


# ─── Core Value Objects ──────────────────────────────────────────

class Span(BaseModel):
    """Character-offset span into document.full_text"""
    start: int = Field(..., description="Start char offset into full_text")
    end: int = Field(..., description="End char offset into full_text")
    page: int | None = Field(None, description="Page number (0-indexed)")


class Citation(BaseModel):
    """
    A grounded reference — either to a span in the source document
    or to an entry in the curated statute knowledge base.
    """
    kind: Literal["document", "statute"]
    span: Span | None = Field(
        None, description="Required when kind == 'document'"
    )
    statute_id: str | None = Field(
        None, description="Required when kind == 'statute'"
    )
    quote: str = Field(
        ...,
        description="Must equal full_text[start:end] for document kind"
    )


class Clause(BaseModel):
    """A segmented clause from the document with exact offsets."""
    id: str = Field(..., description='e.g. "c-014"')
    index: int
    heading: str | None = None
    text: str
    span: Span
    type: ClauseType = ClauseType.OTHER
    burden_on: Literal["user", "counterparty", "mutual", "unclear"] = "unclear"
    risk_score: int = Field(1, ge=1, le=5)
    risk_reasons: list[str] = Field(default_factory=list)


# ─── Analysis Results ────────────────────────────────────────────

class BaselineVerdict(BaseModel):
    """Comparison of a clause against the baseline corpus."""
    clause_id: str
    verdict: Literal["standard", "stricter_than_usual", "unusual", "no_baseline"]
    baseline_id: str | None = None
    baseline_text: str | None = None
    explanation: str
    citations: list[Citation] = Field(default_factory=list)


class EnforceabilityFlag(BaseModel):
    """Enforceability assessment of a clause under Indian law."""
    clause_id: str
    status: Literal[
        "likely_unenforceable",
        "limited_enforceability",
        "likely_enforceable",
        "unclear"
    ]
    statute_ids: list[str] = Field(default_factory=list)
    explanation: str
    ask_a_lawyer: list[str] = Field(
        ...,
        min_length=1,
        description="Non-empty list — always present"
    )
    confidence: Literal["high", "medium", "low"] = "low"


class Obligation(BaseModel):
    """A date, deadline, notice window, or financial duty extracted from the doc."""
    clause_id: str
    who: Literal["user", "counterparty"]
    what: str
    due: str | None = Field(
        None, description="ISO date or relative expression"
    )
    trigger: str | None = Field(
        None, description='e.g. "on resignation", "30 days before renewal"'
    )
    amount_inr: float | None = None
    citations: list[Citation] = Field(default_factory=list)


class Finding(BaseModel):
    """The unit shown in the UI — a single insight with grounded citations."""
    id: str
    title: str
    tier: Literal["document_says", "general_law", "option"]
    body: str
    clause_ids: list[str] = Field(default_factory=list)
    citations: list[Citation] = Field(default_factory=list)
    verified: bool = False


# ─── Redline Models ──────────────────────────────────────────────

class Redline(BaseModel):
    """A suggested change to a clause."""
    clause_id: str
    current_text: str
    suggested_text: str
    rationale: str


# ─── API Request / Response Models ───────────────────────────────

class PageMapEntry(BaseModel):
    """Maps page numbers to character offset ranges."""
    page_no: int
    start: int
    end: int


class UploadResponse(BaseModel):
    """Response from POST /api/documents"""
    document_id: str
    full_text: str
    pages: list[PageMapEntry]


class AnalysisResponse(BaseModel):
    """Response from POST /api/documents/{id}/analyze"""
    document_id: str
    clauses: list[Clause]
    baseline_verdicts: list[BaselineVerdict]
    enforceability_flags: list[EnforceabilityFlag]
    obligations: list[Obligation]
    findings: list[Finding]


class QARequest(BaseModel):
    """Request body for POST /api/documents/{id}/ask"""
    question: str


class QAResponse(BaseModel):
    """Response from POST /api/documents/{id}/ask"""
    answer: str
    citations: list[Citation] = Field(default_factory=list)
    abstained: bool = False


class RedlineResponse(BaseModel):
    """Response from POST /api/documents/{id}/redline"""
    redlines: list[Redline]
    email_draft: str
