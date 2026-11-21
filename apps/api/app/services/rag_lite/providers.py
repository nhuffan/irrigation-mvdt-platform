"""Generation adapters for the local, experimental evidence preview."""

import asyncio
import json
import os
import re
from functools import lru_cache
from threading import Lock
from time import monotonic
from typing import Protocol

import httpx

OLLAMA_ORIGIN = "http://127.0.0.1:11434"
RESPONSE_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "answer": {"type": "string", "maxLength": 4000},
        "citation_ids": {
            "type": "array",
            "maxItems": 8,
            "items": {"type": "string", "maxLength": 120},
        },
    },
    "required": ["answer", "citation_ids"],
}


class Provider(Protocol):
    def generate(self, prompt: str, *, timeout: float) -> dict: ...


class UnavailableProvider:
    def generate(self, prompt: str, *, timeout: float) -> dict:
        raise RuntimeError("No authorized provider configured")


async def ollama_request(path: str, body: dict, timeout: float) -> dict:
    async with (
        asyncio.timeout(timeout),
        httpx.AsyncClient(
            base_url=OLLAMA_ORIGIN,
            follow_redirects=False,
            timeout=None,
            trust_env=False,
            headers={"Accept-Encoding": "identity"},
        ) as client,
        client.stream("POST", path, json=body) as response,
    ):
        response.raise_for_status()
        if response.headers.get("Content-Encoding", "identity").lower() != "identity":
            raise ValueError("Unexpected model response encoding")
        raw = bytearray()
        async for chunk in response.aiter_bytes(chunk_size=8192):
            raw.extend(chunk)
            if len(raw) > 256 * 1024:
                raise ValueError("Model response exceeds the local response limit")
        result = json.loads(raw)
        if not isinstance(result, dict):
            raise TypeError("Invalid model response")
        return result


class OllamaProvider:
    def __init__(self, model: str):
        self.model = f"{model}:local"
        self._probe_lock = Lock()
        self._probe_expires_at = 0.0
        self._available = False

    def ready(self) -> bool:
        if monotonic() < self._probe_expires_at:
            return self._available
        if not self._probe_lock.acquire(blocking=False):
            return False
        try:
            if monotonic() >= self._probe_expires_at:
                try:
                    details = asyncio.run(
                        ollama_request("/api/show", {"model": self.model}, 1.0)
                    )
                    capabilities = details.get("capabilities")
                    self._available = (
                        isinstance(capabilities, list)
                        and "completion" in capabilities
                        and not details.get("remote_host")
                        and not details.get("remote_model")
                    )
                except (
                    httpx.HTTPError,
                    OSError,
                    ValueError,
                    TypeError,
                    RecursionError,
                ):
                    self._available = False
                self._probe_expires_at = monotonic() + 5.0
            return self._available
        finally:
            self._probe_lock.release()

    def generate(self, prompt: str, *, timeout: float) -> dict:
        try:
            response = asyncio.run(
                ollama_request(
                    "/api/chat",
                    {
                        "model": self.model,
                        "messages": json.loads(prompt),
                        "format": RESPONSE_SCHEMA,
                        "stream": False,
                        "think": False,
                        "options": {
                            "temperature": 0,
                            "num_ctx": 8192,
                            "num_predict": 768,
                        },
                    },
                    timeout,
                )
            )
            message = response.get("message")
            if (
                response.get("done") is not True
                or response.get("done_reason") != "stop"
                or response.get("remote_host")
                or response.get("remote_model")
                or not isinstance(message, dict)
                or message.get("role") != "assistant"
                or message.get("tool_calls")
                or message.get("refusal")
            ):
                raise ValueError("Invalid model completion")
            return json.loads(message["content"])
        except (
            httpx.HTTPError,
            OSError,
            ValueError,
            KeyError,
            TypeError,
            RecursionError,
        ):
            raise RuntimeError("Local model generation unavailable") from None


# Claude structured outputs accept no string/array length constraints; the
# server-side validator still enforces every answer and citation rule.
CLOUD_RESPONSE_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "answer": {"type": "string"},
        "citation_ids": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["answer", "citation_ids"],
}
CLOUD_PROVIDERS = frozenset({"anthropic"})


class AnthropicProvider:
    """Hosted Claude model. Only ever authorized for SYNTHETIC demo evidence."""

    def __init__(self, model: str):
        self.model = model

    def ready(self) -> bool:
        return bool(os.environ.get("ANTHROPIC_API_KEY"))

    def generate(self, prompt: str, *, timeout: float) -> dict:
        import anthropic

        try:
            messages = json.loads(prompt)
            system = "\n".join(m["content"] for m in messages if m["role"] == "system")
            turns = [m for m in messages if m["role"] == "user"]
            client = anthropic.Anthropic(timeout=timeout, max_retries=1)
            response = client.messages.create(
                model=self.model,
                max_tokens=2048,
                system=system,
                messages=turns,
                output_config={
                    "effort": "low",
                    "format": {"type": "json_schema", "schema": CLOUD_RESPONSE_SCHEMA},
                },
            )
            if response.stop_reason != "end_turn":
                raise ValueError("Incomplete or refused model completion")
            text = next(
                block.text for block in response.content if block.type == "text"
            )
            result = json.loads(text)
            if not isinstance(result, dict):
                raise TypeError("Invalid model response")
            return result
        except (
            anthropic.APIError,
            StopIteration,
            KeyError,
            ValueError,
            TypeError,
            RecursionError,
        ):
            raise RuntimeError("Hosted model generation unavailable") from None


@lru_cache(maxsize=8)
def provider_for(provider: str, model: str):
    if provider == "anthropic":
        if re.fullmatch(r"claude-[a-z0-9][a-z0-9-]{0,62}", model):
            return AnthropicProvider(model)
        return None
    # A single local model name/tag, with no endpoint or cloud selection.
    if (
        provider != "ollama"
        or not re.fullmatch(
            r"[a-z0-9][a-z0-9._/-]{0,95}:[a-z0-9][a-z0-9._-]{0,39}", model
        )
        or model.endswith((":local", ":cloud", "-cloud"))
    ):
        return None
    return OllamaProvider(model)
