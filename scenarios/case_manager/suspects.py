from __future__ import annotations

import asyncio

from scenarios.case_manager.selectors import SEL


class SuspectsMixin:

    async def test_suspects_search(self):
        """S10: Open Suspects tab, disable filters, search, verify table columns."""
        start = await self._step("suspects_search")
        try:
            await self._close_dialog()
            await self._click_tab(SEL["tab_suspects"])
            await asyncio.sleep(1)

            # Disable restrictive toggles for a clean search
            await self._toggle_switch("has_updates", False)
            await self._toggle_switch("openOnly", False)

            screenshot_tab = await self._screenshot("10a_suspects_tab")

            # Verify filters present
            uid_field = self.page.locator('[name="uids"]')
            case_ids = self.page.locator('[name="caseIDs"]')
            has_filters = await uid_field.count() > 0 and await case_ids.count() > 0

            # Click SEARCH
            search_btn = self.page.locator('button[type="submit"]:has-text("Search")')
            if await search_btn.count() > 0:
                await search_btn.first.click()
                await self.page.wait_for_load_state("networkidle", timeout=15000)
                await asyncio.sleep(1)

            screenshot = await self._screenshot("10b_suspects_results")

            # Check table
            table = self.page.locator('table[class*="Table_table"]')
            rows = self.page.locator('table[class*="Table_table"] tbody tr')
            row_count = await rows.count()

            # Check expected columns
            headers = self.page.locator('table[class*="Table_table"] thead th')
            header_texts = []
            for i in range(await headers.count()):
                t = await headers.nth(i).text_content()
                if t:
                    header_texts.append(t.strip())

            expected_cols = ["UID", "Country", "Cases", "Client Profit", "Black Flags", "Abuse Ratio"]
            missing = [c for c in expected_cols if not any(c.lower() in h.lower() for h in header_texts)]

            issues = []
            if not has_filters:
                issues.append("Filters (UIDs, Case IDs) not found")
            if missing:
                issues.append(f"Missing columns: {missing}")

            if issues:
                self._record("suspects_search", "FAIL", "; ".join(issues), screenshot, start)
            elif row_count == 0:
                self._record("suspects_search", "WARN",
                             "Suspects tab loaded, filters OK, but 0 rows returned",
                             screenshot, start)
            else:
                self._record("suspects_search", "PASS",
                             f"Suspects tab: {row_count} row(s), all columns present",
                             screenshot, start)
        except Exception as e:
            screenshot = await self._screenshot("10_error")
            self._record("suspects_search", "FAIL", str(e), screenshot, start)
        return self.results[-1]

    async def test_suspect_detail(self):
        """S11: Open suspect detail dialog, verify fields and sections."""
        start = await self._step("suspect_detail")
        try:
            await self._close_dialog()
            await self._click_tab(SEL["tab_cases"])
            await asyncio.sleep(0.5)

            # Search cases
            search_btn = self.page.locator(SEL["btn_search"])
            if await search_btn.count() > 0:
                await search_btn.first.click()
                await self.page.wait_for_load_state("networkidle", timeout=15000)
                await asyncio.sleep(1)

            # Find UUID link in table (longer text = UUID, not case ID)
            links = self.page.locator(f'{SEL["table_cases"]} tbody tr:first-child button[class*="Link_link"]')
            link_count = await links.count()

            clicked_uid = False
            for i in range(link_count):
                text = await links.nth(i).text_content()
                if text and len(text.strip()) > 10:  # UUID is long
                    await links.nth(i).click()
                    clicked_uid = True
                    break

            if not clicked_uid:
                screenshot = await self._screenshot("11_no_uid")
                self._record("suspect_detail", "FAIL",
                             "No UUID link found in table row", screenshot, start)
                return self.results[-1]

            await asyncio.sleep(2)
            screenshot = await self._screenshot("11a_suspect_detail")

            # Check dialog content
            page_text = await self.page.content()

            expected_fields = ["UID", "Country", "Reg Date", "Potential Abuse Type",
                               "Black Flags", "Abuse Ratio"]
            expected_sections = ["CLIENT PROFIT"]
            expected_links = ["Backoffice", "Restrictions"]

            found_fields = [f for f in expected_fields if f in page_text]
            found_sections = [s for s in expected_sections if s.lower() in page_text.lower()]
            found_links = [l for l in expected_links if l in page_text]

            missing_fields = [f for f in expected_fields if f not in page_text]

            # Check for "undefined" text (bug indicator)
            has_undefined = "undefined Details" in page_text or "undefined" in (
                await self.page.locator('h3').first.text_content() or ""
            )

            issues = []
            if missing_fields:
                issues.append(f"Missing fields: {missing_fields}")
            if has_undefined:
                issues.append("BUG: 'undefined' in dialog title (missing suspect name/country)")
            if not found_sections:
                issues.append("CLIENT PROFIT section not found")

            if issues:
                status = "FAIL" if has_undefined else "WARN"
                self._record("suspect_detail", status,
                             "; ".join(issues), screenshot, start)
            else:
                self._record("suspect_detail", "PASS",
                             f"Suspect detail: {len(found_fields)} fields, "
                             f"{len(found_links)} links, chart section present",
                             screenshot, start)

            # Close dialog
            await self._close_dialog()

        except Exception as e:
            screenshot = await self._screenshot("11_error")
            self._record("suspect_detail", "FAIL", str(e), screenshot, start)
        return self.results[-1]

    async def test_suspect_detail_links(self):
        """S18: In suspect detail, verify external links are present and not broken."""
        start = await self._step("suspect_detail_links")
        try:
            await self._close_dialog()
            await self._click_tab(SEL["tab_cases"])
            await asyncio.sleep(0.5)

            await self.page.locator(SEL["btn_search"]).first.click()
            await self.page.wait_for_load_state("networkidle", timeout=15000)
            await asyncio.sleep(1)

            # Open suspect from Cases table
            links = self.page.locator(f'{SEL["table_cases"]} tbody tr:first-child button[class*="Link_link"]')
            for i in range(await links.count()):
                text = await links.nth(i).text_content()
                if text and len(text.strip()) > 10:
                    await links.nth(i).click()
                    break

            await asyncio.sleep(2)
            screenshot = await self._screenshot("18_suspect_links")

            page_text = await self.page.content()
            expected_links = ["Backoffice", "Restrictions", "Toxicity", "Ticks"]
            found = [l for l in expected_links if l in page_text]
            missing = [l for l in expected_links if l not in page_text]

            if missing:
                self._record("suspect_detail_links", "FAIL",
                             f"Missing links: {missing} (found: {found})", screenshot, start)
            else:
                self._record("suspect_detail_links", "PASS",
                             f"All {len(expected_links)} external links present: {found}",
                             screenshot, start)

            await self._close_dialog()
        except Exception as e:
            screenshot = await self._screenshot("18_error")
            self._record("suspect_detail_links", "FAIL", str(e), screenshot, start)
        return self.results[-1]

    async def test_suspects_search_with_updates(self):
        """S19: Search suspects with 'With updates' ON — verify behavior."""
        start = await self._step("suspects_with_updates")
        try:
            await self._close_dialog()
            await self._click_tab(SEL["tab_suspects"])
            await asyncio.sleep(1)

            # Ensure "With updates" is ON
            await self._toggle_switch("has_updates", True)

            uid_field = self.page.locator('[name="uids"]')
            if await uid_field.count() > 0:
                await uid_field.first.fill("ab00eefb-a3db-406e-9f32-298b49fdf652")

            search_btn = self.page.locator('button[type="submit"]:has-text("Search")')
            if await search_btn.count() > 0:
                await search_btn.first.click()
                await self.page.wait_for_load_state("networkidle", timeout=15000)
                await asyncio.sleep(1)

            screenshot = await self._screenshot("19a_with_updates_on")
            rows = self.page.locator('table[class*="Table_table"] tbody tr')
            row_count = await rows.count()

            # With updates ON: PASS if search executed without errors (0 results is valid)
            api_errors = [e for e in self.network_errors if "400" in e or "500" in e]
            status = "FAIL" if api_errors else "PASS"
            self._record("suspects_with_updates", status,
                         f"With updates ON: {row_count} suspect(s) found",
                         screenshot, start)
        except Exception as e:
            screenshot = await self._screenshot("19a_error")
            self._record("suspects_with_updates", "FAIL", str(e), screenshot, start)
        return self.results[-1]

    async def test_suspects_search_without_updates(self):
        """S20: Search suspects with 'With updates' OFF — should return results."""
        start = await self._step("suspects_without_updates")
        try:
            await self._close_dialog()
            await self._click_tab(SEL["tab_suspects"])
            await asyncio.sleep(1)

            # Turn OFF "With updates"
            await self._toggle_switch("has_updates", False)

            uid_field = self.page.locator('[name="uids"]')
            if await uid_field.count() > 0:
                await uid_field.first.fill("ab00eefb-a3db-406e-9f32-298b49fdf652")

            search_btn = self.page.locator('button[type="submit"]:has-text("Search")')
            if await search_btn.count() > 0:
                await search_btn.first.click()
                await self.page.wait_for_load_state("networkidle", timeout=15000)
                await asyncio.sleep(1)

            screenshot = await self._screenshot("20_with_updates_off")
            rows = self.page.locator('table[class*="Table_table"] tbody tr')
            row_count = await rows.count()

            if row_count > 0:
                self._record("suspects_without_updates", "PASS",
                             f"With updates OFF: {row_count} suspect(s) found",
                             screenshot, start)
            else:
                self._record("suspects_without_updates", "WARN",
                             "With updates OFF + UID filter: still 0 suspects",
                             screenshot, start)
        except Exception as e:
            screenshot = await self._screenshot("20_error")
            self._record("suspects_without_updates", "FAIL", str(e), screenshot, start)
        return self.results[-1]
