"""Provider-neutral extension seam. No external provider is authorized in this POC."""

from typing import Protocol


class Provider(Protocol):
    def generate(self, prompt: str, *, timeout: float) -> dict: ...


class UnavailableProvider:
    def generate(self, prompt: str, *, timeout: float) -> dict:
        raise RuntimeError("No authorized provider configured")
