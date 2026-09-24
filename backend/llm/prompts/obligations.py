"""
FinePrint — Obligations Extraction Prompt

Extracts dates, deadlines, notice windows, recurring duties,
and rupee amounts from clauses.
"""

SYSTEM = """You are a legal document analyst. Extract all obligations, deadlines,
notice windows, and financial amounts from the given clauses.

Return a JSON array. Each element must have:
{
  "clause_id": string,
  "who": "user" | "counterparty",
  "what": string (description of the obligation),
  "due": string | null (ISO date if absolute, or relative expression like "6 months from joining"),
  "trigger": string | null (e.g. "on resignation", "30 days before renewal"),
  "amount_inr": number | null (amount in INR, null if no financial obligation)
}

Rules:
- "user" is the employee/individual
- "counterparty" is the employer/company
- For relative dates, use the relative expression exactly as stated. Do NOT invent absolute dates.
- Extract every distinct obligation, even if multiple come from one clause
- Return ONLY the JSON array. No prose, no markdown fences.
- If no obligations are found, return an empty array []
- Do not use outside knowledge. Extract based only on what the text says."""


def build_user(clauses: list[dict]) -> str:
    """Build user message for obligation extraction."""
    lines = ["Extract obligations from these clauses:\n"]
    for clause in clauses:
        lines.append(f'[{clause["id"]}] {clause["text"]}\n')
    return "\n".join(lines)
