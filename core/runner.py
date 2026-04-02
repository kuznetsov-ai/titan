"""Session runner — orchestrates the full test run."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from playwright.async_api import async_playwright

from ai.analyst import AnalysisResult, analyze_page
from ai.visual import DiffResult, compare_screenshots
from config.loader import SystemConfig
from core.auth import create_authenticated_context
from core.crawler import Crawler, PageResult
from storage.baselines import get_baseline_path, has_baselines, save_baselines
from storage.reports import generate_report


async def run_session(config: SystemConfig, update_baselines: bool = False) -> Path:
    """Run a full test session for all roles. Returns path to report."""
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    run_dir = Path("storage_layout/runs") / timestamp
    run_dir.mkdir(parents=True, exist_ok=True)

    all_crawl_results: list[PageResult] = []
    all_analysis_results: list[AnalysisResult] = []
    all_diff_results: list[DiffResult] = []

    async with async_playwright() as pw:
        browser_type = getattr(pw, config.browser.type)
        browser = await browser_type.launch(headless=config.browser.headless)

        for role in config.roles:
            print(f"\n{'='*60}")
            print(f"  Testing role: {role.name} ({role.username})")
            print(f"{'='*60}")

            # Authenticate
            print(f"  Logging in as {role.name}...")
            context = await create_authenticated_context(browser, config, role)

            # Crawl
            print("  Crawling pages...")
            crawler = Crawler(context, config, role, run_dir)

            def on_page(result: PageResult):
                status = "OK" if not result.js_errors else f"JS_ERR({len(result.js_errors)})"
                print(f"    [{status}] {result.url} ({result.load_time_ms}ms)")

            results = await crawler.crawl(on_page=on_page)
            all_crawl_results.extend(results)
            print(f"  Crawled {len(results)} pages for role '{role.name}'")

            # AI Analysis
            print("  Analyzing pages with AI...")
            for result in results:
                analysis = analyze_page(result, model=config.ai.model,
                                        api_base=config.ai.api_base, api_key=config.ai.api_key)
                all_analysis_results.append(analysis)
                if analysis.status != "OK":
                    print(f"    [{analysis.status}][{analysis.severity}] {result.url} — {analysis.description[:80]}")

            # Visual diff against baselines
            if has_baselines(config.name) and not update_baselines:
                print("  Comparing with baselines...")
                for result in results:
                    if not result.screenshot_path:
                        continue
                    filename = Path(result.screenshot_path).name
                    baseline = get_baseline_path(config.name, role.name, filename)
                    if baseline:
                        diff = compare_screenshots(
                            baseline, result.screenshot_path,
                            result.url, role.name, model=config.ai.model,
                            api_base=config.ai.api_base, api_key=config.ai.api_key,
                        )
                        all_diff_results.append(diff)
                        if diff.status != "OK":
                            print(f"    [DIFF][{diff.severity}] {result.url} — {diff.description[:80]}")

            await context.close()

        await browser.close()

    # Update baselines if requested
    if update_baselines:
        screenshots_dir = run_dir / "screenshots"
        count = save_baselines(config.name, screenshots_dir)
        print(f"\n  Baselines updated: {count} screenshots saved")

    # Generate report
    report_path = generate_report(
        system_name=config.name,
        environment=config.environment,
        crawl_results=all_crawl_results,
        analysis_results=all_analysis_results,
        diff_results=all_diff_results if all_diff_results else None,
        output_dir=run_dir,
    )

    # Print summary
    bugs = [a for a in all_analysis_results if a.status == "BUG"]
    uncertain = [a for a in all_analysis_results if a.status == "UNCERTAIN"]
    print(f"\n{'='*60}")
    print(f"  RESULTS: {len(all_crawl_results)} pages, {len(bugs)} bugs, {len(uncertain)} uncertain")
    print(f"  Report: {report_path}")
    print(f"{'='*60}")

    return report_path
