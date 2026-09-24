"""
FinePrint — Clause Segmentation

Rule-first, model-second approach to segmenting raw text into clauses
with exact character offsets.

CRITICAL INVARIANT:
    full_text[clause.span.start:clause.span.end] == clause.text
    This is asserted in code. Mismatch raises an error.
"""

from __future__ import annotations

import re
import logging
from typing import Optional

from schemas import Clause, Span, ClauseType

logger = logging.getLogger(__name__)

# ─── Heading Patterns (rule-first) ───────────────────────────────

HEADING_PATTERNS = [
    # "1." or "1.1" or "1.1.1" at start of line
    re.compile(r"^(\d+\.(?:\d+\.?)*)\s+(.+)", re.MULTILINE),
    # "(a)" or "(i)" or "(1)" at start of line
    re.compile(r"^\(([a-z]|\d+|[ivxlc]+)\)\s+(.+)", re.MULTILINE),
    # "ARTICLE I" or "ARTICLE III" etc.
    re.compile(r"^(ARTICLE\s+[IVXLC]+)\s*[:\.\-]?\s*(.*)", re.MULTILINE | re.IGNORECASE),
    # "Section 1" or "Clause 1"
    re.compile(r"^((?:Section|Clause|Article)\s+\d+)\s*[:\.\-]?\s*(.*)", re.MULTILINE | re.IGNORECASE),
    # "SCHEDULE" or "ANNEXURE"
    re.compile(r"^((?:SCHEDULE|ANNEXURE|APPENDIX)\s*[A-Z0-9]*)\s*[:\.\-]?\s*(.*)", re.MULTILINE | re.IGNORECASE),
    # All-caps headings (e.g., "NOTICE PERIOD", "TRAINING BOND")
    re.compile(r"^([A-Z][A-Z\s]{4,})\s*$", re.MULTILINE),
]

# Keywords that often appear as clause headings
HEADING_KEYWORDS = {
    "compensation", "salary", "remuneration", "probation", "notice period",
    "notice", "termination", "training bond", "bond", "non-compete",
    "non compete", "non-solicitation", "non solicitation", "confidentiality",
    "intellectual property", "ip assignment", "dispute resolution",
    "jurisdiction", "arbitration", "indemnity", "penalty", "liquidated damages",
    "working hours", "leave", "benefits", "amendment", "severability",
    "governing law", "entire agreement", "force majeure", "assignment",
}


async def segment_clauses(full_text: str) -> list[Clause]:
    """
    Segment raw document text into clauses with exact character offsets.

    Uses a rule-first approach:
    1. Detect clause boundaries using heading patterns
    2. Split on detected boundaries
    3. Assign headings
    4. Verify all offsets match

    Args:
        full_text: Complete document text

    Returns:
        List of Clause objects with verified character offsets
    """
    if not full_text.strip():
        return []

    # Step 1: Find all potential clause boundaries
    boundaries = _find_boundaries(full_text)

    if not boundaries:
        # Fallback: split on double newlines
        boundaries = _split_on_blank_lines(full_text)

    if not boundaries:
        # Last resort: treat entire text as one clause
        boundaries = [(0, len(full_text), None)]

    # Step 2: Create clause objects
    clauses = []
    for idx, (start, end, heading) in enumerate(boundaries):
        text = full_text[start:end].strip()
        if not text or len(text) < 10:
            # Skip very short fragments
            continue

        # Find the exact position of the stripped text in full_text
        actual_start = full_text.find(text, max(0, start - 5))
        if actual_start == -1:
            actual_start = start
        actual_end = actual_start + len(text)

        clause = Clause(
            id=f"c-{idx + 1:03d}",
            index=idx,
            heading=heading,
            text=text,
            span=Span(start=actual_start, end=actual_end, page=None),
            type=ClauseType.OTHER,
            burden_on="unclear",
            risk_score=1,
            risk_reasons=[],
        )

        # CRITICAL: Verify offset invariant
        _verify_offset(full_text, clause)

        clauses.append(clause)

    # Step 3: Try to assign page numbers if we know page boundaries
    # (this happens later when we have the page_map)

    # Step 4: Try LLM-based refinement if we have few clauses
    if len(clauses) < 3 and len(full_text) > 500:
        logger.info("Few clauses detected, attempting LLM-based segmentation...")
        try:
            refined = await _llm_refine_clauses(full_text, clauses)
            if refined and len(refined) > len(clauses):
                clauses = refined
        except Exception as e:
            logger.warning(f"LLM refinement failed: {e}, using rule-based results")

    logger.info(f"Segmented document into {len(clauses)} clauses")
    return clauses


def _find_boundaries(
    full_text: str,
) -> list[tuple[int, int, Optional[str]]]:
    """
    Find clause boundaries using heading pattern matching.

    Returns list of (start, end, heading) tuples.
    """
    # Collect all heading positions
    heading_positions: list[tuple[int, str]] = []

    for pattern in HEADING_PATTERNS:
        for match in pattern.finditer(full_text):
            pos = match.start()
            # Extract heading text
            groups = match.groups()
            if len(groups) >= 2:
                heading = f"{groups[0].strip()} {groups[1].strip()}".strip()
            else:
                heading = groups[0].strip()
            heading_positions.append((pos, heading))

    # Also look for keyword-based headings (lines that are mostly a heading keyword)
    for line_match in re.finditer(r"^(.+)$", full_text, re.MULTILINE):
        line_text = line_match.group(1).strip().lower()
        # Remove numbering prefixes
        clean = re.sub(r"^\d+[\.\)]\s*", "", line_text)
        clean = re.sub(r"^[a-z][\.\)]\s*", "", clean)

        for keyword in HEADING_KEYWORDS:
            if clean == keyword or clean.startswith(keyword + ":"):
                heading_positions.append((line_match.start(), line_match.group(1).strip()))
                break

    if not heading_positions:
        return []

    # Sort by position and deduplicate (keep the one closest to line start)
    heading_positions.sort(key=lambda x: x[0])

    # Remove duplicates that are too close together
    deduped: list[tuple[int, str]] = []
    for pos, heading in heading_positions:
        if not deduped or pos - deduped[-1][0] > 20:
            deduped.append((pos, heading))

    # Create boundary tuples
    boundaries: list[tuple[int, int, Optional[str]]] = []
    for i, (pos, heading) in enumerate(deduped):
        start = pos
        if i + 1 < len(deduped):
            end = deduped[i + 1][0]
        else:
            end = len(full_text)
        boundaries.append((start, end, heading))

    return boundaries


def _split_on_blank_lines(
    full_text: str,
) -> list[tuple[int, int, Optional[str]]]:
    """
    Fallback: split text on double newlines (blank lines).
    """
    boundaries: list[tuple[int, int, Optional[str]]] = []
    # Split on 2+ consecutive newlines
    parts = re.split(r"\n\s*\n", full_text)

    offset = 0
    for part in parts:
        if part.strip():
            # Find actual position in full_text
            start = full_text.find(part.strip(), offset)
            if start == -1:
                start = offset
            end = start + len(part.strip())

            # Try to extract heading from first line
            first_line = part.strip().split("\n")[0].strip()
            heading = first_line if len(first_line) < 60 else None

            boundaries.append((start, end, heading))
            offset = end

    return boundaries


async def _llm_refine_clauses(
    full_text: str, existing_clauses: list[Clause]
) -> list[Clause]:
    """
    Use LLM to refine clause segmentation for ambiguous documents.

    IMPORTANT: After LLM produces clause boundaries, we re-derive
    offsets by searching the original text. Never trust LLM offsets.
    """
    from llm.client import complete_with_retry

    system = """You are a legal document parser. Given the text of a legal document,
identify each distinct clause or section.

Return a JSON array of objects, each with:
- "heading": the clause heading/title (or null if none)
- "first_words": the first 10-15 words of the clause text (exact match required)
- "last_words": the last 10-15 words of the clause text (exact match required)

Rules:
- Each clause should be a logically distinct provision
- Do not split sub-clauses from their parent unless they address a clearly different topic
- Include preamble/recitals as a separate entry if present
- If the text does not support an answer, return an empty array

Return ONLY the JSON array, no other text."""

    # Only send first 8000 chars to limit cost
    truncated = full_text[:8000]

    try:
        result = await complete_with_retry(system, truncated)
        if isinstance(result, str):
            import json
            # Try to parse JSON from response
            result = result.strip()
            if result.startswith("```"):
                result = result.split("```")[1]
                if result.startswith("json"):
                    result = result[4:]
            items = json.loads(result)
        else:
            items = result

        if not isinstance(items, list):
            return existing_clauses

        refined: list[Clause] = []
        for idx, item in enumerate(items):
            first_words = item.get("first_words", "")
            last_words = item.get("last_words", "")
            heading = item.get("heading")

            # Re-derive offsets from original text
            start = full_text.find(first_words)
            if start == -1:
                continue

            if last_words:
                last_pos = full_text.find(last_words, start)
                if last_pos == -1:
                    # Try to find end by searching for the next clause's start
                    end = start + 500  # fallback
                else:
                    end = last_pos + len(last_words)
            else:
                end = start + 500

            end = min(end, len(full_text))
            text = full_text[start:end].strip()

            # Re-find exact match for the stripped text
            actual_start = full_text.find(text, max(0, start - 5))
            if actual_start == -1:
                actual_start = start
            actual_end = actual_start + len(text)

            clause = Clause(
                id=f"c-{idx + 1:03d}",
                index=idx,
                heading=heading,
                text=text,
                span=Span(start=actual_start, end=actual_end, page=None),
                type=ClauseType.OTHER,
                burden_on="unclear",
                risk_score=1,
                risk_reasons=[],
            )

            _verify_offset(full_text, clause)
            refined.append(clause)

        return refined if refined else existing_clauses

    except Exception as e:
        logger.warning(f"LLM clause refinement failed: {e}")
        return existing_clauses


def _verify_offset(full_text: str, clause: Clause):
    """
    CRITICAL: Verify that the clause text matches the span in full_text.
    This is the most important invariant in the system.
    """
    extracted = full_text[clause.span.start:clause.span.end]
    if extracted != clause.text:
        # Try to fix by searching for the text
        idx = full_text.find(clause.text)
        if idx != -1:
            clause.span.start = idx
            clause.span.end = idx + len(clause.text)
            logger.warning(
                f"Fixed offset mismatch for clause {clause.id}: "
                f"was ({clause.span.start}, {clause.span.end}), "
                f"corrected to ({idx}, {idx + len(clause.text)})"
            )
        else:
            raise ValueError(
                f"CRITICAL: Offset mismatch for clause {clause.id}. "
                f"full_text[{clause.span.start}:{clause.span.end}] != clause.text. "
                f"Got: '{extracted[:50]}...', Expected: '{clause.text[:50]}...'"
            )


def assign_pages(clauses: list[Clause], page_map: list[tuple[int, int, int]]):
    """
    Assign page numbers to clauses based on the page map.

    Args:
        clauses: List of clauses to update
        page_map: List of (page_no, start_offset, end_offset) tuples
    """
    for clause in clauses:
        for page_no, page_start, page_end in page_map:
            if clause.span.start >= page_start and clause.span.start < page_end:
                clause.span.page = page_no
                break
