"""
FinePrint — Gold Set Generator

Synthesizes 25 distinct legal documents with ground truth labels for:
- Clause boundaries and headings
- Clause types (ClauseType enum)
- Risk scores
- Obligations
- Unanswerable questions (for abstention testing)
"""

import json
from pathlib import Path

GOLD_DIR = Path(__file__).parent / "gold"
GOLD_DIR.mkdir(parents=True, exist_ok=True)

TEMPLATES = [
    {
        "title": "Senior Software Engineer Offer Letter",
        "company": "Infosolutions Global Pvt. Ltd.",
        "role": "Senior Software Engineer",
        "salary": "INR 18,00,000",
        "probation": "six (6) months",
        "notice": "90 days",
        "bond_amount": "INR 2,50,000",
        "bond_period": "2 years",
        "non_compete_period": "12 months",
        "jurisdiction": "Bengaluru, Karnataka",
    },
    {
        "title": "Graduate Trainee Bond and Appointment",
        "company": "Vertex Tech Services Ltd.",
        "role": "Graduate Engineer Trainee",
        "salary": "INR 4,50,000",
        "probation": "twelve (12) months",
        "notice": "60 days",
        "bond_amount": "INR 3,00,000",
        "bond_period": "3 years",
        "non_compete_period": "24 months",
        "jurisdiction": "Hyderabad, Telangana",
    },
    {
        "title": "Product Marketing Lead Agreement",
        "company": "Apex Digital Innovations Pvt. Ltd.",
        "role": "Product Marketing Lead",
        "salary": "INR 22,00,000",
        "probation": "three (3) months",
        "notice": "30 days",
        "bond_amount": None,
        "bond_period": None,
        "non_compete_period": "6 months",
        "jurisdiction": "Mumbai, Maharashtra",
    },
    {
        "title": "Cloud Infrastructure Consultant Contract",
        "company": "CloudSphere Solutions India",
        "role": "Senior Cloud Consultant",
        "salary": "INR 26,00,000",
        "probation": "three (3) months",
        "notice": "45 days",
        "bond_amount": None,
        "bond_period": None,
        "non_compete_period": "12 months",
        "jurisdiction": "Pune, Maharashtra",
    },
    {
        "title": "Data Science Associate Offer Letter",
        "company": "QuantPulse Analytics India Pvt. Ltd.",
        "role": "Data Scientist",
        "salary": "INR 14,00,000",
        "probation": "six (6) months",
        "notice": "60 days",
        "bond_amount": "INR 1,50,000",
        "bond_period": "18 months",
        "non_compete_period": "12 months",
        "jurisdiction": "Gurugram, Haryana",
    },
]

# Expand to 25 variations with varying attributes
ALL_CONFIGS = []
for idx in range(25):
    base = TEMPLATES[idx % len(TEMPLATES)]
    variant = dict(base)
    variant["index"] = idx + 1
    variant["doc_id"] = f"gold-{idx + 1:03d}"
    if idx >= len(TEMPLATES):
        variant["title"] = f"{base['role']} Agreement — Tier {idx // 5}"
        variant["company"] = f"Enterprise Horizon {idx + 1} Pvt. Ltd."
    ALL_CONFIGS.append(variant)


def build_document(cfg: dict) -> dict:
    parts = []
    clauses = []
    obligations = []
    
    header = f"{cfg['title'].upper()}\n\nDate: 10th February 2025\nCompany: {cfg['company']}\nRole: {cfg['role']}\n\n"
    current_offset = len(header)
    
    # 1. Compensation
    c1_title = "1. Compensation and Benefits"
    c1_body = f"The Company shall pay the Employee a total compensation of {cfg['salary']} per annum, payable in monthly instalments subject to statutory tax deductions."
    c1_full = f"{c1_title}\n{c1_body}\n\n"
    c1_start = current_offset
    c1_end = c1_start + len(c1_full.strip())
    clauses.append({
        "heading": c1_title,
        "text": c1_full.strip(),
        "start": c1_start,
        "end": c1_end,
        "type": "compensation",
        "risk_score": 1,
    })
    obligations.append({
        "party": "counterparty",
        "action": f"Pay compensation of {cfg['salary']} per annum",
        "amount": cfg['salary'],
    })
    current_offset += len(c1_full)
    
    # 2. Probation
    c2_title = "2. Probationary Period"
    c2_body = f"The Employee shall remain on probation for {cfg['probation']} from the date of joining. Performance will be reviewed prior to confirmation."
    c2_full = f"{c2_title}\n{c2_body}\n\n"
    c2_start = current_offset
    c2_end = c2_start + len(c2_full.strip())
    clauses.append({
        "heading": c2_title,
        "text": c2_full.strip(),
        "start": c2_start,
        "end": c2_end,
        "type": "probation",
        "risk_score": 2,
    })
    current_offset += len(c2_full)
    
    # 3. Notice Period
    c3_title = "3. Notice Period and Separation"
    c3_body = f"Following confirmation, either party may terminate employment by providing {cfg['notice']} written notice or basic salary in lieu thereof."
    c3_full = f"{c3_title}\n{c3_body}\n\n"
    c3_start = current_offset
    c3_end = c3_start + len(c3_full.strip())
    clauses.append({
        "heading": c3_title,
        "text": c3_full.strip(),
        "start": c3_start,
        "end": c3_end,
        "type": "notice_period",
        "risk_score": 2,
    })
    obligations.append({
        "party": "user",
        "action": f"Provide {cfg['notice']} notice upon resignation",
    })
    current_offset += len(c3_full)
    
    # 4. Training Bond (if applicable)
    if cfg.get("bond_amount"):
        c4_title = "4. Service Commitment and Training Bond"
        c4_body = f"The Employee agrees to remain in service for at least {cfg['bond_period']} following completion of training. In the event of breach, Employee shall pay {cfg['bond_amount']} as liquidated damages."
        c4_full = f"{c4_title}\n{c4_body}\n\n"
        c4_start = current_offset
        c4_end = c4_start + len(c4_full.strip())
        clauses.append({
            "heading": c4_title,
            "text": c4_full.strip(),
            "start": c4_start,
            "end": c4_end,
            "type": "training_bond",
            "risk_score": 4,
        })
        obligations.append({
            "party": "user",
            "action": f"Pay liquidated damages of {cfg['bond_amount']} if resigning before {cfg['bond_period']}",
            "amount": cfg['bond_amount'],
        })
        current_offset += len(c4_full)
    
    # 5. Non-Compete
    c5_title = "5. Restrictive Covenant and Non-Compete"
    c5_body = f"For {cfg['non_compete_period']} following termination, the Employee agrees not to solicit clients or be employed by competing firms in India."
    c5_full = f"{c5_title}\n{c5_body}\n\n"
    c5_start = current_offset
    c5_end = c5_start + len(c5_full.strip())
    clauses.append({
        "heading": c5_title,
        "text": c5_full.strip(),
        "start": c5_start,
        "end": c5_end,
        "type": "non_compete",
        "risk_score": 5,
    })
    current_offset += len(c5_full)
    
    # 6. Confidentiality and IP Assignment
    c6_title = "6. Confidentiality and Intellectual Property"
    c6_body = "All discoveries, software source codes, designs, and inventions created shall remain the exclusive proprietary property of the Company."
    c6_full = f"{c6_title}\n{c6_body}\n\n"
    c6_start = current_offset
    c6_end = c6_start + len(c6_full.strip())
    clauses.append({
        "heading": c6_title,
        "text": c6_full.strip(),
        "start": c6_start,
        "end": c6_end,
        "type": "ip_assignment",
        "risk_score": 2,
    })
    current_offset += len(c6_full)
    
    # 7. Governing Law
    c7_title = "7. Governing Law and Jurisdiction"
    c7_body = f"This contract shall be construed in accordance with the laws of India. Courts at {cfg['jurisdiction']} have exclusive jurisdiction."
    c7_full = f"{c7_title}\n{c7_body}\n\n"
    c7_start = current_offset
    c7_end = c7_start + len(c7_full.strip())
    clauses.append({
        "heading": c7_title,
        "text": c7_full.strip(),
        "start": c7_start,
        "end": c7_end,
        "type": "jurisdiction",
        "risk_score": 1,
    })
    current_offset += len(c7_full)
    
    footer = "Sincerely,\nAuthorised Signatory\n" + cfg["company"]
    
    full_text = header + "".join([c["text"] + "\n\n" for c in clauses]) + footer
    
    # Exact start/end offsets recalculated directly on final string
    for c in clauses:
        idx = full_text.find(c["text"])
        assert idx != -1, f"Failed to locate clause text: {c['text'][:30]}"
        c["start"] = idx
        c["end"] = idx + len(c["text"])
        # Verify invariant
        assert full_text[c["start"]:c["end"]] == c["text"]
    
    unanswerable = [
        f"Does {cfg['company']} provide free hot lunch in the office cafeteria?",
        "What is the maternity leave stipend granted after 3 years?",
        f"Can employees bring pet rabbits to the {cfg['jurisdiction']} office?",
        "What was the annual audited gross revenue of the company?",
        "Is free rooftop helicopter parking offered to engineers?",
    ]
    
    return {
        "doc_id": cfg["doc_id"],
        "title": cfg["title"],
        "full_text": full_text,
        "clauses": clauses,
        "obligations": obligations,
        "unanswerable_questions": unanswerable,
    }


def main():
    print(f"Generating 25 gold standard documents in {GOLD_DIR}...")
    for cfg in ALL_CONFIGS:
        doc = build_document(cfg)
        out_path = GOLD_DIR / f"{doc['doc_id']}.json"
        out_path.write_text(json.dumps(doc, indent=2), encoding="utf-8")
    print("Successfully generated 25 gold standard benchmark documents.")


if __name__ == "__main__":
    main()
