"""Unit tests for the token bucket (app/rate_limit.py). No database, no HTTP.

A fake clock stands in for time.monotonic, so "a minute later" is just
`clock.now += 60` and the tests run instantly and give the same result
every time.
"""

import threading

import pytest

from app.errors import TooManyRequestsError
from app.rate_limit import API, Limit, TokenBucketLimiter, client_key

PER_MINUTE = Limit("test", capacity=100, per_seconds=60)  # 1 token every 0.6 s


class FakeClock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


@pytest.fixture
def clock():
    return FakeClock()


@pytest.fixture
def limiter(clock):
    return TokenBucketLimiter(clock=clock)


def take_many(limiter, count, who="alice", limit=PER_MINUTE):
    for _ in range(count):
        limiter.take(limit, who)


def test_the_api_limit_is_100_per_minute():
    assert (API.capacity, API.per_seconds) == (100, 60)


def test_a_full_burst_is_allowed_and_the_next_request_is_refused(limiter):
    take_many(limiter, 100)  # boundary: exactly the capacity

    with pytest.raises(TooManyRequestsError) as refused:
        limiter.take(PER_MINUTE, "alice")
    assert refused.value.retry_after == 1  # 0.6 s until the next token, rounded up


def test_one_token_comes_back_every_0_6_seconds(limiter, clock):
    take_many(limiter, 100)

    clock.now += 0.5
    with pytest.raises(TooManyRequestsError):
        limiter.take(PER_MINUTE, "alice")  # not yet

    clock.now += 0.1  # 0.6 s since the bucket was emptied
    limiter.take(PER_MINUTE, "alice")  # exactly one token is back...
    with pytest.raises(TooManyRequestsError):
        limiter.take(PER_MINUTE, "alice")  # ...and only one


def test_the_bucket_never_holds_more_than_its_capacity(limiter, clock):
    clock.now += 3600  # an hour of doing nothing doesn't save up 6000 requests

    take_many(limiter, 100)
    with pytest.raises(TooManyRequestsError):
        limiter.take(PER_MINUTE, "alice")


def test_retry_after_tells_how_long_until_the_next_token(limiter):
    slow = Limit("slow", capacity=5, per_seconds=60 * 60)  # one token every 12 minutes
    take_many(limiter, 5, limit=slow)

    with pytest.raises(TooManyRequestsError) as refused:
        limiter.take(slow, "alice")
    assert refused.value.retry_after == 12 * 60


def test_each_caller_has_their_own_bucket(limiter):
    take_many(limiter, 100, who="alice")

    limiter.take(PER_MINUTE, "bob")  # Alice being out of tokens doesn't affect Bob


def test_each_limit_has_its_own_bucket(limiter):
    take_many(limiter, 100)
    other = Limit("other", capacity=1, per_seconds=60)

    limiter.take(other, "alice")


def test_full_buckets_are_forgotten_so_memory_stays_small(clock):
    limiter = TokenBucketLimiter(clock=clock, max_buckets=2)
    limiter.take(PER_MINUTE, "a")
    limiter.take(PER_MINUTE, "b")
    clock.now += 60  # both refill completely

    limiter.take(PER_MINUTE, "c")  # 3 buckets > 2: the full ones (a, b) go

    assert set(limiter._buckets) == {"test:c"}


def test_two_threads_never_both_get_the_last_token(limiter):
    """200 requests at the same moment from 20 threads: exactly 100 get through."""
    allowed = []
    start = threading.Barrier(20)

    def worker():
        start.wait()  # all threads start together, to make a race likely
        for _ in range(10):
            try:
                limiter.take(PER_MINUTE, "alice")
                allowed.append(1)
            except TooManyRequestsError:
                pass

    threads = [threading.Thread(target=worker) for _ in range(20)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(allowed) == 100


@pytest.mark.parametrize("host, key", [
    ("203.0.113.7", "ip:203.0.113.7"),
    ("2001:db8:1:2:aaaa::1", "ip:2001:db8:1:2::/64"),  # IPv6: the whole /64 block...
    ("2001:db8:1:2:bbbb::9", "ip:2001:db8:1:2::/64"),  # ...so switching address doesn't help
    ("testclient", "ip:testclient"),
    (None, "ip:unknown"),
])
def test_callers_are_counted_by_ip_or_ipv6_block(host, key):
    assert client_key(host) == key
