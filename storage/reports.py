"""Report generator — creates .md reports from test results."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from ai.analyst import AnalysisResult
from ai.visual import DiffResult
from core.crawler import PageResult


def generate_report(
    system_name: str,
    environment: str,
    crawl_results: list[PageResult],
    analysis_results: list[AnalysisResult],
    diff_results: list[DiffResult] | None = None,
    output_dir: Path | None = None,
) -> Path:
    """Generate a markdown QA report."""
    now = datetime.now()
    timestamp = now.strftime("%Y-%m-%d_%H-%M-%S")

    if output_dir is None:
        output_dir = Path("storage_layout/runs") / timestamp

    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / "report.md"

    # Group by role
    roles = sorted(set(r.role for r in crawl_results))

    # Count by severity
    bugs = [a for a in analysis_results if a.status == "BUG"]
    uncertain = [a for a in analysis_results if a.status == "UNCERTAIN"]

    severity_counts = {"P0": 0, "P1": 0, "P2": 0, "P3": 0}
    for a in analysis_results:
        if a.severity in severity_counts:
            severity_counts[a.severity] += 1

    lines = []
    lines.append(f"# QA Report — {system_name} — {environment}")
    lines.append(f"**Date:** {now.strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"**Roles tested:** {', '.join(roles)}")
    lines.append(f"**Pages crawled:** {len(crawl_results)}")
    lines.append("")

    # Summary table
    lines.append("## Summary")
    lines.append("")
    lines.append("| Metric | Count |")
    lines.append("|--------|-------|")
    lines.append(f"| Total pages | {len(crawl_results)} |")
    lines.append(f"| Bugs found | {len(bugs)} |")
    lines.append(f"| Uncertain | {len(uncertain)} |")
    lines.append(f"| P0 (critical) | {severity_counts['P0']} |")
    lines.append(f"| P1 (high) | {severity_counts['P1']} |")
    lines.append(f"| P2 (medium) | {severity_counts['P2']} |")
    lines.append(f"| P3 (low) | {severity_counts['P3']} |")
    lines.append("")

    # Role summary
    lines.append("## Coverage by Role")
    lines.append("")
    lines.append("| Role | Pages | Bugs | Uncertain |")
    lines.append("|------|-------|------|-----------|")
    for role in roles:
        role_pages = [r for r in crawl_results if r.role == role]
        role_bugs = [a for a in bugs if a.role == role]
        role_uncertain = [a for a in uncertain if a.role == role]
        lines.append(f"| {role} | {len(role_pages)} | {len(role_bugs)} | {len(role_uncertain)} |")
    lines.append("")

    # Critical bugs (P0-P1)
    critical = [a for a in analysis_results if a.severity in ("P0", "P1") and a.status == "BUG"]
    if critical:
        lines.append("## Critical Issues (P0-P1)")
        lines.append("")
        for i, bug in enumerate(critical, 1):
            lines.append(f"### {i}. [{bug.severity}] {bug.category} — {bug.page_url}")
            lines.append(f"- **Role:** {bug.role}")
            lines.append(f"- **Category:** {bug.category}")
            lines.append(f"- **Description:** {bug.description}")
            # Find matching crawl result for screenshot
            matching = [c for c in crawl_results if c.url == bug.page_url and c.role == bug.role]
            if matching and matching[0].screenshot_path:
                rel_path = Path(matching[0].screenshot_path).name
                lines.append(f"- **Screenshot:** `{rel_path}`")
            lines.append("")

    # Other bugs (P2-P3)
    other_bugs = [a for a in analysis_results if a.severity in ("P2", "P3") and a.status == "BUG"]
    if other_bugs:
        lines.append("## Other Issues (P2-P3)")
        lines.append("")
        for bug in other_bugs:
            lines.append(f"- **[{bug.severity}]** `{bug.page_url}` ({bug.role}) — {bug.description}")
        lines.append("")

    # Uncertain findings
    if uncertain:
        lines.append("## Needs Review (UNCERTAIN)")
        lines.append("")
        for item in uncertain:
            lines.append(f"- `{item.page_url}` ({item.role}) — {item.description}")
        lines.append("")

    # Visual diff results
    if diff_results:
        diff_issues = [d for d in diff_results if d.status != "OK"]
        if diff_issues:
            lines.append("## Visual Regressions")
            lines.append("")
            for d in diff_issues:
                lines.append(f"- **[{d.severity}] [{d.status}]** `{d.page_url}` ({d.role}) — {d.description}")
            lines.append("")

    # Performance warnings
    slow_pages = [r for r in crawl_results if r.load_time_ms > 3000]
    if slow_pages:
        lines.append("## Slow Pages (>3s)")
        lines.append("")
        lines.append("| URL | Role | Load time |")
        lines.append("|-----|------|-----------|")
        for p in sorted(slow_pages, key=lambda x: -x.load_time_ms):
            lines.append(f"| {p.url} | {p.role} | {p.load_time_ms}ms |")
        lines.append("")

    # JS errors
    pages_with_errors = [r for r in crawl_results if r.js_errors]
    if pages_with_errors:
        lines.append("## JavaScript Errors")
        lines.append("")
        for p in pages_with_errors:
            lines.append(f"- `{p.url}` ({p.role}):")
            for err in p.js_errors[:3]:
                lines.append(f"  - `{err[:200]}`")
        lines.append("")

    # All pages list
    lines.append("## All Pages Crawled")
    lines.append("")
    lines.append("| URL | Role | Title | Load (ms) | Status |")
    lines.append("|-----|------|-------|-----------|--------|")
    for r in crawl_results:
        matching_analysis = [a for a in analysis_results if a.page_url == r.url and a.role == r.role]
        status_str = matching_analysis[0].status if matching_analysis else "—"
        lines.append(f"| {r.url} | {r.role} | {r.title} | {r.load_time_ms} | {status_str} |")
    lines.append("")

    report_content = "\n".join(lines)
    report_path.write_text(report_content, encoding="utf-8")

    return report_path
