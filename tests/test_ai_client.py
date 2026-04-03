"""Tests for the async multi-provider AI client."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from ai import client
from config.loader import AIConfig


@pytest.fixture(autouse=True)
def _reset_global_config():
    """Reset the module-level _config before each test."""
    client._config = None
    yield
    client._config = None


def _run(coro):
    """Helper to run async function in sync test."""
    return asyncio.get_event_loop().run_until_complete(coro)


# ── Configuration tests ───────────────────────────────────────


def test_default_config():
    """No configure() called — uses claude_cli fallback."""
    cfg = client._get_config()
    assert cfg.provider == "claude_cli"
    assert cfg.model == "sonnet"


def test_configure_sets_global():
    """configure(AIConfig(...)) then _get_config() returns it."""
    custom = AIConfig(provider="anthropic", model="claude-opus-4-20250514", api_key="sk-test")
    client.configure(custom)
    cfg = client._get_config()
    assert cfg is custom
    assert cfg.provider == "anthropic"
    assert cfg.model == "claude-opus-4-20250514"
    assert cfg.api_key == "sk-test"


# ── Provider dispatch tests ──────────────────────────────────


def test_claude_cli_provider():
    """provider='claude_cli' calls async subprocess."""
    client.configure(AIConfig(provider="claude_cli", model="sonnet"))

    mock_cli = AsyncMock(return_value="CLI response text")
    with patch.object(client, "_call_claude_cli", mock_cli):
        result = _run(client.ask_vision("describe the page"))

    mock_cli.assert_called_once()
    assert result == "CLI response text"


def test_anthropic_provider_no_key(monkeypatch):
    """provider='anthropic', no api_key -> ValueError."""
    client.configure(AIConfig(provider="anthropic", model="claude-sonnet-4-20250514", api_key=None))
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    with pytest.raises(ValueError, match="Anthropic provider requires api_key"):
        _run(client.ask_vision("test prompt"))


def test_openai_provider_no_base():
    """provider='openai_compatible', no api_base -> ValueError."""
    client.configure(AIConfig(provider="openai_compatible", model="gpt-4", api_base=None))

    with pytest.raises(ValueError, match="openai_compatible provider requires api_base"):
        _run(client.ask_vision("test prompt"))


def test_unknown_provider():
    """provider='gpt4all' -> ValueError with helpful message."""
    client.configure(AIConfig(provider="gpt4all", model="anything"))

    with pytest.raises(ValueError, match="Unknown AI provider.*gpt4all.*Supported"):
        _run(client.ask_vision("test prompt"))


# ── ask_vision_json parsing tests ────────────────────────────


def test_ask_vision_json_parses_json():
    """Mock ask_vision to return clean JSON -> parsed dict."""
    mock_vision = AsyncMock(return_value='{"key": "value"}')
    with patch.object(client, "ask_vision", mock_vision):
        result = _run(client.ask_vision_json("get json"))
    assert result == {"key": "value"}


def test_ask_vision_json_strips_markdown():
    """Mock ask_vision to return markdown-fenced JSON -> parsed."""
    mock_vision = AsyncMock(return_value='```json\n{"key": "val"}\n```')
    with patch.object(client, "ask_vision", mock_vision):
        result = _run(client.ask_vision_json("get json"))
    assert result == {"key": "val"}


def test_ask_vision_json_finds_json_in_text():
    """Mock ask_vision to return JSON embedded in text -> parsed."""
    mock_vision = AsyncMock(return_value='Here is the result: {"key": "val"} done')
    with patch.object(client, "ask_vision", mock_vision):
        result = _run(client.ask_vision_json("get json"))
    assert result == {"key": "val"}


def test_ask_vision_json_parse_failure():
    """Mock ask_vision to return non-JSON -> dict with _error key."""
    mock_vision = AsyncMock(return_value="not json at all")
    with patch.object(client, "ask_vision", mock_vision):
        result = _run(client.ask_vision_json("get json"))
    assert "_error" in result
    assert "_raw" in result
    assert result["_raw"] == "not json at all"
