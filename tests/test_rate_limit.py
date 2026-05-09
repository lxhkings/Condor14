import pytest
from data_source.rate_limit import TokenBucket


class FakeClock:
    def __init__(self, start: float = 0.0) -> None:
        self.t = start
        self.sleeps: list[float] = []

    def now(self) -> float:
        return self.t

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.t += seconds


def test_initial_capacity_allows_burst_without_sleep():
    clock = FakeClock()
    bucket = TokenBucket(rate_per_sec=0.3, capacity=9, now=clock.now, sleep=clock.sleep)
    for _ in range(9):
        bucket.acquire()
    assert clock.sleeps == []


def test_eleventh_call_sleeps_until_token_refilled():
    clock = FakeClock()
    bucket = TokenBucket(rate_per_sec=0.3, capacity=9, now=clock.now, sleep=clock.sleep)
    for _ in range(9):
        bucket.acquire()
    bucket.acquire()
    assert len(clock.sleeps) == 1
    # rate=0.3 token/s, need 1 token => sleep ~ 1/0.3 ≈ 3.333s
    assert clock.sleeps[0] == pytest.approx(1 / 0.3, rel=1e-6)


def test_tokens_refill_over_time_without_explicit_sleep():
    clock = FakeClock()
    bucket = TokenBucket(rate_per_sec=0.3, capacity=9, now=clock.now, sleep=clock.sleep)
    for _ in range(9):
        bucket.acquire()
    clock.t += 30  # 30s 全自然回血
    bucket.acquire()
    assert clock.sleeps == []  # 不需要再 sleep


def test_capacity_caps_refill():
    clock = FakeClock()
    bucket = TokenBucket(rate_per_sec=0.3, capacity=9, now=clock.now, sleep=clock.sleep)
    clock.t += 1000  # 长时间空闲，桶最多回血到 capacity
    for _ in range(9):
        bucket.acquire()
    bucket.acquire()
    assert len(clock.sleeps) == 1  # 第 10 次仍要等
