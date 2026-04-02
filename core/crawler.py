"""AI-powered crawler — explores web app, collects screenshots and errors."""

from __future__ import annotations

import asyncio
import fnmatch
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlparse

from playwright.async_api import BrowserContext, Page

from config.loader import RoleConfig, SystemConfig


@dataclass
class PageResult:
    url: str
    title: str
    role: str
    screenshot_path: str | None = None
    load_time_ms: int = 0
    js_errors: list[str] = field(default_factory=list)
    network_errors: list[str] = field(default_factory=list)
    console_warnings: list[str] = field(default_factory=list)
    links_found: list[str] = field(default_factory=list)
    interactive_elements: int = 0


class Crawler:
    """Crawls a web application, taking screenshots and collecting errors."""

    def __init__(
        self,
        context: BrowserContext,
        config: SystemConfig,
        role: RoleConfig,
        output_dir: Path,
    ):
        self.context = context
        self.config = config
        self.role = role
        self.output_dir = output_dir
        self.visited: set[str] = set()
        self.results: list[PageResult] = []
        self.base_domain = urlparse(config.base_url).netloc

    def _should_skip(self, url: str) -> bool:
        """Check if URL matches ignore patterns."""
        path = urlparse(url).path
        for pattern in self.config.crawl.ignore_patterns:
            if fnmatch.fnmatch(path, pattern):
                return True
        return False

    def _normalize_url(self, url: str) -> str:
        """Normalize URL: remove fragment, trailing slash."""
        parsed = urlparse(url)
        # Only crawl same domain
        if parsed.netloc and parsed.netloc != self.base_domain:
            return ""
        path = parsed.path.rstrip("/") or "/"
        return f"{parsed.scheme}://{parsed.netloc}{path}"

    def _safe_filename(self, url: str) -> str:
        """Convert URL to safe filename (path + query hash to avoid collisions)."""
        import hashlib
        parsed = urlparse(url)
        path = parsed.path.strip("/")
        if not path:
            path = "index"
        safe = re.sub(r"[^\w\-]", "_", path)
        # Add short hash if URL has query params to prevent collisions
        if parsed.query:
            h = hashlib.md5(parsed.query.encode()).hexdigest()[:8]
            safe = f"{safe}_{h}"
        return safe

    async def _collect_page_data(self, page: Page, url: str) -> PageResult:
        """Visit a page and collect all data."""
        js_errors: list[str] = []
        network_errors: list[str] = []
        console_warnings: list[str] = []

        # Listen for errors
        page.on("pageerror", lambda err: js_errors.append(str(err)))
        page.on("console", lambda msg: (
            console_warnings.append(msg.text)
            if msg.type in ("warning", "error") else None
        ))

        def on_response(response):
            if response.status >= 400:
                network_errors.append(f"{response.status} {response.url}")

        page.on("response", on_response)

        # Navigate
        start = time.monotonic()
        try:
            await page.goto(url, wait_until="networkidle", timeout=self.config.browser.timeout)
        except Exception as e:
            return PageResult(
                url=url,
                title="LOAD_ERROR",
                role=self.role.name,
                js_errors=[str(e)],
            )

        # Wait extra for dynamic content
        await asyncio.sleep(self.config.crawl.screenshot_delay / 1000)
        load_time_ms = int((time.monotonic() - start) * 1000)

        title = await page.title()

        # Mask dynamic selectors before screenshot
        for selector in self.config.crawl.ignore_selectors:
            try:
                await page.eval_on_selector_all(
                    selector,
                    "els => els.forEach(el => el.style.visibility = 'hidden')",
                )
            except Exception:
                pass

        # Take screenshot
        screenshots_dir = self.output_dir / "screenshots" / self.role.name
        screenshots_dir.mkdir(parents=True, exist_ok=True)
        filename = f"{self._safe_filename(url)}.png"
        screenshot_path = screenshots_dir / filename
        await page.screenshot(path=str(screenshot_path), full_page=True)

        # Collect links
        links = await page.eval_on_selector_all(
            "a[href]",
            "els => els.map(el => el.href)",
        )

        # Count interactive elements
        interactive_count = await page.eval_on_selector_all(
            "button, a, input, select, textarea, [role='button'], [onclick]",
            "els => els.length",
        )

        # Restore masked elements
        for selector in self.config.crawl.ignore_selectors:
            try:
                await page.eval_on_selector_all(
                    selector,
                    "els => els.forEach(el => el.style.visibility = 'visible')",
                )
            except Exception:
                pass

        return PageResult(
            url=url,
            title=title,
            role=self.role.name,
            screenshot_path=str(screenshot_path),
            load_time_ms=load_time_ms,
            js_errors=js_errors,
            network_errors=network_errors,
            console_warnings=console_warnings,
            links_found=links,
            interactive_elements=interactive_count,
        )

    async def crawl(self, on_page=None) -> list[PageResult]:
        """Crawl the application starting from base_url. Returns all page results."""
        start_url = self.config.base_url.rstrip("/") + "/"
        queue = [start_url]

        while queue and len(self.visited) < self.config.crawl.max_pages:
            url = queue.pop(0)
            normalized = self._normalize_url(url)

            if not normalized or normalized in self.visited or self._should_skip(normalized):
                continue

            self.visited.add(normalized)

            page = await self.context.new_page()
            try:
                result = await self._collect_page_data(page, url)
                self.results.append(result)

                if on_page:
                    on_page(result)

                # Add discovered links to queue
                for link in result.links_found:
                    norm_link = self._normalize_url(link)
                    if norm_link and norm_link not in self.visited:
                        queue.append(link)
            finally:
                await page.close()

        return self.results
