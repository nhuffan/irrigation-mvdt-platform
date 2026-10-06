from pathlib import Path
from typing import Protocol


class Storage(Protocol):
    def path(self, key: str) -> Path: ...
    def store(self, key: str, data: bytes) -> None: ...
