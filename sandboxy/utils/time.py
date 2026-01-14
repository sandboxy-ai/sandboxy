"""Time utilities for Sandboxy.

Provides timezone-aware datetime functions to replace deprecated
datetime.utcnow() calls (deprecated in Python 3.12+).
"""

from datetime import UTC, datetime


def utcnow() -> datetime:
    """Get current UTC time as a timezone-aware datetime.

    This replaces the deprecated datetime.utcnow() with a timezone-aware
    alternative that works correctly in Python 3.12+.

    Returns:
        Current UTC time as timezone-aware datetime.

    """
    return datetime.now(UTC)
