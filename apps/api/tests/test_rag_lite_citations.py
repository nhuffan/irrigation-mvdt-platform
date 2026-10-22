from uuid import uuid4

import pytest

from app.schemas.rag_lite import Citation, RagQuery
from app.services.rag_lite.answer import respond
from app.services.rag_lite.citations import validate_generation


@pytest.fixture
def evidence():
    return [
        Citation(
            citation_id="server-issued",
            kind="document_chunk",
            source_id=uuid4(),
            source_code="TEST",
            document_id=uuid4(),
            page=9,
            locator="PDF:p9",
            url="/documents/test",
            title="Synthetic",
            excerpt="Historical value 270 bar",
            source_status="UNVERIFIED",
        )
    ]


@pytest.mark.parametrize(
    "output",
    [
        {"answer": "270 bar [invented]", "citation_ids": ["invented"]},
        {"answer": "270 bar", "citation_ids": ["server-issued"]},
        {"answer": "270 bar [invented]", "citation_ids": ["server-issued"]},
        {
            "answer": "https://fake.example [server-issued]",
            "citation_ids": ["server-issued"],
        },
        {"answer": "<script> [server-issued]", "citation_ids": ["server-issued"]},
        {"answer": "", "citation_ids": []},
        {
            "answer": "270 [server-issued]",
            "citation_ids": ["server-issued"],
            "url": "/fake",
        },
    ],
)
def test_reject_fabricated_citations(output, evidence):
    with pytest.raises(ValueError):
        validate_generation(output, evidence)


def request():
    return RagQuery(
        question="pressure",
        reservoir_id=uuid4(),
        asset_id=uuid4(),
        mode="grounded_answer",
    )


def test_empty_evidence_and_disabled_provider(evidence):
    assert respond(request(), [], []).status == "NOT_ENOUGH_EVIDENCE"
    result = respond(request(), evidence, [])
    assert result.status == "GENERATION_UNAVAILABLE" and result.answer is None
    assert result.citations == evidence


@pytest.mark.parametrize("failure", [TimeoutError, ValueError, RuntimeError])
def test_provider_failure_falls_back(evidence, failure):
    class Failing:
        def generate(self, prompt, *, timeout):
            raise failure("sensitive provider error")

    result = respond(request(), evidence, [], Failing())
    assert (
        result.status == "GENERATION_UNAVAILABLE"
        and "sensitive" not in result.model_dump_json()
    )


def test_network_free_grounded_adapter_and_untrusted_prompt(evidence):
    class Mock:
        def generate(self, prompt, *, timeout):
            assert "untrusted data" in prompt and timeout == 10
            assert "270 bar" in prompt
            return {
                "answer": "Historical value: 270 bar [server-issued]",
                "citation_ids": ["server-issued"],
            }

    result = respond(request(), evidence, [], Mock())
    assert result.status == "ANSWERED" and result.citations == evidence
    assert (
        respond(request(), evidence, [], Mock(), max_context_chars=1).status
        == "GENERATION_UNAVAILABLE"
    )
