from __future__ import annotations

import asyncio
import os
import time
from dataclasses import dataclass, field
from pathlib import Path

from playwright.async_api import Page


@dataclass
class StepResult:
    name: str
    status: str  # PASS | FAIL | WARN
    description: str
    screenshot_path: str | None = None
    duration_ms: int = 0
    js_errors: list[str] = field(default_factory=list)
    network_errors: list[str] = field(default_factory=list)


class BaseScenario:
    """Base class for E2E test scenarios."""

    OUTPUT_SUBDIR = "default"

    def __init__(self, page: Page, base_url: str, output_dir: Path):
        self.page = page
        self.base_url = base_url.rstrip("/")
        self.output_dir = output_dir / self.OUTPUT_SUBDIR
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.results: list[StepResult] = []
        self.js_errors: list[str] = []
        self.network_errors: list[str] = []

        page.on("pageerror", lambda err: self.js_errors.append(str(err)))
        page.on("response", lambda resp: (
            self.network_errors.append(f"{resp.status} {resp.url}")
            if resp.status >= 400 else None
        ))

    async def _screenshot(self, name: str) -> str:
        path = self.output_dir / f"{name}.png"
        await self.page.screenshot(path=str(path), full_page=True)
        return str(path)

    async def _step(self, name: str):
        self.js_errors.clear()
        self.network_errors.clear()
        return time.monotonic()

    def _record(self, name: str, status: str, description: str,
                screenshot: str | None, start_time: float):
        self.results.append(StepResult(
            name=name, status=status, description=description,
            screenshot_path=screenshot,
            duration_ms=int((time.monotonic() - start_time) * 1000),
            js_errors=list(self.js_errors),
            network_errors=list(self.network_errors),
        ))

    async def _click_tab(self, tab_selector: str) -> bool:
        loc = self.page.locator(tab_selector)
        if await loc.count() > 0:
            try:
                await loc.first.click(timeout=5000)
            except Exception:
                # Might be blocked by toast/overlay — try closing it first
                await self._close_dialog()
                await asyncio.sleep(0.3)
                try:
                    await loc.first.click(timeout=5000)
                except Exception:
                    return False
            await asyncio.sleep(1)
            try:
                await self.page.wait_for_load_state("networkidle", timeout=10000)
            except Exception:
                pass
            return True
        return False

    async def _fill_field(self, selector: str, value: str) -> bool:
        """Fill a text input or textarea."""
        loc = self.page.locator(selector)
        if await loc.count() > 0:
            await loc.first.fill(value)
            return True
        return False

    async def _select_custom_dropdown(self, field_name: str, value: str | None = None) -> bool:
        """Select option in a custom Select component.

        Click input[name=field_name] to open dropdown,
        then click button.ListItem_item (first or matching value).
        """
        inp = self.page.locator(f'input[name="{field_name}"]')
        if await inp.count() == 0:
            return False

        # Force click — Select_searchInput is small and may not pass actionability checks
        await inp.first.click(force=True)
        await asyncio.sleep(0.5)

        # Wait for dropdown options
        options = self.page.locator('button[class*="ListItem_item"]')
        try:
            await options.first.wait_for(state="visible", timeout=3000)
        except Exception:
            return False

        if value:
            # Try to find matching option by text
            match = self.page.locator(f'button[class*="ListItem_item"]:has-text("{value}")')
            if await match.count() > 0:
                await match.first.click()
                await asyncio.sleep(0.3)
                return True

        # Click first available option
        if await options.count() > 0:
            await options.first.click()
            await asyncio.sleep(0.3)
            return True
        return False

    async def _create_monitoring_case(self, title: str, uid: str, jira: str,
                                       severity: str = "Medium",
                                       with_file: bool = False,
                                       link: str | None = None) -> bool:
        """Helper: create a monitoring case via UI. Returns True on success."""
        from .case_manager.selectors import SEL
        await self._click_tab(SEL["tab_cases"])
        await asyncio.sleep(0.5)
        await self._click_tab(SEL["tab_create_monitoring"])
        await asyncio.sleep(1)
        await self._fill_field(SEL["field_title"], title)
        await self._fill_field(SEL["field_user_uids"], uid)
        await self._select_custom_dropdown("abuse_type")
        await self._select_custom_dropdown("process")
        await self._select_custom_dropdown("severity", severity)
        await self._fill_field(SEL["field_description"], f"Auto-created by TITAN: {title}")
        await self._fill_field(SEL["field_jira_tickets"], jira)

        if link:
            await self._fill_field(SEL["field_link"], link)

        if with_file:
            await self._attach_test_file()

        submit = self.page.locator(SEL["btn_create_monitoring"])
        return await self._submit_and_check(submit)

    async def _create_reporting_case(self, uid: str,
                                      severity: str = "Medium",
                                      with_file: bool = False,
                                      link: str | None = None) -> bool:
        """Helper: create a reporting case via UI. Returns True on success."""
        from .case_manager.selectors import SEL
        await self._click_tab(SEL["tab_cases"])
        await asyncio.sleep(0.5)
        await self._click_tab(SEL["tab_create_reporting"])
        await asyncio.sleep(1)
        await self._fill_field(SEL["field_user_uids"], uid)
        await self._select_custom_dropdown("abuse_type")
        await self._select_custom_dropdown("symbol")
        await self._select_custom_dropdown("severity", severity)
        await self._fill_field(SEL["field_description"], "Auto-created reporting case by TITAN")

        if link:
            await self._fill_field(SEL["field_link"], link)

        # Non-critical reporting requires suspicious_timeframe
        if severity.lower() != "critical":
            timeframe = self.page.locator('[name="suspicious_timeframe"]')
            if await timeframe.count() > 0:
                await timeframe.first.click()
                await asyncio.sleep(0.5)
                # Click "Last 30 days" preset — auto-closes datepicker
                preset = self.page.locator('button.ListItem_item:has-text("Last 30 days")')
                if await preset.count() > 0:
                    await preset.first.click()
                    await asyncio.sleep(0.5)

        if with_file:
            await self._attach_test_file()

        submit = self.page.locator(SEL["btn_create_reporting"])
        return await self._submit_and_check(submit)

    async def _attach_test_file(self):
        """Attach a test PNG file via the file chooser dialog (like a real user)."""
        test_file = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                  "..", "storage_layout", "test_attachment.png")
        if not os.path.exists(test_file):
            from PIL import Image
            os.makedirs(os.path.dirname(test_file), exist_ok=True)
            Image.new("RGB", (100, 100), color="red").save(test_file)
        test_file = os.path.abspath(test_file)

        # Click "Browse for files" area to trigger file chooser
        browse_area = self.page.locator('[class*="FileInput"]')

        if await browse_area.count() > 0:
            # Use filechooser event — this triggers real JS events like a user
            async with self.page.expect_file_chooser() as fc_info:
                await browse_area.first.click()
            file_chooser = await fc_info.value
            await file_chooser.set_files(test_file)
            await asyncio.sleep(1)
        else:
            # Fallback: direct set_input_files
            file_input = self.page.locator('input[name="files"][type="file"]')
            if await file_input.count() > 0:
                await file_input.first.set_input_files(test_file)
                await asyncio.sleep(0.5)

    async def _submit_and_check(self, submit_locator) -> bool:
        """Click submit button and check for API errors."""
        if await submit_locator.count() > 0:
            await submit_locator.first.scroll_into_view_if_needed()
            self.network_errors.clear()
            await submit_locator.first.click()
            await asyncio.sleep(3)
            try:
                await self.page.wait_for_load_state("networkidle", timeout=15000)
            except Exception:
                pass
            api_errors = [e for e in self.network_errors
                          if "/api/" in e and any(c in e for c in ("400", "422", "500"))]
            return len(api_errors) == 0
        return False

    async def _close_dialog(self):
        """Close any open dialog or toast notification."""
        # Close toast/snackbar notifications first
        toast_close = self.page.locator('[class*="Snackbar"] button, [class*="Toast"] button, [class*="notification"] button')
        if await toast_close.count() > 0:
            try:
                await toast_close.first.click(timeout=1000)
                await asyncio.sleep(0.3)
            except Exception:
                pass

        # Close dialog
        close_btn = self.page.locator('button[class*="Dialog_close"]')
        if await close_btn.count() > 0:
            try:
                await close_btn.first.click(timeout=2000)
                await asyncio.sleep(0.5)
            except Exception:
                pass
            return
        # Fallback: Escape
        await self.page.keyboard.press("Escape")
        await asyncio.sleep(0.5)

    async def _toggle_switch(self, name: str, desired_state: bool) -> bool:
        """Toggle a custom Switch component by name. Returns True if toggled."""
        # Structure: <span class="Switch_switch"><input name="..."/><label class="Switch_label"/></span>
        switch_input = self.page.locator(f'input[name="{name}"]')
        if await switch_input.count() == 0:
            return False
        is_checked = await switch_input.first.is_checked()
        if is_checked != desired_state:
            # Click the label sibling — it triggers the toggle
            label = self.page.locator(f'input[name="{name}"] + label, input[name="{name}"] ~ label')
            if await label.count() > 0:
                await label.first.click()
            else:
                # Fallback: use JS to toggle
                await switch_input.first.evaluate("el => el.click()")
            await asyncio.sleep(0.5)
        return True

    async def _open_case_by_index(self, index: int = 0) -> bool:
        """Open nth case from search results. Returns True if opened."""
        from .case_manager.selectors import SEL
        await self._close_dialog()
        await self._click_tab(SEL["tab_cases"])
        await asyncio.sleep(0.5)
        await self.page.locator(SEL["btn_search"]).first.click()
        await self.page.wait_for_load_state("networkidle", timeout=15000)
        await asyncio.sleep(1)

        rows = self.page.locator(f'{SEL["table_cases"]} tbody tr')
        if await rows.count() <= index:
            return False

        case_btn = rows.nth(index).locator('td:nth-child(2) button[class*="Link_link"]')
        if await case_btn.count() > 0:
            await case_btn.first.click()
            await asyncio.sleep(2)
            return True
        return False
