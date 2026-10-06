from app.core.config import settings
from app.storage.base import Storage
from app.storage.local import LocalStorage


def get_storage() -> Storage:
    return LocalStorage(settings.storage_root)
