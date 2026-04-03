"""AI client — async multi-provider LLM integration for TITAN.

Supported providers:
  - claude_cli:        Claude Code CLI (`claude --print`) — no API key needed
  - anthropic:         Anthropic API (requires ANTHROPIC_API_KEY)
  - openai_compatible: OpenAI-compatible APIs (local proxies, internal LLMs, Codex, etc.)

All public functions are async to avoid blocking the event loop.
"""

from __future__ import annotations

import asyncio
import base64
import json
import os
from pathlib import Path

from config.loader import AIConfig

# ── Provider registry ──────────────────────────────────────

_config: AIConfig | None = None


def configure(ai_config: AIConfig):
    """Set the global AI config. Call once at startup."""
    global _config
    _config = ai_config


def _get_config() -> AIConfig:
    if _config is None:
        return AIConfig(provider="claude_cli", model="sonnet")
    return _config


def _build_image_content(image_paths: list[Path]) -> list[dict]:
    """Build base64 image content blocks for API calls."""
    content = []
    for img_path in image_paths:
        if img_path.exists():
            data = base64.b64encode(img_path.read_bytes()).decode()
            suffix = img_path.suffix.lower().lstrip(".")
            media_type = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg",
                          "gif": "image/gif", "webp": "image/webp"}.get(suffix, "image/png")
            content.append({"media_type": media_type, "data": data})
    return content


# ── Async provider implementations ────────────────────────

async def _call_claude_cli(prompt: str, image_paths: list[Path], model: str) -> str:
    """Call Claude Code CLI with --print flag (non-blocking subprocess)."""
    parts = []
    for img_path in image_paths:
        if img_path.exists():
            parts.append(f"Read and analyze the screenshot at: {img_path}")
    parts.append(prompt)

    proc = await asyncio.create_subprocess_exec(
        "claude", "--print", "--model", model,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await asyncio.wait_for(
        proc.communicate(input="\n\n".join(parts).encode()),
        timeout=180,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"Claude CLI error (exit {proc.returncode}): {stderr.decode()[:500]}")
    return stdout.decode().strip()


async def _call_anthropic(prompt: str, image_paths: list[Path], model: str, api_key: str) -> str:
    """Call Anthropic Messages API (async httpx)."""
    import httpx

    images = _build_image_content(image_paths)
    content = [
        {"type": "image", "source": {"type": "base64", "media_type": img["media_type"], "data": img["data"]}}
        for img in images
    ]
    content.append({"type": "text", "text": prompt})

    async with httpx.AsyncClient(timeout=180) as client:
        resp = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={"model": model, "max_tokens": 4096, "messages": [{"role": "user", "content": content}]},
        )
    resp.raise_for_status()
    return resp.json()["content"][0]["text"]


async def _call_openai_compatible(prompt: str, image_paths: list[Path],
                                  model: str, api_base: str, api_key: str) -> str:
    """Call OpenAI-compatible API (async httpx)."""
    import httpx

    images = _build_image_content(image_paths)
    content = [
        {"type": "image_url", "image_url": {"url": f"data:{img['media_type']};base64,{img['data']}"}}
        for img in images
    ]
    content.append({"type": "text", "text": prompt})

    url = f"{api_base.rstrip('/')}/chat/completions"
    async with httpx.AsyncClient(timeout=180) as client:
        resp = await client.post(
            url,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={"model": model, "max_tokens": 4096, "messages": [{"role": "user", "content": content}]},
        )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


# ── Public async API ──────────────────────────────────────

async def ask_vision(
    prompt: str,
    image_paths: list[str | Path] | None = None,
    **kwargs,
) -> str:
    """Send a prompt with optional images to the configured LLM provider (async)."""
    cfg = _get_config()
    resolved = [Path(p).resolve() for p in (image_paths or [])]

    if cfg.provider == "claude_cli":
        return await _call_claude_cli(prompt, resolved, cfg.model)
    elif cfg.provider == "anthropic":
        api_key = cfg.api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            raise ValueError("Anthropic provider requires api_key in config or ANTHROPIC_API_KEY env var")
        return await _call_anthropic(prompt, resolved, cfg.model, api_key)
    elif cfg.provider == "openai_compatible":
        if not cfg.api_base:
            raise ValueError("openai_compatible provider requires api_base in config")
        api_key = cfg.api_key or os.environ.get("OPENAI_API_KEY", "not-needed")
        return await _call_openai_compatible(prompt, resolved, cfg.model, cfg.api_base, api_key)
    else:
        raise ValueError(
            f"Unknown AI provider: {cfg.provider!r}. "
            f"Supported: claude_cli, anthropic, openai_compatible"
        )


async def ask_vision_json(
    prompt: str,
    image_paths: list[str | Path] | None = None,
    **kwargs,
) -> dict:
    """Send a prompt to the configured LLM and parse JSON response (async)."""
    raw = await ask_vision(prompt, image_paths, **kwargs)

    # Strip markdown fences if present
    if "```" in raw:
        parts = raw.split("```")
        for part in parts:
            part = part.strip()
            if part.startswith("json"):
                part = part[4:].strip()
            try:
                return json.loads(part)
            except json.JSONDecodeError:
                continue

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start >= 0 and end > start:
            try:
                return json.loads(raw[start:end])
            except json.JSONDecodeError:
                pass
        return {"_raw": raw, "_error": "JSON parse failed"}
