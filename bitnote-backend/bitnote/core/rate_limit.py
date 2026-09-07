import time
from collections import defaultdict
from threading import Lock

from fastapi import HTTPException, Request


class RateLimiter:
    """
    Simple in-memory sliding-window rate limiter, keyed per caller.

    In-memory only: resets on restart and does not share state across
    multiple worker processes. Good enough for a single-process deployment;
    swap for a shared store (e.g. Redis) if running multiple workers.
    """

    def __init__(self, max_attempts: int, window_seconds: int):
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self._hits: dict[str, list[float]] = defaultdict(list)
        self._lock = Lock()

    def check(self, key: str):
        now = time.time()
        cutoff = now - self.window_seconds
        with self._lock:
            hits = self._hits[key]
            while hits and hits[0] < cutoff:
                hits.pop(0)
            if len(hits) >= self.max_attempts:
                raise HTTPException(
                    status_code=429,
                    detail="Too many attempts. Please try again later.",
                )
            hits.append(now)


auth_rate_limiter = RateLimiter(max_attempts=10, window_seconds=60)


def rate_limit_auth(request: Request):
    client_ip = request.client.host if request.client else "unknown"
    key = f"{client_ip}:{request.url.path}"
    auth_rate_limiter.check(key)
