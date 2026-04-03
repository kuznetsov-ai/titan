"""Case Manager-specific helper methods (not part of BaseScenario).

These are used by SetupMixin, CasesMixin, and FilesMixin but are domain-specific
and should not be in the generic BaseScenario class.
"""

from __future__ import annotations

import asyncio

from scenarios.case_manager.selectors import SEL


class CaseManagerHelpersMixin:
    """Helpers specific to Case Manager UI (create/open cases)."""

    async def _create_monitoring_case(self, title: str, uid: str, jira: str,
                                       severity: str = "Medium",
                                       with_file: bool = False,
                                       link: str | None = None) -> bool:
        """Create a monitoring case via UI. Returns True on success."""
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
        """Create a reporting case via UI. Returns True on success."""
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

        if severity.lower() != "critical":
            timeframe = self.page.locator('[name="suspicious_timeframe"]')
            if await timeframe.count() > 0:
                await timeframe.first.click()
                await asyncio.sleep(0.5)
                preset = self.page.locator('button.ListItem_item:has-text("Last 30 days")')
                if await preset.count() > 0:
                    await preset.first.click()
                    await asyncio.sleep(0.5)

        if with_file:
            await self._attach_test_file()

        submit = self.page.locator(SEL["btn_create_reporting"])
        return await self._submit_and_check(submit)

    async def _open_case_by_index(self, index: int = 0) -> bool:
        """Open nth case from search results. Returns True if opened."""
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
