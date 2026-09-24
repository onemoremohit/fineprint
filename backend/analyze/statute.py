"""
FinePrint — Statute Enforceability Analysis

Matches clauses against the curated statute knowledge base.
Only loads entries with verified_by populated — enforced in code.

CRITICAL: Agents must NOT generate, invent, or expand legal provisions.
Only uses entries present in data/statutes/*.json.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import numpy as np

from schemas import Clause, EnforceabilityFlag, Citation

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent.parent / "data"
STATUTES_DIR = DATA_DIR / "statutes"
CACHE_DIR = DATA_DIR / "cache"
MISSING_LOG = STATUTES_DIR / "MISSING.md"

# In-memory cache
_statute_entries: list[dict] = []
_statute_embeddings: np.ndarray | None = None


def _load_statute_files() -> list[dict]:
    """
    Load all statute entries from JSON files.
    CRITICAL: Only load entries with verified_by populated.
    """
    entries = []

    if not STATUTES_DIR.exists():
        logger.warning(f"Statutes directory not found: {STATUTES_DIR}")
        return entries

    for json_path in STATUTES_DIR.glob("*.json"):
        try:
            data = json.loads(json_path.read_text(encoding="utf-8"))
            if isinstance(data, list):
                for entry in data:
                    if _is_verified(entry):
                        entries.append(entry)
                    else:
                        logger.info(
                            f"Skipping unverified statute entry: "
                            f"{entry.get('id', 'unknown')} from {json_path.name}"
                        )
            elif isinstance(data, dict):
                if _is_verified(data):
                    entries.append(data)
        except Exception as e:
            logger.error(f"Failed to load statute file {json_path}: {e}")

    logger.info(f"Loaded {len(entries)} verified statute entries")
    return entries


def _is_verified(entry: dict) -> bool:
    """
    Check if a statute entry has been verified.
    Entries without verified_by must be excluded — this is enforced here.
    """
    verified_by = entry.get("verified_by")
    return bool(verified_by and verified_by.strip())


async def _load_statutes():
    """Load and embed statute entries on first use."""
    global _statute_entries, _statute_embeddings

    if _statute_entries:
        return

    _statute_entries = _load_statute_files()

    if not _statute_entries:
        logger.warning("No verified statute entries loaded")
        return

    # Try cached embeddings
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path = CACHE_DIR / "statute_embeddings.npy"

    if cache_path.exists():
        _statute_embeddings = np.load(str(cache_path))
        if _statute_embeddings.shape[0] == len(_statute_entries):
            logger.info("Loaded cached statute embeddings")
            return

    # Embed statute texts
    from llm.client import embed

    texts = [
        f"{entry.get('heading', '')} {entry.get('bare_text', '')} {entry.get('plain_summary', '')}"
        for entry in _statute_entries
    ]
    _statute_embeddings = await embed(texts)
    np.save(str(cache_path), _statute_embeddings)
    logger.info("Computed and cached statute embeddings")


def _log_missing(clause_type: str, clause_text: str):
    """Log a missing statute entry to MISSING.md."""
    STATUTES_DIR.mkdir(parents=True, exist_ok=True)
    with open(MISSING_LOG, "a", encoding="utf-8") as f:
        f.write(f"\n- **{clause_type}**: Needed for clause starting with: "
                f'"{clause_text[:80]}..."\n')


async def check_enforceability(clauses: list[Clause]) -> list[EnforceabilityFlag]:
    """
    Check clause enforceability against the statute knowledge base.

    Strategy:
    1. Match on applies_to_clause_types FIRST
    2. Then rank by embedding similarity
    3. Only entries with verified_by are loaded (enforced at load time)

    Confidence rule:
    - high: clause_type in statute's applies_to_clause_types AND similarity > 0.7
    - medium: clause_type matches but similarity ≤ 0.7
    - low: similarity match only, or unclear application

    Returns:
        List of EnforceabilityFlag objects (only for flagged clauses)
    """
    await _load_statutes()

    if not _statute_entries or _statute_embeddings is None:
        return []

    from llm.client import embed, cosine_similarity

    # Embed clause texts
    clause_texts = [c.text for c in clauses]
    clause_embeddings = await embed(clause_texts)

    flags: list[EnforceabilityFlag] = []

    for i, clause in enumerate(clauses):
        # Step 1: Filter by applies_to_clause_types
        type_matched_indices = [
            j for j, entry in enumerate(_statute_entries)
            if clause.type.value in entry.get("applies_to_clause_types", [])
        ]

        # Step 2: Rank by embedding similarity
        if type_matched_indices:
            filtered_embeddings = _statute_embeddings[type_matched_indices]
            similarities = cosine_similarity(
                clause_embeddings[i:i+1], filtered_embeddings
            )[0]

            best_local_idx = int(np.argmax(similarities))
            best_similarity = float(similarities[best_local_idx])
            best_global_idx = type_matched_indices[best_local_idx]
            best_entry = _statute_entries[best_global_idx]

            # Collect all statute IDs that apply to this clause type
            all_matched_statutes = [_statute_entries[idx] for idx in type_matched_indices]

            # Determine confidence
            if best_similarity > 0.7:
                confidence = "high"
            elif best_similarity > 0.5:
                confidence = "medium"
            else:
                confidence = "low"

            # Build the flag
            flag = _build_flag(clause, best_entry, confidence, all_matched_statutes)
            if flag:
                flags.append(flag)

        else:
            # Try similarity-only match across all statutes
            all_similarities = cosine_similarity(
                clause_embeddings[i:i+1], _statute_embeddings
            )[0]

            best_idx = int(np.argmax(all_similarities))
            best_sim = float(all_similarities[best_idx])

            if best_sim > 0.6:
                best_entry = _statute_entries[best_idx]
                flag = _build_flag(clause, best_entry, "low")
                if flag:
                    flags.append(flag)
            else:
                # No matching statute — log to MISSING.md if clause seems risky
                if clause.risk_score >= 3:
                    _log_missing(clause.type.value, clause.text)

    return flags


def _build_flag(
    clause: Clause,
    statute: dict,
    confidence: str,
    all_matched_statutes: list[dict] | None = None,
) -> EnforceabilityFlag | None:
    """Build an EnforceabilityFlag from a clause + matched statute entry."""
    effect = statute.get("effect", "unclear")
    if effect not in (
        "likely_unenforceable", "limited_enforceability",
        "likely_enforceable", "unclear"
    ):
        effect = "unclear"

    # Build explanation from statute data
    explanation_parts = [statute.get("plain_summary", "")]
    caveats = statute.get("caveats", [])
    if caveats:
        explanation_parts.append("Caveats: " + "; ".join(caveats))

    # ask_a_lawyer must always be non-empty
    ask_a_lawyer = [
        f"Whether {statute.get('heading', 'this provision')} applies to your specific situation",
        "Whether any state-specific legislation provides additional protections",
        "What the practical enforcement implications would be in your jurisdiction",
    ]

    statute_ids = [statute["id"]]
    if all_matched_statutes:
        for s in all_matched_statutes:
            sid = s.get("id")
            if sid and sid not in statute_ids:
                statute_ids.append(sid)

    return EnforceabilityFlag(
        clause_id=clause.id,
        status=effect,
        statute_ids=statute_ids,
        explanation=" ".join(explanation_parts),
        ask_a_lawyer=ask_a_lawyer,
        confidence=confidence,
    )
