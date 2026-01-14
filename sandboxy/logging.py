"""Logging configuration for Sandboxy."""

import logging
import sys


def setup_logging(level: int = logging.INFO, verbose: bool = False) -> None:
    """Configure logging for Sandboxy.

    Args:
        level: Base logging level.
        verbose: If True, use DEBUG level and show module names.
    """
    if verbose:
        level = logging.DEBUG
        fmt = "%(asctime)s %(levelname)s [%(name)s] %(message)s"
    else:
        fmt = "%(levelname)s: %(message)s"

    logging.basicConfig(
        level=level,
        format=fmt,
        stream=sys.stderr,
        force=True,
    )

    # Quiet noisy libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("anthropic").setLevel(logging.WARNING)
