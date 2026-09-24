"""
FinePrint — Fixture Validation Tests

Validates all fixture JSON files against Pydantic models.
Ensures the data contract is maintained from Phase 0 onward.
"""

import json
import sys
from pathlib import Path

import pytest

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from schemas import (
    AnalysisResponse,
    QAResponse,
    RedlineResponse,
)

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


class TestAnalysisFixture:
    """Validate the analysis_response.json fixture."""

    @pytest.fixture
    def fixture_data(self):
        path = FIXTURES_DIR / "analysis_response.json"
        return json.loads(path.read_text(encoding="utf-8"))

    def test_parses_as_analysis_response(self, fixture_data):
        """The fixture must parse into a valid AnalysisResponse."""
        response = AnalysisResponse(**fixture_data)
        assert response.document_id == "doc-001"

    def test_has_clauses(self, fixture_data):
        response = AnalysisResponse(**fixture_data)
        assert len(response.clauses) >= 5, "Fixture should have at least 5 clauses"

    def test_clause_types_valid(self, fixture_data):
        response = AnalysisResponse(**fixture_data)
        for clause in response.clauses:
            assert clause.type is not None
            assert 1 <= clause.risk_score <= 5

    def test_has_baseline_verdicts(self, fixture_data):
        response = AnalysisResponse(**fixture_data)
        assert len(response.baseline_verdicts) > 0

    def test_has_enforceability_flags(self, fixture_data):
        response = AnalysisResponse(**fixture_data)
        assert len(response.enforceability_flags) > 0
        for flag in response.enforceability_flags:
            # ask_a_lawyer must always be non-empty
            assert len(flag.ask_a_lawyer) > 0

    def test_has_obligations(self, fixture_data):
        response = AnalysisResponse(**fixture_data)
        assert len(response.obligations) > 0

    def test_has_findings(self, fixture_data):
        response = AnalysisResponse(**fixture_data)
        assert len(response.findings) > 0
        # Check all three tiers exist
        tiers = {f.tier for f in response.findings}
        assert "document_says" in tiers
        assert "general_law" in tiers
        assert "option" in tiers

    def test_no_imperative_in_option_tier(self, fixture_data):
        """Option-tier findings must not use imperative phrasing."""
        response = AnalysisResponse(**fixture_data)
        banned = ["you should", "you must", "do not sign", "you need to"]
        for finding in response.findings:
            if finding.tier == "option":
                body_lower = finding.body.lower()
                for phrase in banned:
                    assert phrase not in body_lower, (
                        f"Finding {finding.id} uses banned imperative phrase: '{phrase}'"
                    )

    def test_non_compete_flagged(self, fixture_data):
        """The non-compete clause should be flagged as likely_unenforceable."""
        response = AnalysisResponse(**fixture_data)
        non_compete_flags = [
            f for f in response.enforceability_flags
            if any(
                c.type.value == "non_compete"
                for c in response.clauses
                if c.id == f.clause_id
            )
        ]
        assert len(non_compete_flags) > 0
        assert non_compete_flags[0].status == "likely_unenforceable"
        assert "ica-s27" in non_compete_flags[0].statute_ids


class TestQAFixture:
    """Validate the qa_responses.json fixture."""

    @pytest.fixture
    def fixture_data(self):
        path = FIXTURES_DIR / "qa_responses.json"
        return json.loads(path.read_text(encoding="utf-8"))

    def test_parses_all_responses(self, fixture_data):
        for item in fixture_data:
            response = QAResponse(**item["response"])
            assert isinstance(response.answer, str)
            assert isinstance(response.abstained, bool)

    def test_has_abstention_examples(self, fixture_data):
        """Must include at least one abstention example."""
        abstained = [
            item for item in fixture_data if item["response"]["abstained"]
        ]
        assert len(abstained) >= 1

    def test_abstained_responses_have_no_document_citations(self, fixture_data):
        """Abstained responses should not cite the document."""
        for item in fixture_data:
            if item["response"]["abstained"]:
                doc_citations = [
                    c for c in item["response"]["citations"]
                    if c["kind"] == "document"
                ]
                assert len(doc_citations) == 0


class TestRedlineFixture:
    """Validate the redline_response.json fixture."""

    @pytest.fixture
    def fixture_data(self):
        path = FIXTURES_DIR / "redline_response.json"
        return json.loads(path.read_text(encoding="utf-8"))

    def test_parses_as_redline_response(self, fixture_data):
        response = RedlineResponse(**fixture_data)
        assert len(response.redlines) > 0
        assert len(response.email_draft) > 0

    def test_redlines_have_rationale(self, fixture_data):
        response = RedlineResponse(**fixture_data)
        for redline in response.redlines:
            assert redline.rationale, f"Redline for {redline.clause_id} missing rationale"

    def test_email_is_professional_tone(self, fixture_data):
        response = RedlineResponse(**fixture_data)
        email = response.email_draft.lower()
        # Should not contain aggressive language
        aggressive = ["demand", "threaten", "unacceptable", "refuse"]
        for word in aggressive:
            assert word not in email, f"Email contains aggressive word: '{word}'"
