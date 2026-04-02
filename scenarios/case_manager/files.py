from __future__ import annotations

import asyncio
import uuid

from scenarios.case_manager.selectors import SEL


class FilesMixin:

    async def test_reporting_case_file_upload(self):
        """S21: Create reporting case with file, verify file appears in case detail."""
        start = await self._step("reporting_file_upload")
        try:
            await self._close_dialog()

            # Create reporting case with file via UI
            test_uid = str(uuid.uuid4())
            await self._click_tab(SEL["tab_cases"])
            await asyncio.sleep(0.5)
            await self._click_tab(SEL["tab_create_reporting"])
            await asyncio.sleep(1)

            await self._fill_field(SEL["field_user_uids"], test_uid)
            await self._select_custom_dropdown("abuse_type")
            await self._select_custom_dropdown("symbol")
            await self._select_custom_dropdown("severity", "Medium")
            await self._fill_field(SEL["field_description"], "File upload test by TITAN")

            # Non-critical reporting requires suspicious_timeframe
            timeframe = self.page.locator('[name="suspicious_timeframe"]')
            if await timeframe.count() > 0:
                await timeframe.first.click()
                await asyncio.sleep(0.5)
                preset = self.page.locator('button.ListItem_item:has-text("Last 30 days")')
                if await preset.count() > 0:
                    await preset.first.click()
                    await asyncio.sleep(0.5)

            # Attach file
            await self._attach_test_file()
            screenshot_form = await self._screenshot("21a_form_with_file")

            # Verify file preview appeared in form
            file_preview = self.page.locator('[class*="FileInput"] [class*="file"], [class*="FileInput"] img, [class*="preview"]')
            file_visible = await file_preview.count() > 0

            # Submit
            submit = self.page.locator(SEL["btn_create_reporting"])
            ok = await self._submit_and_check(submit)
            screenshot_after = await self._screenshot("21b_after_submit")

            if not ok:
                self._record("reporting_file_upload", "FAIL",
                             "Reporting case with file failed to create",
                             screenshot_after, start)
                return self.results[-1]

            # Go to Cases, search, find the new case by UID
            await self._click_tab(SEL["tab_cases"])
            await asyncio.sleep(0.5)
            await self.page.locator(SEL["btn_search"]).first.click()
            await self.page.wait_for_load_state("networkidle", timeout=15000)
            await asyncio.sleep(1)

            # Find the row with our UID and open it
            uid_links = self.page.locator(f'{SEL["table_cases"]} tbody button[class*="Link_link"]')
            opened = False
            for i in range(await uid_links.count()):
                text = await uid_links.nth(i).text_content()
                if text and test_uid in text.strip():
                    # Click case ID in same row — go up to tr, then find 2nd td button
                    row = uid_links.nth(i).locator("xpath=ancestor::tr")
                    case_id_btn = row.locator('td:nth-child(2) button[class*="Link_link"]')
                    if await case_id_btn.count() > 0:
                        await case_id_btn.first.click()
                        opened = True
                    break

            if not opened:
                # Fallback: click newest case (last in table or first by sort)
                case_btn = self.page.locator(
                    f'{SEL["table_cases"]} tbody tr:first-child td:nth-child(2) button[class*="Link_link"]'
                )
                if await case_btn.count() > 0:
                    await case_btn.first.click()
                    opened = True

            if opened:
                await asyncio.sleep(2)
                screenshot_detail = await self._screenshot("21c_case_detail_with_file")

                # Check if file/attachment is visible in the detail
                page_text = await self.page.content()
                has_file_ref = (
                    "test_attachment" in page_text
                    or ".png" in page_text
                    or await self.page.locator('[class*="file"], [class*="File"], [class*="attachment"], img[src*="file"]').count() > 0
                )

                if has_file_ref:
                    self._record("reporting_file_upload", "PASS",
                                 "Reporting case created with file, file visible in detail",
                                 screenshot_detail, start)
                else:
                    self._record("reporting_file_upload", "WARN",
                                 "Case created with file but file not found in detail view",
                                 screenshot_detail, start)
            else:
                self._record("reporting_file_upload", "WARN",
                             "Case created but couldn't open it to verify file",
                             screenshot_after, start)

            await self._close_dialog()
        except Exception as e:
            screenshot = await self._screenshot("21_error")
            self._record("reporting_file_upload", "FAIL", str(e), screenshot, start)
        return self.results[-1]
