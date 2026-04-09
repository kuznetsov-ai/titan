"""Security tests — path traversal, symlink attacks, env var injection, TLS warnings."""

from __future__ import annotations

from pathlib import Path

import pytest

# ── Path allowlist tests (_validate_scenario_path) ────────────────────


class TestValidateScenarioPath:
    """Tests for scenarios.runner._validate_scenario_path."""

    def _make_testme(self, base: Path) -> Path:
        """Create a valid testMe dir with ui_test_scenarios.py inside *base*."""
        testme = base / "testMe"
        testme.mkdir(parents=True, exist_ok=True)
        (testme / "ui_test_scenarios.py").write_text("# stub", encoding="utf-8")
        return testme

    def test_valid_path_under_projects(self, tmp_path, monkeypatch):
        from scenarios.runner import _validate_scenario_path

        monkeypatch.setattr(
            "scenarios.runner.ALLOWED_SCENARIO_ROOTS", [tmp_path],
        )
        testme = self._make_testme(tmp_path / "some-project")
        result = _validate_scenario_path(str(testme))
        assert result == testme / "ui_test_scenarios.py"

    def test_path_outside_allowed_roots(self, tmp_path, monkeypatch):
        from scenarios.runner import _validate_scenario_path

        monkeypatch.setattr(
            "scenarios.runner.ALLOWED_SCENARIO_ROOTS", [tmp_path / "allowed"],
        )
        evil = tmp_path / "evil" / "testMe"
        evil.mkdir(parents=True)
        (evil / "ui_test_scenarios.py").write_text("# stub", encoding="utf-8")

        with pytest.raises(ValueError, match="outside allowed roots"):
            _validate_scenario_path(str(evil))

    def test_path_traversal_attack(self, tmp_path, monkeypatch):
        from scenarios.runner import _validate_scenario_path

        projects = tmp_path / "Projects"
        projects.mkdir()
        monkeypatch.setattr(
            "scenarios.runner.ALLOWED_SCENARIO_ROOTS", [projects],
        )
        # ../../etc resolves outside Projects
        traversal_path = str(projects / ".." / ".." / "etc" / "testMe")

        with pytest.raises(ValueError, match="outside allowed roots"):
            _validate_scenario_path(traversal_path)

    def test_symlink_scenario_rejected(self, tmp_path, monkeypatch):
        from scenarios.runner import _validate_scenario_path

        monkeypatch.setattr(
            "scenarios.runner.ALLOWED_SCENARIO_ROOTS", [tmp_path],
        )
        testme = tmp_path / "project" / "testMe"
        testme.mkdir(parents=True)

        # Create a real file somewhere and symlink it as ui_test_scenarios.py
        real_file = tmp_path / "real_scenario.py"
        real_file.write_text("# real", encoding="utf-8")
        symlink = testme / "ui_test_scenarios.py"
        symlink.symlink_to(real_file)

        with pytest.raises(ValueError, match="symlinked"):
            _validate_scenario_path(str(testme))

    def test_missing_scenario_file(self, tmp_path, monkeypatch):
        from scenarios.runner import _validate_scenario_path

        monkeypatch.setattr(
            "scenarios.runner.ALLOWED_SCENARIO_ROOTS", [tmp_path],
        )
        testme = tmp_path / "project" / "testMe"
        testme.mkdir(parents=True)
        # No ui_test_scenarios.py inside

        with pytest.raises(FileNotFoundError, match="Scenario file not found"):
            _validate_scenario_path(str(testme))

    def test_non_testme_dir_warns(self, tmp_path, monkeypatch, capsys):
        from scenarios.runner import _validate_scenario_path

        monkeypatch.setattr(
            "scenarios.runner.ALLOWED_SCENARIO_ROOTS", [tmp_path],
        )
        # Directory named "custom_dir" instead of "testMe"
        custom = tmp_path / "project" / "custom_dir"
        custom.mkdir(parents=True)
        (custom / "ui_test_scenarios.py").write_text("# stub", encoding="utf-8")

        result = _validate_scenario_path(str(custom))
        assert result == custom / "ui_test_scenarios.py"

        captured = capsys.readouterr()
        assert "WARNING" in captured.out
        assert "not named 'testMe'" in captured.out


# ── Env var resolution tests (_resolve_env_vars) ─────────────────────


class TestResolveEnvVars:
    """Tests for config.loader._resolve_env_vars."""

    def test_resolve_with_default(self, monkeypatch):
        from config.loader import _resolve_env_vars

        monkeypatch.delenv("FOO", raising=False)
        assert _resolve_env_vars("${FOO:bar}") == "bar"

    def test_resolve_from_env(self, monkeypatch):
        from config.loader import _resolve_env_vars

        monkeypatch.setenv("FOO", "hello")
        assert _resolve_env_vars("${FOO:bar}") == "hello"

    def test_resolve_no_default(self, monkeypatch):
        from config.loader import _resolve_env_vars

        monkeypatch.delenv("FOO", raising=False)
        assert _resolve_env_vars("${FOO}") == ""

    def test_resolve_nested_dict(self, monkeypatch):
        from config.loader import _resolve_env_vars

        monkeypatch.delenv("X", raising=False)
        monkeypatch.delenv("Y", raising=False)
        result = _resolve_env_vars({"a": "${X:1}", "b": {"c": "${Y:2}"}})
        assert result == {"a": "1", "b": {"c": "2"}}

    def test_resolve_list(self, monkeypatch):
        from config.loader import _resolve_env_vars

        monkeypatch.delenv("A", raising=False)
        monkeypatch.delenv("B", raising=False)
        result = _resolve_env_vars(["${A:x}", "${B:y}"])
        assert result == ["x", "y"]

    def test_no_env_pattern(self):
        from config.loader import _resolve_env_vars

        assert _resolve_env_vars("plain string") == "plain string"

    def test_resolve_multiple_in_string(self, monkeypatch):
        from config.loader import _resolve_env_vars

        monkeypatch.delenv("U", raising=False)
        monkeypatch.delenv("P", raising=False)
        result = _resolve_env_vars("user=${U:admin} pass=${P:secret}")
        assert result == "user=admin pass=secret"


# ── TLS warning tests ────────────────────────────────────────────────


class TestTLSWarning:
    """Tests for TLS warning emitted by load_system_config."""

    def _write_config(self, path: Path, base_url: str, ignore_https: bool) -> Path:
        """Write a minimal valid YAML config to *path*."""
        cfg = path / "test_system.yaml"
        cfg.write_text(
            f"""\
name: test-system
base_url: {base_url}
environment: test
browser:
  ignore_https_errors: {str(ignore_https).lower()}
roles:
  - name: admin
    username: user@example.com
    password: testpass
""",
            encoding="utf-8",
        )
        return cfg

    def test_tls_warning_for_non_local_url(self, tmp_path, capsys):
        from config.loader import load_system_config

        cfg_path = self._write_config(
            tmp_path,
            base_url="https://prod.example.com",
            ignore_https=True,
        )
        load_system_config(cfg_path)

        captured = capsys.readouterr()
        assert "WARNING" in captured.err
        assert "ignore_https_errors" in captured.err

    def test_no_tls_warning_for_localhost(self, tmp_path, capsys):
        from config.loader import load_system_config

        cfg_path = self._write_config(
            tmp_path,
            base_url="http://localhost:3000",
            ignore_https=True,
        )
        load_system_config(cfg_path)

        captured = capsys.readouterr()
        assert "WARNING" not in captured.err
