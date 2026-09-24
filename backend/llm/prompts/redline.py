"""
FinePrint — Redline Generation Prompt

Generates suggested clause changes and a negotiation email.
Tone: professional, non-adversarial, non-accusatory.
"""

SYSTEM = """You are a legal drafting assistant. For each problematic clause,
suggest an alternative text and a rationale.

Return a JSON object with:
{
  "redlines": [
    {
      "clause_id": string,
      "current_text": string,
      "suggested_text": string,
      "rationale": string
    }
  ],
  "email_draft": string
}

Rules for redlines:
- Suggested text should be a complete replacement for the clause
- Rationale should explain why the change is beneficial
- Changes should be reasonable and balanced, not one-sided

Rules for the email:
- Professional, polite, non-adversarial, non-accusatory tone
- Cover the top 3 most significant issues
- Frame requests as discussion points, not demands
- Include a warm opening acknowledging the offer
- End with a collaborative closing

Return ONLY the JSON object. No prose, no markdown fences.
Do not use imperative language like "you should" or "you must"."""


def build_user(high_risk_clauses: list[dict], baseline_verdicts: list[dict]) -> str:
    """Build user message for redline generation."""
    lines = ["Generate redlines and a negotiation email for these clauses:\n"]
    for clause in high_risk_clauses:
        verdict_info = ""
        for bv in baseline_verdicts:
            if bv.get("clause_id") == clause["id"]:
                verdict_info = f" (Baseline verdict: {bv.get('verdict', 'unknown')})"
                break
        lines.append(
            f'[{clause["id"]}] Risk: {clause.get("risk_score", "?")}/5{verdict_info}\n'
            f'{clause["text"]}\n'
        )
    return "\n".join(lines)
