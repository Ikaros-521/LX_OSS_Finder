import time
from typing import Any, Dict, Tuple
from ..config import get_settings


class InMemoryCache:
    def __init__(self):
        self.settings = get_settings()
        self.store: Dict[str, Tuple[float, Any]] = {}

    def get(self, key: str):
        entry = self.store.get(key)
        if not entry:
            return None
        expires_at, value = entry
        if time.time() > expires_at:
            self.store.pop(key, None)
            return None
        return value

    def set(self, key: str, value: Any):
        ttl = self.settings.cache_ttl_seconds
        self.store[key] = (time.time() + ttl, value)

