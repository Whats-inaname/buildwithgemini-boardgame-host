import time
from typing import Any, Optional, Dict, Tuple

class SimpleMemoryCache:
    """In-memory key-value cache with TTL (time-to-live) in seconds."""
    def __init__(self, default_ttl: int = 300):
        self._cache: Dict[str, Tuple[Any, float]] = {}
        self.default_ttl = default_ttl

    def get(self, key: str) -> Optional[Any]:
        if key not in self._cache:
            return None
        val, expiry = self._cache[key]
        if time.time() > expiry:
            del self._cache[key]
            return None
        return val

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        duration = ttl if ttl is not None else self.default_ttl
        expiry = time.time() + duration
        self._cache[key] = (value, expiry)

    def clear(self) -> None:
        self._cache.clear()

# Global memory cache instance
memory_cache = SimpleMemoryCache(default_ttl=300)
