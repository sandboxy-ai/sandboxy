"""Local UI assets for Sandboxy."""

from pathlib import Path


def get_ui_path() -> Path | None:
    """Get the path to the local UI assets.

    Returns:
        Path to ui/dist/ if it exists, None otherwise.

    """
    dist_path = Path(__file__).parent / "dist"
    return dist_path if dist_path.exists() else None


def has_ui_assets() -> bool:
    """Check if local UI assets are available.

    Returns:
        True if ui/dist/ exists and contains files.

    """
    dist_path = Path(__file__).parent / "dist"
    if not dist_path.exists():
        return False
    return any(dist_path.iterdir())
