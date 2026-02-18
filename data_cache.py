"""
Simple in-process data cache with TTL.
Avoids redundant fetches/computations within the same request cycle.
"""

import threading
import time

_cache = {}
_lock = threading.Lock()
_DEFAULT_TTL = 300  # 5 minutes


def get(key):
    """Get a cached value. Returns None if not found or expired."""
    with _lock:
        entry = _cache.get(key)
        if entry is None:
            return None
        value, expiry = entry
        if time.monotonic() > expiry:
            del _cache[key]
            return None
        return value


def set(key, value, ttl=_DEFAULT_TTL):
    """Cache a value with a TTL (seconds)."""
    with _lock:
        _cache[key] = (value, time.monotonic() + ttl)


def clear():
    """Clear all cached entries."""
    with _lock:
        _cache.clear()
