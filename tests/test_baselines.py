"""Tests for storage/baselines.py."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from storage.baselines import (
    BASELINES_DIR,
    get_baseline_dir,
    get_baseline_path,
    has_baselines,
    save_baselines,
)


class TestValidateName:
    def test_valid_system_name(self):
        # Should not raise — alphanumeric, hyphens, underscores are OK
        path = get_baseline_dir("backoffice")
        assert path == BASELINES_DIR / "backoffice"

    def test_invalid_system_name_dots(self):
        with pytest.raises(ValueError, match="Invalid name"):
            get_baseline_dir("../../etc")

    def test_invalid_system_name_spaces(self):
        with pytest.raises(ValueError, match="Invalid name"):
            get_baseline_dir("my system")

    def test_invalid_system_name_slash(self):
        with pytest.raises(ValueError, match="Invalid name"):
            get_baseline_dir("foo/bar")


class TestSaveAndLoadBaselines:
    def test_save_and_load_baselines(self, tmp_path):
        screenshots = tmp_path / "screenshots"
        screenshots.mkdir()
        (screenshots / "page1.png").write_bytes(b"\x89PNG-fake1")
        (screenshots / "page2.png").write_bytes(b"\x89PNG-fake2")
        (screenshots / "page3.png").write_bytes(b"\x89PNG-fake3")

        baselines_root = tmp_path / "baselines"
        baselines_root.mkdir()

        with patch("storage.baselines.BASELINES_DIR", baselines_root):
            count = save_baselines("myapp", screenshots)

        assert count == 3
        saved_dir = baselines_root / "myapp"
        assert saved_dir.exists()
        assert (saved_dir / "page1.png").read_bytes() == b"\x89PNG-fake1"
        assert (saved_dir / "page2.png").read_bytes() == b"\x89PNG-fake2"
        assert (saved_dir / "page3.png").read_bytes() == b"\x89PNG-fake3"


class TestHasBaselines:
    def test_has_baselines_empty(self, tmp_path):
        baselines_root = tmp_path / "baselines"
        baselines_root.mkdir()

        with patch("storage.baselines.BASELINES_DIR", baselines_root):
            assert has_baselines("noapp") is False

    def test_has_baselines_with_pngs(self, tmp_path):
        baselines_root = tmp_path / "baselines"
        system_dir = baselines_root / "myapp"
        system_dir.mkdir(parents=True)
        (system_dir / "shot.png").write_bytes(b"\x89PNG")

        with patch("storage.baselines.BASELINES_DIR", baselines_root):
            assert has_baselines("myapp") is True


class TestGetBaselinePath:
    def test_get_baseline_path_exists(self, tmp_path):
        baselines_root = tmp_path / "baselines"
        role_dir = baselines_root / "myapp" / "admin"
        role_dir.mkdir(parents=True)
        target = role_dir / "login.png"
        target.write_bytes(b"\x89PNG")

        with patch("storage.baselines.BASELINES_DIR", baselines_root):
            result = get_baseline_path("myapp", "admin", "login.png")

        assert result is not None
        assert result == target
        assert isinstance(result, Path)

    def test_get_baseline_path_missing(self, tmp_path):
        baselines_root = tmp_path / "baselines"
        baselines_root.mkdir()

        with patch("storage.baselines.BASELINES_DIR", baselines_root):
            result = get_baseline_path("myapp", "admin", "nonexistent.png")

        assert result is None


class TestSaveBaselinesSymlinkRejected:
    def test_save_baselines_symlink_rejected(self, tmp_path):
        baselines_root = tmp_path / "baselines"
        baselines_root.mkdir()

        # Create a symlink where the baseline dir would be
        evil_target = tmp_path / "evil"
        evil_target.mkdir()
        symlink_path = baselines_root / "hacked"
        symlink_path.symlink_to(evil_target)

        screenshots = tmp_path / "screenshots"
        screenshots.mkdir()
        (screenshots / "shot.png").write_bytes(b"\x89PNG")

        with patch("storage.baselines.BASELINES_DIR", baselines_root):
            with pytest.raises(ValueError, match="symlink"):
                save_baselines("hacked", screenshots)
