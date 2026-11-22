"""Hosted (Claude) provider gate, adapter and answer trace. No network calls."""

import json
from types import SimpleNamespace

import anthropic
import pytest

from app.services.rag_lite import generation, providers
from tests.test_rag_lite_generation import (  # noqa: F401 - pytest fixtures
    FakeProvider,
    provider,
    retrieval,
    scope,
)


def hosted(scope, *, app_env="demo", classification="SYNTHETIC_DEMO"):  # noqa: F811
    settings, request, record, _document, grant = scope
    settings.rag_provider = "anthropic"
    settings.rag_anthropic_model = "claude-haiku-5-5"
    settings.app_env = app_env
    grant.update(provider="anthropic", model="claude-haiku-5-5")
    if classification is not None:
        grant["data_classification"] = classification
    settings.rag_generation_authorization_path.write_text(json.dumps(grant))
    return settings, request, record


def test_hosted_provider_answers_only_for_synthetic_demo(scope, provider):  # noqa: F811
    settings, request, record = hosted(scope)
    result = generation.grounded_response(settings, request, retrieval(record))
    assert result.status == "ANSWERED"
    assert result.trace.provider == "anthropic"
    assert result.trace.model == "claude-haiku-5-5"


@pytest.mark.parametrize(
    ("app_env", "classification"),
    [("development", "SYNTHETIC_DEMO"), ("demo", "PRIVATE"), ("demo", None)],
)
def test_hosted_provider_never_sees_private_or_non_demo_evidence(
    scope,  # noqa: F811
    provider,  # noqa: F811
    app_env,
    classification,
):
    settings, request, record = hosted(
        scope, app_env=app_env, classification=classification
    )
    result = generation.grounded_response(settings, request, retrieval(record))
    assert result.status == "GENERATION_UNAVAILABLE"
    assert provider.calls == []
    assert result.citations == [record]
    authorization = next(c for c in result.trace.checks if c.name == "authorization")
    assert authorization.status == "failed"


def test_trace_records_each_passed_check_without_content(scope, provider):  # noqa: F811
    settings, request, record, _, _ = scope
    result = generation.grounded_response(settings, request, retrieval(record))
    trace = result.trace
    assert [c.status for c in trace.checks] == ["passed"] * 8
    assert trace.aliases == ["E1"] and trace.evidence_sent == 1
    assert trace.latency_ms is not None
    dumped = trace.model_dump_json()
    assert "Test witnessed on site" not in dumped
    assert record.citation_id not in dumped


@pytest.mark.parametrize(
    ("output", "failed"),
    [
        ({"answer": "Historical: 999 bar [E1]", "citation_ids": ["E1"]}, "numbers"),
        ({"answer": "Historical: 270 psi [E1]", "citation_ids": ["E1"]}, "units"),
        (
            {"answer": "It is safe at 270 bar today [E1]", "citation_ids": ["E1"]},
            "content_policy",
        ),
        ({"answer": "Historical: 270 bar [E9]", "citation_ids": ["E9"]}, "citations"),
        (RuntimeError("down"), "model_output"),
    ],
)
def test_trace_names_the_failed_check(scope, provider, output, failed):  # noqa: F811
    settings, request, record, _, _ = scope
    provider.output = output
    result = generation.grounded_response(settings, request, retrieval(record))
    assert result.status == "GENERATION_UNAVAILABLE"
    statuses = {c.name: c.status for c in result.trace.checks}
    assert statuses[failed] == "failed"
    order = [c.name for c in result.trace.checks]
    assert all(statuses[name] == "skipped" for name in order[order.index(failed) + 1 :])


def test_trace_without_evidence_never_calls_model(scope, provider):  # noqa: F811
    settings, request, _, _, _ = scope
    result = generation.grounded_response(settings, request, retrieval())
    assert provider.calls == []
    assert result.trace.checks[0].name == "retrieval"
    assert result.trace.checks[0].status == "failed"


class FakeMessages:
    def __init__(self, response):
        self.response = response
        self.kwargs = None

    def create(self, **kwargs):
        self.kwargs = kwargs
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


def fake_client(monkeypatch, response):
    messages = FakeMessages(response)
    monkeypatch.setattr(
        anthropic, "Anthropic", lambda **_: SimpleNamespace(messages=messages)
    )
    return messages


PROMPT = json.dumps(
    [
        {"role": "system", "content": "rules"},
        {"role": "user", "content": '{"question":"q","evidence":[]}'},
    ]
)


def test_claude_adapter_uses_structured_output_and_no_tools(monkeypatch):
    text = SimpleNamespace(
        type="text", text='{"answer":"a [E1]","citation_ids":["E1"]}'
    )
    messages = fake_client(
        monkeypatch, SimpleNamespace(stop_reason="end_turn", content=[text])
    )
    result = providers.AnthropicProvider("claude-haiku-5-5").generate(PROMPT, timeout=5)
    assert result == {"answer": "a [E1]", "citation_ids": ["E1"]}
    kwargs = messages.kwargs
    assert kwargs["model"] == "claude-haiku-5-5"
    assert kwargs["system"] == "rules"
    assert [m["role"] for m in kwargs["messages"]] == ["user"]
    assert kwargs["output_config"]["format"]["schema"] == (
        providers.CLOUD_RESPONSE_SCHEMA
    )
    assert "tools" not in kwargs


@pytest.mark.parametrize(
    "response",
    [
        SimpleNamespace(stop_reason="refusal", content=[]),
        SimpleNamespace(stop_reason="max_tokens", content=[]),
        SimpleNamespace(
            stop_reason="end_turn", content=[SimpleNamespace(type="text", text="[1]")]
        ),
        anthropic.APIConnectionError(request=None),
    ],
)
def test_claude_adapter_fails_closed(monkeypatch, response):
    fake_client(monkeypatch, response)
    with pytest.raises(RuntimeError):
        providers.AnthropicProvider("claude-haiku-5-5").generate(PROMPT, timeout=5)


def test_claude_model_names_are_validated(monkeypatch):
    assert providers.provider_for("anthropic", "http://evil") is None
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert providers.provider_for("anthropic", "claude-haiku-5-5").ready() is False
    monkeypatch.setenv("ANTHROPIC_API_KEY", "none")
    assert providers.provider_for("anthropic", "claude-haiku-5-5").ready() is False
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-only")
    assert providers.provider_for("anthropic", "claude-haiku-5-5").ready() is True
