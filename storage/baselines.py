"""Baseline management — save and load baseline screenshots."""

from __future__ import annotations

import re
import shutil
from pathlib import Path

BASELINES_DIR = Path("storage_layout/baselines")

_SAFE_NAME = re.compile(r"^[a-zA-Z0-9_-]+$")


def _validate_name(name: str) -> str:
    """Validate system/role/file names to prevent path traversal."""
    if not _SAFE_NAME.match(name):
        raise ValueError(f"Invalid name (only [a-zA-Z0-9_-] allowed): {name!r}")
    return name


def get_baseline_dir(system_name: str) -> Path:
    _validate_name(system_name)
    return BASELINES_DIR / system_name


def save_baselines(system_name: str, screenshots_dir: Path) -> int:
    """Copy current screenshots as new baselines. Returns count saved."""
    baseline_dir = get_baseline_dir(system_name)
    # Verify resolved path stays under BASELINES_DIR
    if not baseline_dir.resolve().is_relative_to(BASELINES_DIR.resolve()):
        raise ValueError(f"Path escapes baselines dir: {baseline_dir}")
    if baseline_dir.exists():
        if baseline_dir.is_symlink():
            raise ValueError(f"Refusing to delete symlink: {baseline_dir}")
        shutil.rmtree(baseline_dir)
    shutil.copytree(screenshots_dir, baseline_dir)
    return len(list(baseline_dir.rglob("*.png")))


def get_baseline_path(system_name: str, role: str, filename: str) -> Path | None:
    """Get path to baseline screenshot if it exists."""
    _validate_name(role)
    _validate_name(filename.replace(".", "_"))  # allow dots in filenames
    path = get_baseline_dir(system_name) / role / filename
    return path if path.exists() else None


def has_baselines(system_name: str) -> bool:
    """Check if baselines exist for a system."""
    baseline_dir = get_baseline_dir(system_name)
    return baseline_dir.exists() and any(baseline_dir.rglob("*.png"))
