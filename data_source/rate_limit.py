"""Single-threaded token-bucket rate limiter.

Used to keep Futu API calls under per-endpoint quotas (typically 10/30s).
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable


@dataclass
class TokenBucket:
    # NOT thread-safe. Intended for single-threaded use only.
    rate_per_sec: float
    capacity: float
    now: Callable[[], float] = field(default=time.monotonic)
    sleep: Callable[[float], None] = field(default=time.sleep)
    _tokens: float = field(init=False)
    _last: float = field(init=False)

    def __post_init__(self) -> None:
        self._tokens = self.capacity
        self._last = self.now()

    def acquire(self, n: float = 1.0) -> None:
        if n > self.capacity:
            raise ValueError(f"n={n} exceeds bucket capacity={self.capacity}")
        while True:
            t = self.now()
            self._tokens = min(self.capacity, self._tokens + (t - self._last) * self.rate_per_sec)
            self._last = t
            if self._tokens >= n:
                self._tokens -= n
                return
            self.sleep((n - self._tokens) / self.rate_per_sec)
