"""Content-policy post-check and the scripted guardrail evaluation (no model)."""

import csv
import sys

import pytest

from app.services.rag_lite.answer import unsupported_claim
from scripts import evaluate_rag_generation


@pytest.mark.parametrize(
    "text",
    [
        "The dam is currently safe at 42.5 m.",
        "Operators should keep the crest at 42.5 m.",
        "Real-time level is 42.5 m.",
        "We recommend inspection.",
        "The spillway will overflow.",
        "Hiện nay đập an toàn.",
        "Dự báo đập ổn định.",
    ],
)
def test_present_safety_and_advice_claims_are_unsupported(text):
    assert unsupported_claim(text)


@pytest.mark.parametrize(
    "text",
    [
        "The historical crest elevation is 42.5 m.",
        "Nền đập là đất đắp đồng chất.",
        "The design summary is known to describe earthfill.",
        "Cao trình đỉnh đập lịch sử là 42,5 m.",
    ],
)
def test_historical_statements_are_allowed(text):
    assert not unsupported_claim(text)


def test_scripted_guardrail_evaluation_passes(tmp_path, monkeypatch):
    output = tmp_path / "guardrails.csv"
    monkeypatch.setattr(sys, "argv", ["evaluate", "--output", str(output)])
    assert evaluate_rag_generation.main() == 0
    rows = list(csv.DictReader(output.open()))
    assert len(rows) == 21 and all(row["passed"] == "True" for row in rows)
    by_id = {row["case_id"]: row for row in rows}
    assert by_id["R15"]["provider_called"] == "0"
    assert by_id["R16"]["status"] == "ANSWERED"  # documented residual risk
