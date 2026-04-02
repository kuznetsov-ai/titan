"""Configuration loader for TITAN."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class RoleConfig:
    name: str
    username: str
    password: str


@dataclass
class AuthConfig:
    type: str = "login_password"
    login_url: str = "/login"
    username_selector: str = "input[name='email'], input[type='email'], input[name='username']"
    password_selector: str = "input[name='password'], input[type='password']"
    submit_selector: str = "button[type='submit']"


@dataclass
class BrowserConfig:
    type: str = "chromium"
    headless: bool = True
    viewport_width: int = 1920
    viewport_height: int = 1080
    timeout: int = 30000
    ignore_https_errors: bool = False


@dataclass
class AIConfig:
    provider: str = "anthropic"
    model: str = "claude-sonnet-4-20250514"
    api_base: str | None = None
    api_key: str | None = None
    depth: str = "deep"


@dataclass
class CrawlConfig:
    max_pages: int = 100
    screenshot_delay: int = 1000
    ignore_patterns: list[str] = field(default_factory=lambda: ["/logout", "/api/*"])
    ignore_selectors: list[str] = field(default_factory=list)


@dataclass
class SystemConfig:
    name: str
    base_url: str
    environment: str
    auth: AuthConfig
    roles: list[RoleConfig]
    browser: BrowserConfig
    ai: AIConfig
    crawl: CrawlConfig
    external_scenarios: dict[str, str] = field(default_factory=dict)  # name → testMe path


def _resolve_env_vars(value):
    """Resolve ${ENV_VAR:default} patterns in strings, recursively in dicts/lists."""
    import os
    import re

    if isinstance(value, str):
        def _replace(m):
            env_var = m.group(1)
            default = m.group(2)
            return os.environ.get(env_var, default if default is not None else "")
        return re.sub(r'\$\{([^:}]+)(?::([^}]*))?\}', _replace, value)
    elif isinstance(value, dict):
        return {k: _resolve_env_vars(v) for k, v in value.items()}
    elif isinstance(value, list):
        return [_resolve_env_vars(v) for v in value]
    return value


def load_system_config(path: str | Path) -> SystemConfig:
    """Load a system configuration from a YAML file."""
    path = Path(path)
    with open(path) as f:
        raw = _resolve_env_vars(yaml.safe_load(f))

    auth_raw = raw.get("auth", {})
    auth = AuthConfig(
        type=auth_raw.get("type", "login_password"),
        login_url=auth_raw.get("login_url", "/login"),
        username_selector=auth_raw.get("username_selector", AuthConfig.username_selector),
        password_selector=auth_raw.get("password_selector", AuthConfig.password_selector),
        submit_selector=auth_raw.get("submit_selector", AuthConfig.submit_selector),
    )

    roles = [
        RoleConfig(name=r["name"], username=r["username"], password=r["password"])
        for r in raw.get("roles", [])
    ]

    browser_raw = raw.get("browser", {})
    viewport = browser_raw.get("viewport", {})
    browser = BrowserConfig(
        type=browser_raw.get("type", "chromium"),
        headless=browser_raw.get("headless", True),
        viewport_width=viewport.get("width", 1920),
        viewport_height=viewport.get("height", 1080),
        timeout=browser_raw.get("timeout", 30000),
        ignore_https_errors=browser_raw.get("ignore_https_errors", False),
    )

    ai_raw = raw.get("ai", {})
    ai = AIConfig(
        provider=ai_raw.get("provider", "anthropic"),
        model=ai_raw.get("model", "claude-sonnet-4-20250514"),
        api_base=ai_raw.get("api_base"),
        api_key=ai_raw.get("api_key"),
        depth=ai_raw.get("depth", "deep"),
    )

    crawl_raw = raw.get("crawl", {})
    crawl = CrawlConfig(
        max_pages=crawl_raw.get("max_pages", 100),
        screenshot_delay=crawl_raw.get("screenshot_delay", 1000),
        ignore_patterns=crawl_raw.get("ignore_patterns", ["/logout", "/api/*"]),
        ignore_selectors=crawl_raw.get("ignore_selectors", []),
    )

    config = SystemConfig(
        name=raw["name"],
        base_url=raw["base_url"],
        environment=raw.get("environment", "test"),
        auth=auth,
        roles=roles,
        browser=browser,
        ai=ai,
        crawl=crawl,
        external_scenarios=raw.get("external_scenarios", {}),
    )

    # Validate
    _VALID_PROVIDERS = {"claude_cli", "anthropic", "openai_compatible"}
    _VALID_BROWSERS = {"chromium", "firefox", "webkit"}
    if config.ai.provider not in _VALID_PROVIDERS:
        raise ValueError(f"Unknown AI provider: {config.ai.provider!r}. Must be one of {_VALID_PROVIDERS}")
    if config.browser.type not in _VALID_BROWSERS:
        raise ValueError(f"Unknown browser type: {config.browser.type!r}. Must be one of {_VALID_BROWSERS}")
    if not config.roles:
        raise ValueError("At least one role must be defined in config")

    # Warn if TLS is disabled for non-local URLs
    if config.browser.ignore_https_errors:
        import sys
        is_local = any(h in config.base_url for h in ("localhost", "127.0.0.1", "[::1]"))
        if not is_local:
            print(
                f"⚠️  WARNING: ignore_https_errors=true for non-local URL {config.base_url}. "
                f"This disables TLS verification and is insecure for production environments.",
                file=sys.stderr,
            )

    return config
