"""AI analyst — reviews crawl results and identifies bugs without baselines."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ai.client import ask_vision_json
from core.crawler import PageResult


@dataclass
class AnalysisResult:
    page_url: str
    role: str
    status: str  # BUG | UNCERTAIN | OK
    severity: str  # P0 | P1 | P2 | P3 | none
    description: str
    category: str  # visual | functional | performance | accessibility


ANALYSIS_PROMPT = """You are an expert QA engineer analyzing a web page screenshot.

Page URL: {url}
Page title: {title}
Role: {role}
Load time: {load_time_ms}ms
JS errors: {js_errors}
Network errors: {network_errors}
Console warnings: {console_warnings}
Interactive elements count: {interactive_count}

Analyze the screenshot and the metadata above. Look for:
1. Visual bugs: broken layout, overlapping elements, cut-off text, missing images
2. Error states: error messages, blank screens, stack traces, 404/500 pages
3. Performance: if load time > 3000ms, flag it
4. Functional hints: disabled buttons that look active, empty tables/lists that should have data
5. Accessibility: tiny text, low contrast, missing labels (only obvious issues)

Respond in this exact JSON format:
{{
    "status": "BUG" or "UNCERTAIN" or "OK",
    "severity": "P0" or "P1" or "P2" or "P3" or "none",
    "category": "visual" or "functional" or "performance" or "accessibility",
    "description": "What you found and why it matters"
}}

If the page looks normal and healthy, respond with status OK and severity none.
Respond ONLY with the JSON, no markdown fences."""


async def analyze_page(
    result: PageResult,
    model: str = "claude-sonnet-4-20250514",
    api_base: str | None = None,
    api_key: str | None = None,
) -> AnalysisResult:
    """Analyze a single page result using AI Vision."""
    prompt = ANALYSIS_PROMPT.format(
        url=result.url,
        title=result.title,
        role=result.role,
        load_time_ms=result.load_time_ms,
        js_errors=result.js_errors or "none",
        network_errors=result.network_errors or "none",
        console_warnings=result.console_warnings[:5] or "none",
        interactive_count=result.interactive_elements,
    )

    image_paths = []
    if result.screenshot_path and Path(result.screenshot_path).exists():
        image_paths.append(result.screenshot_path)

    data = await ask_vision_json(prompt, image_paths)

    # Handle parse errors
    if "_error" in data:
        data = {
            "status": "UNCERTAIN",
            "severity": "P2",
            "category": "visual",
            "description": f"AI response parse error: {data.get('_raw', '')}",
        }

    # Auto-flag from metadata
    if result.title == "LOAD_ERROR":
        data = {"status": "BUG", "severity": "P0", "category": "functional",
                "description": f"Page failed to load: {result.js_errors}"}
    elif result.load_time_ms > 3000 and data.get("status") == "OK":
        data["status"] = "UNCERTAIN"
        data["severity"] = "P2"
        data["category"] = "performance"
        data["description"] = f"Slow load ({result.load_time_ms}ms). " + data.get("description", "")

    return AnalysisResult(
        page_url=result.url,
        role=result.role,
        status=data.get("status", "UNCERTAIN"),
        severity=data.get("severity", "P2"),
        description=data.get("description", "No description"),
        category=data.get("category", "visual"),
    )
