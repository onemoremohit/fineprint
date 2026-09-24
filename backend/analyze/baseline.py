"""
FinePrint — Baseline Comparison ("Is This Normal?")

Retrieves the nearest baseline entry for each clause (same clause_type)
and produces a verdict: standard, stricter_than_usual, unusual, or no_baseline.

Uses brute-force cosine similarity over numpy arrays — correct and fast
for the small corpus size.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import numpy as np

from schemas import Clause, BaselineVerdict, Citation, Span

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent.parent / "data"
BASELINE_PATH = DATA_DIR / "baselines" / "employment.json"
CACHE_DIR = DATA_DIR / "cache"

# Similarity threshold — below this, no meaningful comparison is possible
SIMILARITY_THRESHOLD = 0.55

# In-memory cache
_baseline_entries: list[dict] = []
_baseline_embeddings: np.ndarray | None = None


async def _load_baselines():
    """Load and embed baseline entries on first use."""
    global _baseline_entries, _baseline_embeddings

    if _baseline_entries:
        return  # Already loaded

    if not BASELINE_PATH.exists():
        logger.warning(f"Baseline file not found: {BASELINE_PATH}")
        return

    _baseline_entries = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
    logger.info(f"Loaded {len(_baseline_entries)} baseline entries")

    # Try to load cached embeddings
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path = CACHE_DIR / "baseline_embeddings.npy"

    if cache_path.exists():
        _baseline_embeddings = np.load(str(cache_path))
        if _baseline_embeddings.shape[0] == len(_baseline_entries):
            logger.info("Loaded cached baseline embeddings")
            return
        else:
            logger.info("Cache size mismatch, re-embedding")

    # Embed all baseline texts
    from llm.client import embed

    texts = [entry["canonical_text"] for entry in _baseline_entries]
    _baseline_embeddings = await embed(texts)

    # Cache to disk
    np.save(str(cache_path), _baseline_embeddings)
    logger.info("Computed and cached baseline embeddings")


async def compare_baselines(clauses: list[Clause]) -> list[BaselineVerdict]:
    """
    Compare each clause against baseline entries of the same type.

    For each clause:
    1. Filter baselines to same clause_type
    2. Find nearest by cosine similarity
    3. If similarity < threshold → no_baseline
    4. Otherwise, LLM call produces verdict + explanation

    Returns:
        List of BaselineVerdict objects
    """
    await _load_baselines()

    if not _baseline_entries or _baseline_embeddings is None:
        return [
            BaselineVerdict(
                clause_id=c.id,
                verdict="no_baseline",
                explanation="No baseline corpus available for comparison.",
                citations=[],
            )
            for c in clauses
        ]

    from llm.client import embed, cosine_similarity
    from llm.client import complete_with_retry
    from llm.prompts.baseline import SYSTEM, build_user

    # Embed all clause texts
    clause_texts = [c.text for c in clauses]
    clause_embeddings = await embed(clause_texts)

    verdicts: list[BaselineVerdict] = []

    for i, clause in enumerate(clauses):
        # Filter baselines to same clause type
        type_indices = [
            j for j, entry in enumerate(_baseline_entries)
            if entry.get("clause_type") == clause.type.value
        ]

        if not type_indices:
            verdicts.append(BaselineVerdict(
                clause_id=clause.id,
                verdict="no_baseline",
                explanation=f"No baseline entries exist for clause type '{clause.type.value}'.",
                citations=[],
            ))
            continue

        # Compute similarity against type-filtered baselines
        filtered_embeddings = _baseline_embeddings[type_indices]
        similarities = cosine_similarity(
            clause_embeddings[i:i+1], filtered_embeddings
        )[0]

        best_local_idx = int(np.argmax(similarities))
        best_similarity = float(similarities[best_local_idx])
        best_global_idx = type_indices[best_local_idx]
        best_entry = _baseline_entries[best_global_idx]

        if best_similarity < SIMILARITY_THRESHOLD:
            verdicts.append(BaselineVerdict(
                clause_id=clause.id,
                verdict="no_baseline",
                explanation=(
                    f"The closest baseline entry has low similarity "
                    f"({best_similarity:.2f}). No reliable comparison available."
                ),
                citations=[],
            ))
            continue

        # LLM call to produce verdict
        try:
            user_msg = build_user(
                clause.text,
                best_entry["canonical_text"],
                best_entry.get("typical_range", "Not specified"),
                best_entry.get("stricter_signals", []),
            )

            result = await complete_with_retry(SYSTEM, user_msg, retries=1)

            if isinstance(result, str):
                result = json.loads(result.strip().strip("```").strip("json").strip())

            verdict_str = result.get("verdict", "standard")
            if verdict_str not in ("standard", "stricter_than_usual", "unusual"):
                verdict_str = "standard"

            verdicts.append(BaselineVerdict(
                clause_id=clause.id,
                verdict=verdict_str,
                baseline_id=best_entry["id"],
                baseline_text=best_entry["canonical_text"],
                explanation=result.get("explanation", ""),
                citations=[
                    Citation(
                        kind="document",
                        span=Span(
                            start=clause.span.start,
                            end=clause.span.end,
                            page=clause.span.page,
                        ),
                        quote=clause.text,
                    )
                ],
            ))

        except Exception as e:
            logger.error(f"Baseline comparison failed for clause {clause.id}: {e}")
            verdicts.append(BaselineVerdict(
                clause_id=clause.id,
                verdict="no_baseline",
                explanation=f"Comparison could not be completed: {str(e)}",
                citations=[],
            ))

    return verdicts
