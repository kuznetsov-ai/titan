"""Scenario runner — executes E2E scenarios and generates AI-enhanced report."""

from __future__ import annotations

import asyncio
from datetime import datetime
from pathlib import Path

from playwright.async_api import async_playwright

from ai.client import ask_vision_json
from config.loader import SystemConfig
from core.auth import login
from scenarios.case_manager import CaseManagerScenarios, StepResult

# ── External scenario loader ──────────────────────────────
# Scenarios live in testMe/ folders of target repos.
# Registry comes from system config YAML (external_scenarios section).

# Allowed root directories for external scenario loading.
# Paths outside these roots are rejected to prevent arbitrary code execution.
ALLOWED_SCENARIO_ROOTS = [
    Path.home() / "Projects",
]


def _validate_scenario_path(testme_dir: str) -> Path:
    """Validate that scenario path is under allowed roots and contains expected file."""
    resolved = Path(testme_dir).resolve()

    # Must be under an allowed root
    if not any(resolved.is_relative_to(root.resolve()) for root in ALLOWED_SCENARIO_ROOTS):
        raise ValueError(
            f"Scenario path {resolved} is outside allowed roots: {ALLOWED_SCENARIO_ROOTS}"
        )

    # Must be a directory named testMe (convention)
    if resolved.name != "testMe":
        print(f"  WARNING: scenario dir is not named 'testMe': {resolved.name}")

    # Must contain ui_test_scenarios.py
    module_path = resolved / "ui_test_scenarios.py"
    if not module_path.exists():
        raise FileNotFoundError(f"Scenario file not found: {module_path}")

    # Must not be a symlink (prevent symlink attacks)
    if module_path.is_symlink():
        raise ValueError(f"Refusing to load symlinked scenario: {module_path}")

    return module_path


def _load_external_scenario(scenario_name: str, config: SystemConfig):
    """Dynamically import scenario class from testMe folder."""
    import importlib.util

    testme_dir = config.external_scenarios.get(scenario_name)
    if not testme_dir:
        return None

    try:
        module_path = _validate_scenario_path(testme_dir)
    except (ValueError, FileNotFoundError) as e:
        print(f"  WARNING: {e}")
        return None

    import sys as _sys
    mod_name = f"titan_ext_{scenario_name.replace('-', '_')}"
    spec = importlib.util.spec_from_file_location(mod_name, str(module_path))
    mod = importlib.util.module_from_spec(spec)
    _sys.modules[mod_name] = mod  # required for Python 3.9 + from __future__ import annotations
    spec.loader.exec_module(mod)

    # Find the scenario class (first class with run_all method)
    for attr_name in dir(mod):
        attr = getattr(mod, attr_name)
        if isinstance(attr, type) and hasattr(attr, "run_all") and attr_name != "StepResult":
            return attr
    return None


async def run_scenario(config: SystemConfig, scenario_name: str = "case-manager", only: list[str] | None = None) -> Path:
    """Run an E2E scenario suite. Returns path to report."""
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    run_dir = Path("storage_layout/runs") / f"e2e_{timestamp}"
    run_dir.mkdir(parents=True, exist_ok=True)

    all_results: list[StepResult] = []

    async with async_playwright() as pw:
        browser_type = getattr(pw, config.browser.type)
        browser = await browser_type.launch(headless=config.browser.headless)

        for role in config.roles:
            print(f"\n{'='*60}")
            print(f"  E2E: {scenario_name} | Role: {role.name}")
            print(f"{'='*60}")

            context = await browser.new_context(
                viewport={
                    "width": config.browser.viewport_width,
                    "height": config.browser.viewport_height,
                },
                ignore_https_errors=config.browser.ignore_https_errors,
            )
            page = await context.new_page()

            # Login
            print(f"  Logging in as {role.name}...")
            success = await login(page, config, role)
            if not success:
                print(f"  ❌ Login failed for {role.name}")
                await context.close()
                continue
            print("  ✅ Logged in successfully")

            # Run scenarios
            if scenario_name == "case-manager":
                await page.goto(
                    f"{config.base_url}/case-manager",
                    wait_until="networkidle", timeout=30000,
                )
                await asyncio.sleep(1)
                suite = CaseManagerScenarios(page, config.base_url, run_dir)
                results = await suite.run_all(only=only)
                all_results.extend(results)

            elif scenario_name in config.external_scenarios:
                scenario_cls = _load_external_scenario(scenario_name, config)
                if scenario_cls is None:
                    print(f"  ❌ Failed to load scenario: {scenario_name}")
                    await context.close()
                    continue
                # Navigate to the scenario URL (from REPORT_URL class attr or default)
                report_url = getattr(scenario_cls, "REPORT_URL", f"/{scenario_name}")
                await page.goto(
                    f"{config.base_url}{report_url}",
                    wait_until="networkidle", timeout=30000,
                )
                await asyncio.sleep(2)
                suite = scenario_cls(page, config.base_url, run_dir)
                results = await suite.run_all(only=only)
                all_results.extend(results)

            await context.close()

        await browser.close()

    # Generate report
    report_path = _generate_e2e_report(
        scenario_name, config, all_results, run_dir,
    )

    # AI analysis of failed/warn steps
    failed_steps = [r for r in all_results if r.status in ("FAIL", "WARN") and r.screenshot_path]
    if failed_steps:
        print(f"\n  Running AI analysis on {len(failed_steps)} issues...")
        ai_report_path = run_dir / "ai_analysis.md"
        ai_lines = ["# AI Analysis of E2E Failures\n"]

        for step in failed_steps:
            print(f"    Analyzing: {step.name}...")
            try:
                analysis = ask_vision_json(
                    f"You are a QA engineer. This screenshot is from an E2E test step "
                    f"'{step.name}' that resulted in {step.status}.\n"
                    f"Step description: {step.description}\n"
                    f"JS errors: {step.js_errors or 'none'}\n"
                    f"Network errors: {step.network_errors or 'none'}\n\n"
                    f"Analyze the screenshot and respond in JSON:\n"
                    f'{{"root_cause": "what went wrong", "suggestion": "how to fix it", '
                    f'"severity": "P0/P1/P2/P3"}}',
                    image_paths=[step.screenshot_path],
                )
                ai_lines.append(f"## {step.name} [{step.status}]")
                ai_lines.append(f"- **Root cause:** {analysis.get('root_cause', 'N/A')}")
                ai_lines.append(f"- **Suggestion:** {analysis.get('suggestion', 'N/A')}")
                ai_lines.append(f"- **Severity:** {analysis.get('severity', 'N/A')}")
                ai_lines.append("")
            except Exception as e:
                ai_lines.append(f"## {step.name} — AI analysis failed: {e}\n")

        ai_report_path.write_text("\n".join(ai_lines), encoding="utf-8")
        print(f"  AI analysis saved to: {ai_report_path}")

    # Cleanup: keep only screenshots from FAIL/WARN steps
    keep_screenshots = {
        Path(r.screenshot_path).resolve()
        for r in all_results
        if r.status in ("FAIL", "WARN") and r.screenshot_path
    }
    for png in run_dir.rglob("*.png"):
        if png.resolve() not in keep_screenshots:
            png.unlink()

    # Remove empty directories after cleanup
    for d in sorted(run_dir.rglob("*"), reverse=True):
        if d.is_dir() and not any(d.iterdir()):
            d.rmdir()

    # Summary
    passed = sum(1 for r in all_results if r.status == "PASS")
    failed = sum(1 for r in all_results if r.status == "FAIL")
    warned = sum(1 for r in all_results if r.status == "WARN")
    kept = sum(1 for r in all_results if r.status != "PASS" and r.screenshot_path)
    print(f"\n{'='*60}")
    print(f"  E2E RESULTS: {passed} passed, {failed} failed, {warned} warnings")
    if kept:
        print(f"  Screenshots kept: {kept} (FAIL/WARN only)")
    print(f"  Report: {report_path}")
    print(f"{'='*60}")

    return report_path


def _generate_e2e_report(
    scenario_name: str,
    config: SystemConfig,
    results: list[StepResult],
    output_dir: Path,
) -> Path:
    """Generate markdown report from E2E results."""
    now = datetime.now()
    report_path = output_dir / "report.md"

    passed = [r for r in results if r.status == "PASS"]
    failed = [r for r in results if r.status == "FAIL"]
    warned = [r for r in results if r.status == "WARN"]

    lines = []
    lines.append(f"# E2E Report — {scenario_name} — {config.environment}")
    lines.append(f"**Date:** {now.strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"**System:** {config.name} ({config.base_url})")
    lines.append(f"**Roles:** {', '.join(r.name for r in config.roles)}")
    lines.append("")

    lines.append("## Summary")
    lines.append("")
    lines.append("| Metric | Count |")
    lines.append("|--------|-------|")
    lines.append(f"| Total steps | {len(results)} |")
    lines.append(f"| Passed | {len(passed)} |")
    lines.append(f"| Failed | {len(failed)} |")
    lines.append(f"| Warnings | {len(warned)} |")
    lines.append("")

    # All steps table
    lines.append("## Test Steps")
    lines.append("")
    lines.append("| # | Step | Status | Duration | Description |")
    lines.append("|---|------|--------|----------|-------------|")
    for i, r in enumerate(results, 1):
        icon = {"PASS": "PASS", "FAIL": "FAIL", "WARN": "WARN"}[r.status]
        desc = r.description[:80].replace("|", "\\|")
        lines.append(f"| {i} | {r.name} | {icon} | {r.duration_ms}ms | {desc} |")
    lines.append("")

    # Failed details
    if failed:
        lines.append("## Failed Steps")
        lines.append("")
        for r in failed:
            lines.append(f"### {r.name}")
            lines.append(f"- **Description:** {r.description}")
            if r.js_errors:
                lines.append(f"- **JS Errors:** {r.js_errors[:3]}")
            if r.network_errors:
                lines.append(f"- **Network Errors:** {r.network_errors[:5]}")
            if r.screenshot_path:
                lines.append(f"- **Screenshot:** `{Path(r.screenshot_path).name}`")
            lines.append("")

    # Warnings
    if warned:
        lines.append("## Warnings")
        lines.append("")
        for r in warned:
            lines.append(f"- **{r.name}:** {r.description}")
            if r.screenshot_path:
                lines.append(f"  - Screenshot: `{Path(r.screenshot_path).name}`")
        lines.append("")

    report_path.write_text("\n".join(lines), encoding="utf-8")
    return report_path
