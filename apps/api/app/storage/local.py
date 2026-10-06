from pathlib import Path
from tempfile import NamedTemporaryFile


class LocalStorage:
    def __init__(self, root: Path):
        self.root = root.resolve()

    def path(self, key: str) -> Path:
        if not key or "\\" in key or Path(key).is_absolute():
            raise ValueError("Invalid storage key")
        path = (self.root / key).resolve()
        if not path.is_relative_to(self.root) or path == self.root:
            raise ValueError("Invalid storage key")
        return path

    def store(self, key: str, data: bytes) -> None:
        target = self.path(key)
        target.parent.mkdir(parents=True, exist_ok=True)
        with NamedTemporaryFile(dir=target.parent, delete=False) as temp:
            temp.write(data)
            name = Path(temp.name)
        try:
            name.replace(target)
        finally:
            name.unlink(missing_ok=True)
