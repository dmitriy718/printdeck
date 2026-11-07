#!/usr/bin/env python3
"""
PrintDeck (printdeck.net) — Phase 2 Adaptive Token-Bucket Rate Limiter & Backoff Engine.
Handles Printify API v1 (600 req/min global, 100 req/min catalog) and
Printful API v2 (120 req/min, X-Ratelimit-Remaining / X-Ratelimit-Reset headers).
"""

from __future__ import annotations

import asyncio
import random
import time
from typing import Any, Awaitable, Callable, Dict, Optional
import httpx


class RateLimitExhaustedError(RuntimeError):
    """Raised when a POD provider returns HTTP 429 after all backoff retries."""


class AdaptiveRateLimiter:
    """
    Async token-bucket limiter with exponential backoff + full jitter and
    provider header inspection (Retry-After, X-Ratelimit-Reset).
    """

    def __init__(
        self,
        provider_name: str,
        requests_per_minute: int = 120,
        burst_capacity: int = 30,
        max_retries: int = 4,
        base_backoff_sec: float = 0.25,
    ) -> None:
        self.provider_name = provider_name
        self.rate_per_sec = max(requests_per_minute / 60.0, 0.5)
        self.capacity = float(burst_capacity)
        self.tokens = float(burst_capacity)
        self.last_refill = time.monotonic()
        self.max_retries = max_retries
        self.base_backoff_sec = base_backoff_sec
        self._lock = asyncio.Lock()
        self.telemetry: Dict[str, int] = {
            "total_requests": 0,
            "throttled_waits": 0,
            "http_429_retries": 0,
            "http_5xx_retries": 0,
        }

    async def acquire(self) -> None:
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self.last_refill
            self.tokens = min(self.capacity, self.tokens + elapsed * self.rate_per_sec)
            self.last_refill = now

            if self.tokens < 1.0:
                wait_sec = (1.0 - self.tokens) / self.rate_per_sec
                self.telemetry["throttled_waits"] += 1
                await asyncio.sleep(min(wait_sec, 2.0))
                self.tokens = 0.0
                self.last_refill = time.monotonic()
            else:
                self.tokens -= 1.0

            self.telemetry["total_requests"] += 1

    def update_from_headers(self, headers: Dict[str, str]) -> Optional[float]:
        """
        Parses Retry-After or Printful X-Ratelimit-Remaining / X-Ratelimit-Reset headers.
        Returns recommended sleep duration in seconds if bucket is exhausted.
        """
        lower_headers = {k.lower(): v for k, v in headers.items()}
        if "retry-after" in lower_headers:
            try:
                return float(lower_headers["retry-after"])
            except ValueError:
                pass
        remaining = lower_headers.get("x-ratelimit-remaining")
        reset = lower_headers.get("x-ratelimit-reset")
        if remaining is not None and reset is not None:
            try:
                rem_val = int(remaining)
                reset_val = float(reset)
                if rem_val <= 1:
                    self.tokens = 0.0
                    return max(0.1, min(reset_val, 5.0))
            except ValueError:
                pass
        return None

    async def execute_with_backoff(
        self,
        request_coro_factory: Callable[[], Awaitable[httpx.Response]],
    ) -> httpx.Response:
        """
        Executes an HTTPX request coroutine with token acquisition and exponential
        backoff on HTTP 429 or transient 502/503/504 errors.
        """
        last_exc: Optional[Exception] = None
        for attempt in range(self.max_retries + 1):
            await self.acquire()
            try:
                response = await request_coro_factory()
                header_sleep = self.update_from_headers(dict(response.headers))

                if response.status_code == 429:
                    self.telemetry["http_429_retries"] += 1
                    if attempt >= self.max_retries:
                        raise RateLimitExhaustedError(
                            f"{self.provider_name} rate limit exhausted after {self.max_retries} retries."
                        )
                    delay = header_sleep or (
                        self.base_backoff_sec * (2**attempt) + random.uniform(0.01, 0.1)
                    )
                    await asyncio.sleep(min(delay, 3.0))
                    continue

                if response.status_code in {502, 503, 504} and attempt < self.max_retries:
                    self.telemetry["http_5xx_retries"] += 1
                    delay = self.base_backoff_sec * (2**attempt) + random.uniform(0.01, 0.1)
                    await asyncio.sleep(min(delay, 2.0))
                    continue

                return response
            except (httpx.ConnectError, httpx.ReadTimeout) as exc:
                last_exc = exc
                if attempt >= self.max_retries:
                    raise
                delay = self.base_backoff_sec * (2**attempt)
                await asyncio.sleep(min(delay, 1.5))

        if last_exc:
            raise last_exc
        raise RateLimitExhaustedError(f"{self.provider_name} request failed after retries.")
