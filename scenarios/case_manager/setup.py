from __future__ import annotations

import asyncio
import uuid

from scenarios.case_manager.selectors import SEL


class SetupMixin:

    async def setup_test_data(self):
        """S0: Create test data — 2 monitoring + 1 reporting case for all subsequent tests."""
        start = await self._step("setup_test_data")
        try:
            created = []

            uid1 = str(uuid.uuid4())
            uid2 = str(uuid.uuid4())
            uid3 = str(uuid.uuid4())
            uid4 = str(uuid.uuid4())

            # Monitoring non-critical (no files needed)
            ok1 = await self._create_monitoring_case(
                "TITAN Case Alpha", uid1, "TEST-101")
            created.append(("monitoring-medium", ok1))

            # Monitoring critical (files + link required)
            ok2 = await self._create_monitoring_case(
                "TITAN Case Critical", uid2, "TEST-102",
                severity="Critical", with_file=True, link="http://test.example.com")
            created.append(("monitoring-critical", ok2))

            # Reporting non-critical (files required)
            ok3 = await self._create_reporting_case(
                uid3, severity="Medium", with_file=True)
            created.append(("reporting-medium", ok3))

            # Reporting critical (link required, no files)
            ok4 = await self._create_reporting_case(
                uid4, severity="Critical", link="http://report.example.com")
            created.append(("reporting-critical", ok4))

            screenshot = await self._screenshot("00_setup_done")

            # Verify by searching
            await self._click_tab(SEL["tab_cases"])
            await asyncio.sleep(0.5)
            await self.page.locator(SEL["btn_search"]).first.click()
            await self.page.wait_for_load_state("networkidle", timeout=15000)
            await asyncio.sleep(1)

            rows = self.page.locator(f'{SEL["table_cases"]} tbody tr')
            row_count = await rows.count()
            screenshot_table = await self._screenshot("00_setup_table")

            success = [c[0] for c in created if c[1]]
            failed = [c[0] for c in created if not c[1]]

            total = len(created)
            if len(success) >= total and row_count >= total:
                self._record("setup_test_data", "PASS",
                             f"Created {len(success)}/{total} cases, table has {row_count} rows",
                             screenshot_table, start)
            elif len(success) > 0:
                self._record("setup_test_data", "WARN",
                             f"Created {len(success)}/{total} cases (failed: {failed}), "
                             f"table has {row_count} rows",
                             screenshot_table, start)
            else:
                self._record("setup_test_data", "FAIL",
                             f"Failed to create test cases: {failed}",
                             screenshot_table, start)
        except Exception as e:
            screenshot = await self._screenshot("00_setup_error")
            self._record("setup_test_data", "FAIL", str(e), screenshot, start)
        return self.results[-1]
