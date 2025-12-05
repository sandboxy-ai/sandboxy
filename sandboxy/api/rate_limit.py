"""Simple in-memory rate limiting for the API."""

import time
from collections import defaultdict
from typing import Callable

from fastapi import HTTPException, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


class RateLimiter:
    """Simple in-memory rate limiter using sliding window.

    Tracks requests per IP address and returns 429 when limit exceeded.
    """

    def __init__(
        self,
        requests_per_minute: int = 60,
        requests_per_hour: int = 500,
        session_starts_per_hour: int = 20,
    ):
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        self.session_starts_per_hour = session_starts_per_hour

        # Track timestamps of requests per IP
        self._minute_requests: dict[str, list[float]] = defaultdict(list)
        self._hour_requests: dict[str, list[float]] = defaultdict(list)
        self._session_starts: dict[str, list[float]] = defaultdict(list)

    def _cleanup_old_requests(self, requests: list[float], window_seconds: int) -> list[float]:
        """Remove requests older than the window."""
        cutoff = time.time() - window_seconds
        return [ts for ts in requests if ts > cutoff]

    def check_rate_limit(self, ip: str, is_session_start: bool = False) -> tuple[bool, str | None]:
        """Check if request is within rate limits.

        Returns:
            Tuple of (allowed, error_message)
        """
        now = time.time()

        # Clean up old requests
        self._minute_requests[ip] = self._cleanup_old_requests(
            self._minute_requests[ip], 60
        )
        self._hour_requests[ip] = self._cleanup_old_requests(
            self._hour_requests[ip], 3600
        )

        # Check minute limit
        if len(self._minute_requests[ip]) >= self.requests_per_minute:
            return False, f"Rate limit exceeded: {self.requests_per_minute} requests per minute"

        # Check hour limit
        if len(self._hour_requests[ip]) >= self.requests_per_hour:
            return False, f"Rate limit exceeded: {self.requests_per_hour} requests per hour"

        # Check session start limit (more restrictive)
        if is_session_start:
            self._session_starts[ip] = self._cleanup_old_requests(
                self._session_starts[ip], 3600
            )
            if len(self._session_starts[ip]) >= self.session_starts_per_hour:
                return False, f"Session limit exceeded: {self.session_starts_per_hour} sessions per hour"
            self._session_starts[ip].append(now)

        # Record request
        self._minute_requests[ip].append(now)
        self._hour_requests[ip].append(now)

        return True, None

    def get_remaining(self, ip: str) -> dict[str, int]:
        """Get remaining requests for an IP."""
        self._minute_requests[ip] = self._cleanup_old_requests(
            self._minute_requests[ip], 60
        )
        self._hour_requests[ip] = self._cleanup_old_requests(
            self._hour_requests[ip], 3600
        )
        self._session_starts[ip] = self._cleanup_old_requests(
            self._session_starts[ip], 3600
        )

        return {
            "requests_per_minute": self.requests_per_minute - len(self._minute_requests[ip]),
            "requests_per_hour": self.requests_per_hour - len(self._hour_requests[ip]),
            "sessions_per_hour": self.session_starts_per_hour - len(self._session_starts[ip]),
        }


# Global rate limiter instance
rate_limiter = RateLimiter()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware to enforce rate limits on API requests."""

    # Paths that don't count against rate limits
    EXEMPT_PATHS = {"/health", "/api/docs", "/api/openapi.json"}

    # Paths that count as session starts (more restrictive)
    SESSION_START_PATHS = {"/ws/session"}

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip rate limiting for exempt paths
        path = request.url.path
        if path in self.EXEMPT_PATHS:
            return await call_next(request)

        # Get client IP (handle proxies)
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            ip = forwarded.split(",")[0].strip()
        else:
            ip = request.client.host if request.client else "unknown"

        # Check if this is a session start
        is_session_start = any(path.startswith(p) for p in self.SESSION_START_PATHS)

        # Check rate limit
        allowed, error = rate_limiter.check_rate_limit(ip, is_session_start)

        if not allowed:
            raise HTTPException(
                status_code=429,
                detail=error,
                headers={"Retry-After": "60"},
            )

        # Add rate limit headers to response
        response = await call_next(request)
        remaining = rate_limiter.get_remaining(ip)
        response.headers["X-RateLimit-Remaining-Minute"] = str(remaining["requests_per_minute"])
        response.headers["X-RateLimit-Remaining-Hour"] = str(remaining["requests_per_hour"])

        return response
