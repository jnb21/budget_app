"""Rate limiting with token buckets, kept in memory.

Every caller gets one bucket per kind of request. A bucket holds up to
`capacity` tokens and refills at a steady rate; each request takes one
token. An empty bucket means: wait (429, with how many seconds in
Retry-After).

    Limit("api", capacity=100, per_seconds=60)
      -> a burst of 100 requests at once is fine,
         then one more every 0.6 s (100 per minute).

Unlike "100 per clock minute", a bucket never allows 100 requests at 0:59
and 100 more at 1:00.

Only two numbers are stored per bucket: the tokens left and when we last
looked. Nothing runs in the background; the refill is worked out on the
next request from the time that went by.

The buckets live in this process's memory: they reset when the server
restarts and aren't shared between servers. Fine for one server; with
several, they would move to a shared store such as Redis.
"""

import ipaddress
import math
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass

from app.errors import TooManyRequestsError


@dataclass(frozen=True)
class Limit:
    name: str
    capacity: int       # the biggest burst: requests allowed at once
    per_seconds: float  # how long an empty bucket takes to fill up again

    @property
    def tokens_per_second(self) -> float:
        return self.capacity / self.per_seconds


API = Limit("api", capacity=100, per_seconds=60)                     # every /api request, per user (or IP)
LOGIN = Limit("login", capacity=20, per_seconds=15 * 60)             # per IP: many emails from one place
SIGNUP = Limit("signup", capacity=5, per_seconds=60 * 60)            # per IP: bulk fake accounts
DELETE_ACCOUNT = Limit("delete_account", capacity=5, per_seconds=15 * 60)  # per user: password guessing


class TokenBucketLimiter:
    def __init__(self, clock: Callable[[], float] = time.monotonic, max_buckets: int = 100_000):
        self._clock = clock              # tests pass a fake clock, so "wait a minute" is instant
        self._max_buckets = max_buckets
        self._buckets: dict[str, tuple[float, float, Limit]] = {}  # key -> (tokens, updated at, limit)
        # Requests run in several threads at once; without the lock, two of
        # them could both take "the last token".
        self._lock = threading.Lock()

    def take(self, limit: Limit, who: str) -> None:
        """Take one token from who's bucket for this limit, or raise
        TooManyRequestsError saying how many seconds until the next token."""
        key = f"{limit.name}:{who}"
        with self._lock:
            now = self._clock()
            tokens = self._tokens_now(key, limit, now)
            if tokens < 1:
                self._buckets[key] = (tokens, now, limit)
                wait = math.ceil((1 - tokens) / limit.tokens_per_second)
                raise TooManyRequestsError(f"too many requests; try again in {wait} s", retry_after=wait)
            self._buckets[key] = (tokens - 1, now, limit)
            if len(self._buckets) > self._max_buckets:
                self._forget_full_buckets(now)

    def _tokens_now(self, key: str, limit: Limit, now: float) -> float:
        if key not in self._buckets:
            return float(limit.capacity)  # a new caller starts with a full bucket
        tokens, updated_at, _ = self._buckets[key]
        return min(limit.capacity, tokens + (now - updated_at) * limit.tokens_per_second)

    def _forget_full_buckets(self, now: float) -> None:
        """A full bucket behaves exactly like no bucket, so it can go. Keeps
        memory bounded when many different callers come and go."""
        for key, (_, _, limit) in list(self._buckets.items()):
            if self._tokens_now(key, limit, now) >= limit.capacity:
                del self._buckets[key]


def client_key(host: str | None) -> str:
    """Who to count an anonymous request against: its IP address.

    IPv6: one home or server usually gets a whole /64 block (2^64 addresses),
    so counting single addresses would let one machine dodge the limit by
    switching address. Count the block instead.

    Behind a proxy (Caddy in production), `host` must be the real client's
    IP: start uvicorn with --proxy-headers --forwarded-allow-ips=<proxy IP>,
    so the X-Forwarded-For header is believed from the proxy and nobody else.
    """
    if not host:
        return "ip:unknown"
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        return f"ip:{host}"  # e.g. "testclient" in tests
    if address.version == 6:
        return f"ip:{ipaddress.ip_network(f'{address}/64', strict=False)}"
    return f"ip:{address}"
