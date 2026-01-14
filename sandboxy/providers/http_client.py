"""Shared HTTP client with connection pooling.

Provides a singleton httpx.AsyncClient that reuses connections across requests,
significantly improving performance for repeated API calls.

Configuration via environment:
    SANDBOXY_HTTP_TIMEOUT: Request timeout in seconds (default: 120)
    SANDBOXY_HTTP_CONNECT_TIMEOUT: Connection timeout in seconds (default: 10)
    SANDBOXY_HTTP_POOL_CONNECTIONS: Max keepalive connections (default: 20)
    SANDBOXY_HTTP_POOL_MAXSIZE: Max total connections (default: 100)
"""

import logging
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx

logger = logging.getLogger(__name__)

# Global client instance
_client: httpx.AsyncClient | None = None

# Configuration from environment
_TIMEOUT = float(os.environ.get("SANDBOXY_HTTP_TIMEOUT", "120"))
_CONNECT_TIMEOUT = float(os.environ.get("SANDBOXY_HTTP_CONNECT_TIMEOUT", "10"))
_POOL_CONNECTIONS = int(os.environ.get("SANDBOXY_HTTP_POOL_CONNECTIONS", "20"))
_POOL_MAXSIZE = int(os.environ.get("SANDBOXY_HTTP_POOL_MAXSIZE", "100"))


def _create_client() -> httpx.AsyncClient:
    """Create a new HTTP client with connection pooling."""
    return httpx.AsyncClient(
        timeout=httpx.Timeout(
            _TIMEOUT,
            connect=_CONNECT_TIMEOUT,
        ),
        limits=httpx.Limits(
            max_keepalive_connections=_POOL_CONNECTIONS,
            max_connections=_POOL_MAXSIZE,
            keepalive_expiry=30.0,  # Keep idle connections for 30 seconds
        ),
        # HTTP/2 disabled - requires h2 package (pip install httpx[http2])
        # HTTP/1.1 works fine for API calls
        http2=False,
    )


def get_http_client() -> httpx.AsyncClient:
    """Get the shared HTTP client with connection pooling.

    The client is created lazily on first access and reused for all subsequent
    requests. This provides significant performance benefits for repeated API calls.

    Returns:
        Shared httpx.AsyncClient instance.

    Usage:
        client = get_http_client()
        response = await client.post(url, json=data)

    """
    global _client
    if _client is None:
        _client = _create_client()
        logger.debug(
            f"HTTP client created: pool_connections={_POOL_CONNECTIONS}, "
            f"pool_maxsize={_POOL_MAXSIZE}, timeout={_TIMEOUT}s"
        )
    return _client


async def close_http_client() -> None:
    """Close the shared HTTP client.

    Should be called during application shutdown to cleanly close connections.
    """
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None
        logger.debug("HTTP client closed")


@asynccontextmanager
async def http_client_lifespan() -> AsyncIterator[httpx.AsyncClient]:
    """Context manager for HTTP client lifecycle.

    Use this in application lifespan to ensure proper cleanup:

        async with http_client_lifespan() as client:
            # Application runs here
            pass
        # Client is automatically closed on exit
    """
    client = get_http_client()
    try:
        yield client
    finally:
        await close_http_client()
