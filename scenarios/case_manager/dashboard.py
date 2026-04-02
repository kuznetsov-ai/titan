from __future__ import annotations

import asyncio

from scenarios.case_manager.selectors import SEL


class DashboardMixin:

    async def test_dashboard(self):
        """S14: Open Dashboard, click FILTER, verify charts and stats render."""
        start = await self._step("dashboard")
        try:
            await self._close_dialog()
            await self._click_tab(SEL["tab_dashboard"])
            await asyncio.sleep(1)

            # Click FILTER button
            filter_btn = self.page.locator('button:has-text("FILTER"), button:has-text("Filter")')
            if await filter_btn.count() > 0:
                await filter_btn.first.click()
                await asyncio.sleep(3)  # charts need time to render

            screenshot = await self._screenshot("14a_dashboard")

            # Check for Highcharts rendered charts
            charts = self.page.locator('[class*="PieChart"], [class*="Highchart"], [class*="highcharts-container"]')
            chart_count = await charts.count()

            # Check for stats text
            page_text = await self.page.content()
            expected_stats = ["Total cases", "Total suspects"]
            found_stats = [s for s in expected_stats if s in page_text]

            expected_charts = [
                "investigation outcomes",
                "cases by processes",
                "suspects by potential",
                "cases by statuses",
            ]
            # Highcharts uses \u200b (zero-width space) in text, so match substrings
            page_text_clean = page_text.replace("\u200b", "")
            found_charts = [c for c in expected_charts if c.lower() in page_text_clean.lower()]

            # Check filters present
            filter_fields = ["Process", "Severity", "Investigation Outcome", "Country Code"]
            found_filters = [f for f in filter_fields if f in page_text]

            issues = []
            if chart_count == 0:
                issues.append("No Highcharts rendered")
            if len(found_stats) < len(expected_stats):
                missing = [s for s in expected_stats if s not in found_stats]
                issues.append(f"Missing stats: {missing}")
            if len(found_charts) < 3:
                missing = [c for c in expected_charts if c not in found_charts]
                issues.append(f"Missing charts: {missing}")

            if issues:
                self._record("dashboard", "FAIL", "; ".join(issues), screenshot, start)
            else:
                self._record("dashboard", "PASS",
                             f"Dashboard: {chart_count} charts, {len(found_stats)} stats, "
                             f"{len(found_charts)} chart titles, {len(found_filters)} filters",
                             screenshot, start)
        except Exception as e:
            screenshot = await self._screenshot("14_error")
            self._record("dashboard", "FAIL", str(e), screenshot, start)
        return self.results[-1]
