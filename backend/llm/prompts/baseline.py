"""
FinePrint — Baseline Comparison Prompt

Compares a clause against a baseline entry to determine
if it is standard, stricter than usual, or unusual.
"""

SYSTEM = """You are a legal analyst comparing an employment agreement clause
against a baseline (typical) clause of the same type.

Return a JSON object with:
{
  "verdict": "standard" | "stricter_than_usual" | "unusual",
  "explanation": string (one sentence explaining why)
}

Rules:
- "standard" means the clause is within normal range
- "stricter_than_usual" means it imposes greater obligations than typical
- "unusual" means it contains provisions rarely seen in standard agreements
- Base your comparison ONLY on the clause text and baseline provided
- Do not use outside knowledge
- Return ONLY the JSON object. No prose, no markdown fences.
- If the provided text does not support a comparison, return {"verdict": "standard", "explanation": "Unable to determine meaningful differences from the baseline."}"""


def build_user(clause_text: str, baseline_text: str, typical_range: str, stricter_signals: list[str]) -> str:
    """Build user message for baseline comparison."""
    signals = "\n".join(f"  - {s}" for s in stricter_signals) if stricter_signals else "  (none specified)"
    return f"""Clause from document:
{clause_text}

Baseline (typical clause):
{baseline_text}

Typical range: {typical_range}

Known signals that indicate stricter-than-usual:
{signals}

Compare the document clause against the baseline and determine the verdict."""
