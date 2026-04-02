from __future__ import annotations

import asyncio

from scenarios.case_manager.selectors import SEL


class SettingsMixin:

    async def test_settings_processes(self):
        """S12: Open Settings tab, verify Processes table loads."""
        start = await self._step("settings_processes")
        try:
            await self._close_dialog()
            await self._click_tab(SEL["tab_settings"])
            await asyncio.sleep(1)
            screenshot = await self._screenshot("12a_settings_tab")

            # Settings has sub-tab "Processes" (auto-selected)
            table = self.page.locator('table[class*="Table_table"]')
            has_table = await table.count() > 0

            if has_table:
                rows = self.page.locator('table[class*="Table_table"] tbody tr')
                row_count = await rows.count()

                # Verify columns
                headers = self.page.locator('table[class*="Table_table"] thead th')
                header_texts = []
                for i in range(await headers.count()):
                    t = await headers.nth(i).text_content()
                    if t:
                        header_texts.append(t.strip())

                has_name = any("name" in h.lower() for h in header_texts)
                has_process = any("process" in h.lower() for h in header_texts)

                # Check for edit buttons (pencil icons)
                edit_btns = self.page.locator('table[class*="Table_table"] tbody button')
                edit_count = await edit_btns.count()

                screenshot_table = await self._screenshot("12b_processes_table")

                if row_count > 0 and has_name:
                    self._record("settings_processes", "PASS",
                                 f"Settings/Processes: {row_count} processes loaded, "
                                 f"columns: {header_texts}, {edit_count} edit buttons",
                                 screenshot_table, start)
                elif row_count == 0:
                    self._record("settings_processes", "FAIL",
                                 "Processes table is empty", screenshot_table, start)
                else:
                    self._record("settings_processes", "WARN",
                                 f"Table has {row_count} rows but missing expected columns",
                                 screenshot_table, start)
            else:
                self._record("settings_processes", "FAIL",
                             "No table found in Settings tab", screenshot, start)
        except Exception as e:
            screenshot = await self._screenshot("12_error")
            self._record("settings_processes", "FAIL", str(e), screenshot, start)
        return self.results[-1]

    async def test_settings_edit_process(self):
        """S13: Click edit on a process, verify inline edit activates."""
        start = await self._step("settings_edit_process")
        try:
            # Should already be on Settings tab from S12
            edit_btns = self.page.locator('table[class*="Table_table"] tbody button')
            if await edit_btns.count() > 0:
                await edit_btns.first.click()
                await asyncio.sleep(1)
                screenshot = await self._screenshot("13a_edit_process")

                # Inline edit: a text input appears in the table row
                inline_input = self.page.locator('table[class*="Table_table"] tbody input:visible')
                if await inline_input.count() > 0:
                    original_value = await inline_input.first.input_value()
                    self._record("settings_edit_process", "PASS",
                                 f"Inline edit activated, current value: '{original_value}'",
                                 screenshot, start)
                    # Press Escape to cancel edit without saving
                    await self.page.keyboard.press("Escape")
                    await asyncio.sleep(0.3)
                else:
                    self._record("settings_edit_process", "WARN",
                                 "Edit clicked but no inline input appeared", screenshot, start)
            else:
                screenshot = await self._screenshot("13_no_edit_btn")
                self._record("settings_edit_process", "FAIL",
                             "No edit buttons found in processes table", screenshot, start)
        except Exception as e:
            screenshot = await self._screenshot("13_error")
            self._record("settings_edit_process", "FAIL", str(e), screenshot, start)
        return self.results[-1]
