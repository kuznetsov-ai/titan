"""AI-based visual diff — compares screenshots using AI Vision."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ai.client import ask_vision_json


@dataclass
class DiffResult:
    page_url: str
    role: str
    status: str  # BUG | UNCERTAIN | OK
    severity: str  # P0 | P1 | P2 | P3 | none
    description: str
    baseline_path: str
    current_path: str


DIFF_PROMPT = """You are a QA engineer comparing two screenshots of a web page.

The FIRST image is the BASELINE (expected state).
The SECOND image is the CURRENT state.

Analyze the differences and respond in this exact JSON format:
{
    "status": "BUG" or "UNCERTAIN" or "OK",
    "severity": "P0" or "P1" or "P2" or "P3" or "none",
    "description": "Brief description of what changed and why it matters"
}

Severity guide:
- P0: App is unusable (crash, blank screen, can't navigate)
- P1: Core flow broken (button doesn't work, form won't submit, data missing)
- P2: Works but poorly (slow, layout shift, overlapping elements)
- P3: Cosmetic (typos, minor style inconsistencies)

Rules:
- Ignore dynamic content like timestamps, counters, avatars, notification badges
- Focus on structural changes: missing elements, broken layouts, error messages
- If you see an error page, stack trace, or blank screen — that's P0
- If changes look intentional (new feature), mark as UNCERTAIN
- If no meaningful difference — mark as OK with severity "none"

Respond ONLY with the JSON, no markdown fences."""


async def compare_screenshots(
    baseline_path: str | Path,
    current_path: str | Path,
    page_url: str,
    role: str,
    model: str = "claude-sonnet-4-20250514",
    api_base: str | None = None,
    api_key: str | None = None,
) -> DiffResult:
    """Compare baseline and current screenshots using AI Vision."""
    prompt = f"BASELINE screenshot (first image), then CURRENT screenshot (second image).\n\n{DIFF_PROMPT}"

    data = await ask_vision_json(
        prompt,
        image_paths=[baseline_path, current_path],
    )

    if "_error" in data:
        data = {"status": "UNCERTAIN", "severity": "P2",
                "description": f"AI response parse error: {data.get('_raw', '')}"}

    return DiffResult(
        page_url=page_url,
        role=role,
        status=data.get("status", "UNCERTAIN"),
        severity=data.get("severity", "P2"),
        description=data.get("description", "No description"),
        baseline_path=str(baseline_path),
        current_path=str(current_path),
    )
