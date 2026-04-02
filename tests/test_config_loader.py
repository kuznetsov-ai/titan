"""Tests for config/loader.py."""

from __future__ import annotations

import pytest
import yaml

from config.loader import (
    AIConfig,
    BrowserConfig,
    RoleConfig,
    load_system_config,
)


def _write_yaml(path, data):
    with open(path, "w") as f:
        yaml.dump(data, f)


class TestLoadValidYaml:
    def test_load_valid_yaml(self, tmp_path):
        cfg_file = tmp_path / "full.yaml"
        data = {
            "name": "backoffice",
            "base_url": "http://localhost:3000",
            "environment": "staging",
            "auth": {
                "type": "oauth",
                "login_url": "/auth/login",
                "username_selector": "#user",
                "password_selector": "#pass",
                "submit_selector": "#go",
            },
            "roles": [
                {"name": "admin", "username": "admin@home.app", "password": "admin"},
                {"name": "viewer", "username": "viewer@home.app", "password": "view"},
            ],
            "browser": {
                "type": "firefox",
                "headless": False,
                "viewport": {"width": 1280, "height": 720},
                "timeout": 60000,
            },
            "ai": {
                "provider": "openai_compatible",
                "model": "gpt-4",
                "api_base": "https://api.openai.com",
                "api_key": "sk-test",
                "depth": "shallow",
            },
            "crawl": {
                "max_pages": 50,
                "screenshot_delay": 500,
                "ignore_patterns": ["/health"],
                "ignore_selectors": [".ad-banner"],
            },
        }
        _write_yaml(cfg_file, data)

        cfg = load_system_config(cfg_file)

        assert cfg.name == "backoffice"
        assert cfg.base_url == "http://localhost:3000"
        assert cfg.environment == "staging"

        assert cfg.auth.type == "oauth"
        assert cfg.auth.login_url == "/auth/login"
        assert cfg.auth.username_selector == "#user"
        assert cfg.auth.password_selector == "#pass"
        assert cfg.auth.submit_selector == "#go"

        assert len(cfg.roles) == 2
        assert cfg.roles[0].name == "admin"
        assert cfg.roles[1].username == "viewer@home.app"

        assert cfg.browser.type == "firefox"
        assert cfg.browser.headless is False
        assert cfg.browser.viewport_width == 1280
        assert cfg.browser.viewport_height == 720
        assert cfg.browser.timeout == 60000

        assert cfg.ai.provider == "openai_compatible"
        assert cfg.ai.model == "gpt-4"
        assert cfg.ai.api_base == "https://api.openai.com"
        assert cfg.ai.api_key == "sk-test"
        assert cfg.ai.depth == "shallow"

        assert cfg.crawl.max_pages == 50
        assert cfg.crawl.screenshot_delay == 500
        assert cfg.crawl.ignore_patterns == ["/health"]
        assert cfg.crawl.ignore_selectors == [".ad-banner"]


class TestLoadMinimalYaml:
    def test_load_minimal_yaml(self, tmp_path):
        cfg_file = tmp_path / "minimal.yaml"
        data = {
            "name": "myapp",
            "base_url": "http://localhost:8080",
            "roles": [{"name": "user", "username": "u", "password": "p"}],
        }
        _write_yaml(cfg_file, data)

        cfg = load_system_config(cfg_file)

        assert cfg.name == "myapp"
        assert cfg.base_url == "http://localhost:8080"
        assert cfg.environment == "test"

        # Auth defaults
        assert cfg.auth.type == "login_password"
        assert cfg.auth.login_url == "/login"

        # Browser defaults
        assert cfg.browser.headless is True
        assert cfg.browser.viewport_width == 1920
        assert cfg.browser.viewport_height == 1080
        assert cfg.browser.type == "chromium"
        assert cfg.browser.ignore_https_errors is False

        # AI defaults
        assert cfg.ai.provider == "anthropic"
        assert cfg.ai.model == "claude-sonnet-4-20250514"

        # Crawl defaults
        assert cfg.crawl.max_pages == 100
        assert cfg.crawl.screenshot_delay == 1000
        assert cfg.crawl.ignore_patterns == ["/logout", "/api/*"]
        assert cfg.crawl.ignore_selectors == []

        # Roles
        assert len(cfg.roles) == 1


class TestBrowserDefaults:
    def test_browser_defaults(self):
        b = BrowserConfig()
        assert b.type == "chromium"
        assert b.headless is True
        assert b.viewport_width == 1920
        assert b.viewport_height == 1080
        assert b.timeout == 30000
        assert b.ignore_https_errors is False


class TestAIConfigDefaults:
    def test_ai_config_defaults(self):
        ai = AIConfig()
        assert ai.provider == "anthropic"
        assert ai.model == "claude-sonnet-4-20250514"
        assert ai.api_base is None
        assert ai.api_key is None
        assert ai.depth == "deep"


class TestMissingFile:
    def test_missing_file(self):
        with pytest.raises((FileNotFoundError, OSError)):
            load_system_config("/nonexistent/path/config.yaml")


class TestMultipleRoles:
    def test_multiple_roles(self, tmp_path):
        cfg_file = tmp_path / "roles.yaml"
        roles_data = [
            {"name": "admin", "username": "a@a.com", "password": "aaa"},
            {"name": "manager", "username": "m@a.com", "password": "mmm"},
            {"name": "viewer", "username": "v@a.com", "password": "vvv"},
        ]
        data = {
            "name": "multi",
            "base_url": "http://localhost",
            "roles": roles_data,
        }
        _write_yaml(cfg_file, data)

        cfg = load_system_config(cfg_file)

        assert len(cfg.roles) == 3
        assert [r.name for r in cfg.roles] == ["admin", "manager", "viewer"]
        assert [r.username for r in cfg.roles] == ["a@a.com", "m@a.com", "v@a.com"]
        assert [r.password for r in cfg.roles] == ["aaa", "mmm", "vvv"]
        assert all(isinstance(r, RoleConfig) for r in cfg.roles)


class TestConfigValidation:
    def test_invalid_provider(self, tmp_path):
        cfg_file = tmp_path / "bad_provider.yaml"
        _write_yaml(cfg_file, {
            "name": "x", "base_url": "http://localhost",
            "roles": [{"name": "a", "username": "a", "password": "a"}],
            "ai": {"provider": "gpt4all"},
        })
        with pytest.raises(ValueError, match="Unknown AI provider"):
            load_system_config(cfg_file)

    def test_invalid_browser(self, tmp_path):
        cfg_file = tmp_path / "bad_browser.yaml"
        _write_yaml(cfg_file, {
            "name": "x", "base_url": "http://localhost",
            "roles": [{"name": "a", "username": "a", "password": "a"}],
            "browser": {"type": "safari"},
        })
        with pytest.raises(ValueError, match="Unknown browser type"):
            load_system_config(cfg_file)

    def test_no_roles(self, tmp_path):
        cfg_file = tmp_path / "no_roles.yaml"
        _write_yaml(cfg_file, {"name": "x", "base_url": "http://localhost"})
        with pytest.raises(ValueError, match="At least one role"):
            load_system_config(cfg_file)
