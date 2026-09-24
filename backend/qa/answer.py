"""
FinePrint — Grounded Q&A with Abstention

Answers questions about the uploaded document using only
the document's content. Must abstain when the document
does not contain the answer.

Every answer runs through verify.py before returning.
"""

from __future__ import annotations

import json
import logging

import numpy as np

from schemas import QAResponse, Citation, Span

logger = logging.getLogger(__name__)


async def answer_question(
    question: str, full_text: str, doc_id: str
) -> QAResponse:
    """
    Answer a question grounded in the document.

    Steps:
    1. Retrieve top-k relevant clauses by embedding similarity
    2. LLM call constrained to answer ONLY from retrieved clauses
    3. If document doesn't contain the answer → abstain
    4. Every answer runs through verification

    Args:
        question: User's question
        full_text: Full document text
        doc_id: Document ID for analysis lookup

    Returns:
        QAResponse with answer, citations, and abstention flag
    """
    from llm.client import embed, cosine_similarity, complete_with_retry
    from llm.prompts.qa import SYSTEM, build_user
    from db import get_analysis

    # Get clauses from stored analysis
    analysis = get_analysis(doc_id)
    if not analysis:
        return QAResponse(
            answer="This document has not been analyzed yet. Please run the analysis first.",
            citations=[],
            abstained=True,
        )

    clauses = analysis.get("clauses", [])
    if not clauses:
        return QAResponse(
            answer="No clauses were identified in this document.",
            citations=[],
            abstained=True,
        )

    import re

    # Embed question and clause texts
    question_embedding = await embed([question])
    clause_texts = [c.get("text", "") for c in clauses]
    clause_embeddings = await embed(clause_texts)

    similarities = cosine_similarity(question_embedding, clause_embeddings)[0]

    # Keyword overlap scoring
    stop_words = {
        "what", "is", "the", "are", "my", "your", "this", "that", "there", "a", "an", "and", "or",
        "in", "on", "at", "to", "for", "of", "with", "by", "from", "about", "does", "do", "did",
        "can", "could", "would", "should", "will", "shall", "any", "how", "much", "many", "tell",
        "me", "explain", "i", "we", "they", "it", "its"
    }
    q_words = {w for w in re.findall(r"\w+", question.lower()) if w not in stop_words and len(w) > 2}

    scored_clauses = []
    for idx, clause in enumerate(clauses):
        c_text = clause.get("text", "").lower()
        c_heading = (clause.get("heading") or "").lower()
        c_type = (clause.get("type") or "").lower().replace("_", " ")

        overlap = sum(1 for w in q_words if w in c_text or w in c_heading or w in c_type)
        kw_score = overlap / max(1, len(q_words)) if q_words else 0.0
        sem_score = float(similarities[idx])
        hybrid_score = 0.5 * sem_score + 0.5 * kw_score

        # Clause is relevant if it has keyword overlap or strong semantic match
        is_relevant = (overlap >= 1 and len(q_words) > 0) or (sem_score >= 0.20)
        scored_clauses.append((idx, hybrid_score, is_relevant))

    # Sort descending by hybrid score
    scored_clauses.sort(key=lambda x: x[1], reverse=True)

    relevant_candidates = [sc for sc in scored_clauses if sc[2]]
    k = min(5, len(relevant_candidates))
    top_candidates = relevant_candidates[:k]

    # Build context with relevant clauses
    relevant_clauses = [
        {"id": clauses[idx]["id"], "text": clauses[idx]["text"]}
        for idx, _, _ in top_candidates
    ]

    if not relevant_clauses:
        return QAResponse(
            answer="This document does not contain information to answer that question.",
            citations=[],
            abstained=True,
        )

    # LLM call
    user_msg = build_user(question, relevant_clauses)

    try:
        result = await complete_with_retry(SYSTEM, user_msg, retries=1)

        if isinstance(result, str):
            text = result.strip()
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            result = json.loads(text.strip())

        abstained = result.get("abstained", False)
        answer_text = result.get("answer", "")
        cited_ids = result.get("cited_clause_ids", [])

        # Build citations from cited clause IDs
        citations: list[Citation] = []
        clause_map = {c.get("id"): c for c in clauses}

        for cid in cited_ids:
            clause = clause_map.get(cid)
            if clause:
                span_data = clause.get("span", {})
                citations.append(Citation(
                    kind="document",
                    span=Span(
                        start=span_data.get("start", 0),
                        end=span_data.get("end", 0),
                        page=span_data.get("page"),
                    ),
                    quote=clause.get("text", ""),
                ))

        # Verify citations against full text
        if not abstained and citations:
            from analyze.verify import verify_single_citation
            verified_citations = [
                c for c in citations
                if verify_single_citation(full_text, c)
            ]
            citations = verified_citations

        return QAResponse(
            answer=answer_text,
            citations=citations if not abstained else [],
            abstained=abstained,
        )

    except Exception as e:
        logger.error(f"Q&A failed: {e}")
        return QAResponse(
            answer="An error occurred while processing your question. Please try again.",
            citations=[],
            abstained=True,
        )
