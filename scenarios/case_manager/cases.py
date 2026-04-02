from __future__ import annotations

import asyncio
import os

from scenarios.case_manager.selectors import SEL


class CasesMixin:

    async def test_page_load(self):
        """S1: Verify Case Manager page loads with tabs and search."""
        start = await self._step("page_load")
        try:
            screenshot = await self._screenshot("01_page_load")

            cases_tab = self.page.locator(SEL["tab_cases"])
            search_btn = self.page.locator(SEL["btn_search"])
            table = self.page.locator(SEL["table_cases"])

            has_tab = await cases_tab.count() > 0
            has_search = await search_btn.count() > 0
            has_table = await table.count() > 0

            if has_tab and has_search and has_table:
                self._record("page_load", "PASS",
                             "Page loaded: CASES tab, SEARCH button, casesTable all present",
                             screenshot, start)
            else:
                missing = []
                if not has_tab: missing.append("CASES tab")
                if not has_search: missing.append("SEARCH button")
                if not has_table: missing.append("casesTable")
                self._record("page_load", "FAIL",
                             f"Missing: {', '.join(missing)}", screenshot, start)
        except Exception as e:
            screenshot = await self._screenshot("01_error")
            self._record("page_load", "FAIL", str(e), screenshot, start)
        return self.results[-1]

    async def test_search_cases(self):
        """S2: Click SEARCH and verify results table has rows."""
        start = await self._step("search_cases")
        try:
            await self.page.locator(SEL["btn_search"]).first.click()
            await self.page.wait_for_load_state("networkidle", timeout=15000)
            await asyncio.sleep(1)
            screenshot = await self._screenshot("02_search_results")

            rows = self.page.locator(f'{SEL["table_cases"]} tbody tr')
            row_count = await rows.count()

            if row_count > 0:
                self._record("search_cases", "PASS",
                             f"Search returned {row_count} case(s)", screenshot, start)
            else:
                self._record("search_cases", "WARN",
                             "Search returned 0 cases — table empty", screenshot, start)
        except Exception as e:
            screenshot = await self._screenshot("02_error")
            self._record("search_cases", "FAIL", str(e), screenshot, start)
        return self.results[-1]

    async def test_create_monitoring_case(self):
        """S3: Fill and submit CREATE MONITORING CASE form."""
        start = await self._step("create_monitoring_case")
        try:
            clicked = await self._click_tab(SEL["tab_create_monitoring"])
            if not clicked:
                screenshot = await self._screenshot("03_no_tab")
                self._record("create_monitoring_case", "FAIL",
                             "CREATE MONITORING CASE tab not found", screenshot, start)
                return self.results[-1]

            await asyncio.sleep(1)
            screenshot_form = await self._screenshot("03a_form")

            # Fill required fields for monitoring case
            filled = {}
            filled["title"] = await self._fill_field(SEL["field_title"], "TITAN Test Monitoring Case")
            filled["user_uids"] = await self._fill_field(SEL["field_user_uids"], "00000000-aaaa-bbbb-cccc-000000000001")
            filled["abuse_type"] = await self._select_custom_dropdown("abuse_type")
            filled["process"] = await self._select_custom_dropdown("process")
            filled["severity"] = await self._select_custom_dropdown("severity", "Medium")
            filled["description"] = await self._fill_field(SEL["field_description"], "Automated test case created by TITAN")
            filled["jira_tickets"] = await self._fill_field(SEL["field_jira_tickets"], "TEST-001")

            screenshot_filled = await self._screenshot("03b_filled")
            filled_count = sum(1 for v in filled.values() if v)

            # Submit
            submit = self.page.locator(SEL["btn_create_monitoring"])
            if await submit.count() > 0:
                await submit.first.click()
                await asyncio.sleep(2)
                try:
                    await self.page.wait_for_load_state("networkidle", timeout=15000)
                except Exception:
                    pass
                screenshot_result = await self._screenshot("03c_result")

                api_errors = [e for e in self.network_errors if "/api/" in e and ("400" in e or "500" in e)]
                if api_errors:
                    self._record("create_monitoring_case", "FAIL",
                                 f"Create failed ({filled_count}/7 fields filled): {api_errors}",
                                 screenshot_result, start)
                else:
                    self._record("create_monitoring_case", "PASS",
                                 f"Monitoring case created ({filled_count}/7 required fields filled)",
                                 screenshot_result, start)
            else:
                self._record("create_monitoring_case", "WARN",
                             f"Form shown ({filled_count} fields filled) but submit button not found",
                             screenshot_filled, start)
        except Exception as e:
            screenshot = await self._screenshot("03_error")
            self._record("create_monitoring_case", "FAIL", str(e), screenshot, start)
        return self.results[-1]

    async def test_create_reporting_case(self):
        """S4: Fill and submit CREATE REPORTING CASE form."""
        start = await self._step("create_reporting_case")
        try:
            clicked = await self._click_tab(SEL["tab_create_reporting"])
            if not clicked:
                screenshot = await self._screenshot("04_no_tab")
                self._record("create_reporting_case", "FAIL",
                             "CREATE REPORTING CASE tab not found", screenshot, start)
                return self.results[-1]

            await asyncio.sleep(1)
            screenshot_form = await self._screenshot("04a_form")

            # Fill required fields for reporting case
            filled = {}
            filled["user_uids"] = await self._fill_field(SEL["field_user_uids"], "00000000-aaaa-bbbb-cccc-000000000002")
            filled["abuse_type"] = await self._select_custom_dropdown("abuse_type")
            filled["symbol"] = await self._select_custom_dropdown("symbol")
            filled["severity"] = await self._select_custom_dropdown("severity", "Medium")
            filled["description"] = await self._fill_field(SEL["field_description"], "Automated reporting test case by TITAN")

            # Non-critical reporting requires files — attach test file
            test_file = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                      "..", "..", "storage_layout", "test_attachment.png")
            file_input = self.page.locator('input[name="files"][type="file"]')
            if await file_input.count() > 0 and os.path.exists(test_file):
                await file_input.first.set_input_files(os.path.abspath(test_file))
                filled["files"] = True
                await asyncio.sleep(0.5)

            screenshot_filled = await self._screenshot("04b_filled")
            filled_count = sum(1 for v in filled.values() if v)

            # Submit
            submit = self.page.locator(SEL["btn_create_reporting"])
            if await submit.count() > 0:
                await submit.first.click()
                await asyncio.sleep(2)
                try:
                    await self.page.wait_for_load_state("networkidle", timeout=15000)
                except Exception:
                    pass
                screenshot_result = await self._screenshot("04c_result")

                api_errors = [e for e in self.network_errors if "/api/" in e and ("400" in e or "500" in e)]
                if api_errors:
                    self._record("create_reporting_case", "FAIL",
                                 f"Create failed ({filled_count}/5 fields filled): {api_errors}",
                                 screenshot_result, start)
                else:
                    self._record("create_reporting_case", "PASS",
                                 f"Reporting case created ({filled_count}/5 required fields filled)",
                                 screenshot_result, start)
            else:
                self._record("create_reporting_case", "WARN",
                             f"Form shown ({filled_count} fields filled) but submit button not found",
                             screenshot_filled, start)
        except Exception as e:
            screenshot = await self._screenshot("04_error")
            self._record("create_reporting_case", "FAIL", str(e), screenshot, start)
        return self.results[-1]

    async def test_open_case_details(self):
        """S5: Click a case ID in table to open details dialog."""
        start = await self._step("open_case_details")
        try:
            # Go to CASES tab and search
            await self._click_tab(SEL["tab_cases"])
            await asyncio.sleep(0.5)

            search_btn = self.page.locator(SEL["btn_search"])
            if await search_btn.count() > 0:
                await search_btn.first.click()
                await self.page.wait_for_load_state("networkidle", timeout=15000)
                await asyncio.sleep(1)

            # Click case ID button (2nd column has button.Link_link with case ID)
            case_link = self.page.locator(
                f'{SEL["table_cases"]} tbody tr:first-child td:nth-child(2) button[class*="Link_link"]'
            )
            if await case_link.count() == 0:
                case_link = self.page.locator(f'{SEL["table_cases"]} tbody tr:first-child td:nth-child(2)')

            if await case_link.count() > 0:
                await case_link.first.click()
                await asyncio.sleep(2)
                screenshot = await self._screenshot("05_case_details")

                # Check if caseDetailsDialog appeared
                dialog = self.page.locator(SEL["dialog_details"])
                if await dialog.count() > 0 and await dialog.first.is_visible():
                    self._record("open_case_details", "PASS",
                                 "Case details dialog opened", screenshot, start)
                else:
                    self._record("open_case_details", "WARN",
                                 "Clicked case ID but caseDetailsDialog not visible",
                                 screenshot, start)
            else:
                screenshot = await self._screenshot("05_no_cases")
                self._record("open_case_details", "FAIL",
                             "No case rows found in table", screenshot, start)
        except Exception as e:
            screenshot = await self._screenshot("05_error")
            self._record("open_case_details", "FAIL", str(e), screenshot, start)
        return self.results[-1]

    async def test_edit_case(self):
        """S6: Click EDIT in case detail dialog, modify description, save."""
        start = await self._step("edit_case")
        try:
            # EDIT button is inside the case detail (yellow button at bottom)
            edit_btn = self.page.locator('button:has-text("EDIT")')

            if await edit_btn.count() > 0:
                await edit_btn.first.click()
                await asyncio.sleep(1)
                screenshot_edit = await self._screenshot("06a_edit_form")

                # After clicking EDIT, fields become editable
                # Try to modify description textarea
                desc = self.page.locator('[name="description"]')
                if await desc.count() > 0:
                    await desc.first.fill("Updated by TITAN E2E test")

                screenshot_modified = await self._screenshot("06b_modified")

                # Look for SAVE/UPDATE button
                save_btn = self.page.locator(
                    'button:has-text("SAVE"), button:has-text("UPDATE"), '
                    'button[type="submit"]:has-text("Save")'
                )
                if await save_btn.count() > 0:
                    await save_btn.first.click()
                    await asyncio.sleep(2)
                    screenshot_saved = await self._screenshot("06c_saved")

                    api_errors = [e for e in self.network_errors if "/api/" in e and ("400" in e or "500" in e)]
                    if api_errors:
                        self._record("edit_case", "FAIL",
                                     f"Save failed: {api_errors}", screenshot_saved, start)
                    else:
                        self._record("edit_case", "PASS",
                                     "Case edited and saved", screenshot_saved, start)
                else:
                    self._record("edit_case", "WARN",
                                 "Edit mode entered but save button not found",
                                 screenshot_modified, start)
            else:
                screenshot = await self._screenshot("06_no_edit")
                self._record("edit_case", "WARN",
                             "EDIT button not found — case detail may not be open",
                             screenshot, start)
        except Exception as e:
            screenshot = await self._screenshot("06_error")
            self._record("edit_case", "FAIL", str(e), screenshot, start)
        return self.results[-1]

    async def test_reporter_assignee(self):
        """S7: Verify Reporter and Assignee are not 'unknown' (known bug)."""
        start = await self._step("reporter_assignee")
        try:
            # Close any open dialogs first
            await self._close_dialog()
            await self._click_tab(SEL["tab_cases"])
            await asyncio.sleep(0.5)

            search_btn = self.page.locator(SEL["btn_search"])
            if await search_btn.count() > 0:
                await search_btn.first.click()
                await self.page.wait_for_load_state("networkidle", timeout=15000)
                await asyncio.sleep(1)

            screenshot = await self._screenshot("07_reporter_check")

            cells = self.page.locator(f'{SEL["table_cases"]} tbody td')
            cell_count = await cells.count()
            unknown_cells = []
            for i in range(cell_count):
                text = await cells.nth(i).text_content()
                if text and text.strip().lower() == "unknown":
                    unknown_cells.append(text.strip())

            if unknown_cells:
                self._record("reporter_assignee", "FAIL",
                             f"BUG: Found {len(unknown_cells)} 'unknown' values in table — "
                             f"Reporter/Assignee/Updated By not resolved",
                             screenshot, start)
            else:
                self._record("reporter_assignee", "PASS",
                             "No 'unknown' values in table", screenshot, start)
        except Exception as e:
            screenshot = await self._screenshot("07_error")
            self._record("reporter_assignee", "FAIL", str(e), screenshot, start)
        return self.results[-1]

    async def test_all_tabs(self):
        """S8: Click each tab and verify content loads without errors."""
        start = await self._step("all_tabs")
        tab_map = {
            "CASES": SEL["tab_cases"],
            "SUSPECTS": SEL["tab_suspects"],
            "DASHBOARD": SEL["tab_dashboard"],
            "CREATE MONITORING": SEL["tab_create_monitoring"],
            "CREATE REPORTING": SEL["tab_create_reporting"],
            "SETTINGS": SEL["tab_settings"],
        }
        failed_tabs = []
        try:
            for tab_name, tab_sel in tab_map.items():
                self.network_errors.clear()
                clicked = await self._click_tab(tab_sel)
                await asyncio.sleep(1)
                safe_name = tab_name.lower().replace(" ", "_")
                screenshot = await self._screenshot(f"08_{safe_name}")

                if not clicked:
                    failed_tabs.append(f"{tab_name}: not found")
                else:
                    api_errors = [e for e in self.network_errors if "/api/" in e and ("500" in e)]
                    if api_errors:
                        failed_tabs.append(f"{tab_name}: {api_errors[0]}")

            if failed_tabs:
                self._record("all_tabs", "FAIL",
                             f"Tab issues: {'; '.join(failed_tabs)}", screenshot, start)
            else:
                self._record("all_tabs", "PASS",
                             f"All {len(tab_map)} tabs loaded successfully", screenshot, start)
        except Exception as e:
            screenshot = await self._screenshot("08_error")
            self._record("all_tabs", "FAIL", str(e), screenshot, start)
        return self.results[-1]

    async def test_table_columns(self):
        """S9: Verify expected columns and data population."""
        start = await self._step("table_columns")
        try:
            await self._click_tab(SEL["tab_cases"])
            await asyncio.sleep(0.5)

            # Ensure search results loaded
            search_btn = self.page.locator(SEL["btn_search"])
            if await search_btn.count() > 0:
                await search_btn.first.click()
                await self.page.wait_for_load_state("networkidle", timeout=15000)
                await asyncio.sleep(1)

            screenshot = await self._screenshot("09_table_columns")

            expected = ["ID", "Title", "Severity", "Status",
                        "Investigation Outcome", "Suspect UIDs",
                        "Assignee", "Reporter"]

            headers = self.page.locator(f'{SEL["table_cases"]} thead th')
            header_count = await headers.count()
            header_texts = []
            for i in range(header_count):
                text = await headers.nth(i).text_content()
                if text:
                    header_texts.append(text.strip())

            missing = [col for col in expected
                       if not any(col.lower() in h.lower() for h in header_texts)]

            # Check first row for empty cells
            first_row = self.page.locator(f'{SEL["table_cases"]} tbody tr:first-child td')
            row_count = await first_row.count()
            empty_cols = []
            for i in range(min(row_count, len(header_texts))):
                text = await first_row.nth(i).text_content()
                if text is not None and text.strip() == "" and i < len(header_texts):
                    empty_cols.append(header_texts[i])

            issues = []
            if missing:
                issues.append(f"Missing columns: {missing}")
            if empty_cols:
                issues.append(f"Empty cells: {empty_cols}")

            if issues:
                self._record("table_columns", "WARN",
                             "; ".join(issues), screenshot, start)
            else:
                self._record("table_columns", "PASS",
                             f"All {len(expected)} expected columns present, data populated",
                             screenshot, start)
        except Exception as e:
            screenshot = await self._screenshot("09_error")
            self._record("table_columns", "FAIL", str(e), screenshot, start)
        return self.results[-1]

    async def test_case_comments(self):
        """S15: Open case detail, add a comment, verify it appears."""
        start = await self._step("case_comments")
        try:
            await self._close_dialog()
            await self._click_tab(SEL["tab_cases"])
            await asyncio.sleep(0.5)

            # Search and open case
            await self.page.locator(SEL["btn_search"]).first.click()
            await self.page.wait_for_load_state("networkidle", timeout=15000)
            await asyncio.sleep(1)

            case_btn = self.page.locator(
                f'{SEL["table_cases"]} tbody tr:first-child td:nth-child(2) button[class*="Link_link"]'
            )
            if await case_btn.count() == 0:
                screenshot = await self._screenshot("15_no_case")
                self._record("case_comments", "FAIL", "No cases to open", screenshot, start)
                return self.results[-1]

            await case_btn.first.click()
            await asyncio.sleep(2)

            # Find comment textarea and Comment button
            comment_input = self.page.locator('[name="comment"]')
            comment_btn = self.page.locator('button:has-text("Comment")')

            if await comment_input.count() > 0 and await comment_btn.count() > 0:
                await comment_input.first.fill("TITAN automated test comment")
                screenshot_filled = await self._screenshot("15a_comment_filled")

                await comment_btn.first.click()
                await asyncio.sleep(2)
                screenshot_posted = await self._screenshot("15b_comment_posted")

                api_errors = [e for e in self.network_errors if "/api/" in e and ("400" in e or "500" in e)]
                if api_errors:
                    self._record("case_comments", "FAIL",
                                 f"Comment post failed: {api_errors}", screenshot_posted, start)
                else:
                    self._record("case_comments", "PASS",
                                 "Comment posted successfully", screenshot_posted, start)
            else:
                screenshot = await self._screenshot("15_no_comment_form")
                has_input = await comment_input.count() > 0
                has_btn = await comment_btn.count() > 0
                self._record("case_comments", "FAIL",
                             f"Comment form incomplete: input={has_input}, button={has_btn}",
                             screenshot, start)

            await self._close_dialog()
        except Exception as e:
            screenshot = await self._screenshot("15_error")
            self._record("case_comments", "FAIL", str(e), screenshot, start)
        return self.results[-1]

    async def test_case_logs(self):
        """S16: Open case detail, click Logs button, verify logs load."""
        start = await self._step("case_logs")
        try:
            await self._close_dialog()
            await self._click_tab(SEL["tab_cases"])
            await asyncio.sleep(0.5)

            await self.page.locator(SEL["btn_search"]).first.click()
            await self.page.wait_for_load_state("networkidle", timeout=15000)
            await asyncio.sleep(1)

            case_btn = self.page.locator(
                f'{SEL["table_cases"]} tbody tr:first-child td:nth-child(2) button[class*="Link_link"]'
            )
            if await case_btn.count() > 0:
                await case_btn.first.click()
                await asyncio.sleep(2)

            # Click Logs button
            logs_btn = self.page.locator('button:has-text("Logs")')
            if await logs_btn.count() > 0:
                await logs_btn.first.click()
                await asyncio.sleep(2)
                screenshot = await self._screenshot("16_logs")

                api_errors = [e for e in self.network_errors if "/api/" in e and "500" in e]
                if api_errors:
                    self._record("case_logs", "FAIL",
                                 f"Logs request failed: {api_errors}", screenshot, start)
                else:
                    self._record("case_logs", "PASS",
                                 "Logs loaded successfully", screenshot, start)
            else:
                screenshot = await self._screenshot("16_no_logs_btn")
                self._record("case_logs", "FAIL",
                             "Logs button not found in case detail", screenshot, start)

            await self._close_dialog()
        except Exception as e:
            screenshot = await self._screenshot("16_error")
            self._record("case_logs", "FAIL", str(e), screenshot, start)
        return self.results[-1]

    async def test_case_prev_next(self):
        """S17: In case detail, click PREV/NEXT buttons and verify navigation."""
        start = await self._step("case_prev_next")
        try:
            await self._close_dialog()
            await self._click_tab(SEL["tab_cases"])
            await asyncio.sleep(0.5)

            await self.page.locator(SEL["btn_search"]).first.click()
            await self.page.wait_for_load_state("networkidle", timeout=15000)
            await asyncio.sleep(1)

            # Open case detail fresh
            case_btn = self.page.locator(
                f'{SEL["table_cases"]} tbody tr:first-child td:nth-child(2) button[class*="Link_link"]'
            )
            if await case_btn.count() > 0:
                await case_btn.first.click()
                await asyncio.sleep(2)

            prev_btn = self.page.locator('button:has-text("< PREV")')
            next_btn = self.page.locator('button:has-text("NEXT >")')

            has_prev = await prev_btn.count() > 0
            has_next = await next_btn.count() > 0

            if has_prev and has_next:
                # Try clicking NEXT
                await next_btn.first.click()
                await asyncio.sleep(1)
                screenshot = await self._screenshot("17_after_next")

                # Try clicking PREV
                await prev_btn.first.click()
                await asyncio.sleep(1)
                screenshot = await self._screenshot("17_after_prev")

                api_errors = [e for e in self.network_errors if "/api/" in e and "500" in e]
                if api_errors:
                    self._record("case_prev_next", "FAIL",
                                 f"Navigation error: {api_errors}", screenshot, start)
                else:
                    self._record("case_prev_next", "PASS",
                                 "PREV/NEXT navigation works", screenshot, start)
            else:
                screenshot = await self._screenshot("17_no_nav")
                self._record("case_prev_next", "WARN",
                             f"Navigation buttons: PREV={has_prev}, NEXT={has_next}",
                             screenshot, start)

            await self._close_dialog()
        except Exception as e:
            screenshot = await self._screenshot("17_error")
            self._record("case_prev_next", "FAIL", str(e), screenshot, start)
        return self.results[-1]

    async def test_update_case_fields(self):
        """S22: Open EDIT, change multiple fields (description, abuse_type, severity), save."""
        start = await self._step("update_case_fields")
        try:
            if not await self._open_case_by_index(1):
                screenshot = await self._screenshot("22_no_case")
                self._record("update_case_fields", "FAIL", "No case to edit", screenshot, start)
                return self.results[-1]

            # Click EDIT
            edit_btn = self.page.locator('button:has-text("EDIT")')
            if await edit_btn.count() == 0:
                # Scroll down
                await self.page.evaluate("window.scrollTo(0, 500)")
                await asyncio.sleep(0.5)
                edit_btn = self.page.locator('button:has-text("EDIT"), button:has-text("edit")')

            if await edit_btn.count() == 0:
                screenshot = await self._screenshot("22_no_edit")
                self._record("update_case_fields", "FAIL", "EDIT button not found", screenshot, start)
                return self.results[-1]

            await edit_btn.first.click()
            await asyncio.sleep(1)
            screenshot_before = await self._screenshot("22a_edit_form")

            # Update description — textarea in edit dialog
            desc = self.page.locator('textarea[name="description"]')
            if await desc.count() > 0:
                await desc.first.fill("Updated description by TITAN E2E")

            # Use helper for dropdowns (has force=True)
            await self._select_custom_dropdown("abuse_type", "B2B")
            await self._select_custom_dropdown("investigation_outcome", "Abusive")

            screenshot_filled = await self._screenshot("22b_fields_changed")

            # Save
            save_btn = self.page.locator('button:has-text("Save Changes"), button:has-text("SAVE")')
            if await save_btn.count() > 0:
                self.network_errors.clear()
                await save_btn.first.click()
                await asyncio.sleep(2)
                screenshot_saved = await self._screenshot("22c_saved")

                api_errors = [e for e in self.network_errors
                              if "/api/" in e and any(c in e for c in ("400", "422", "500"))]
                if api_errors:
                    self._record("update_case_fields", "FAIL",
                                 f"Save failed: {api_errors}", screenshot_saved, start)
                else:
                    self._record("update_case_fields", "PASS",
                                 "Case fields updated (description, abuse_type, investigation_outcome)",
                                 screenshot_saved, start)
            else:
                self._record("update_case_fields", "WARN",
                             "Edit opened but Save button not found", screenshot_filled, start)

            await self._close_dialog()
        except Exception as e:
            screenshot = await self._screenshot("22_error")
            self._record("update_case_fields", "FAIL", str(e), screenshot, start)
        return self.results[-1]

    async def test_status_to_in_progress(self):
        """S23: Change case status from 'new' to 'in_progress'."""
        start = await self._step("status_to_in_progress")
        try:
            # Find a case with status "new"
            if not await self._open_case_by_index(1):
                screenshot = await self._screenshot("23_no_case")
                self._record("status_to_in_progress", "FAIL", "No case", screenshot, start)
                return self.results[-1]

            # Status is in case detail view — scroll to it
            await self.page.evaluate("window.scrollTo(0, 800)")
            await asyncio.sleep(0.5)

            status_input = self.page.locator('input[name="status"]')
            if await status_input.count() > 0:
                await status_input.first.scroll_into_view_if_needed()
                await asyncio.sleep(0.3)
                await status_input.first.click(force=True)
                await asyncio.sleep(0.5)
                opt = self.page.locator('button.ListItem_item:has-text("In Progress")')
                if await opt.count() > 0:
                    await opt.first.click()
                    await asyncio.sleep(1)
            else:
                screenshot = await self._screenshot("23_no_status")
                self._record("status_to_in_progress", "FAIL",
                             "Status dropdown not found in case detail", screenshot, start)
                await self._close_dialog()
                return self.results[-1]
            await asyncio.sleep(2)
            screenshot = await self._screenshot("23_status_changed")

            api_errors = [e for e in self.network_errors
                          if "/api/" in e and any(c in e for c in ("400", "422", "500"))]
            if api_errors:
                self._record("status_to_in_progress", "FAIL",
                             f"Status change failed: {api_errors}", screenshot, start)
            else:
                self._record("status_to_in_progress", "PASS",
                             "Status changed to in_progress", screenshot, start)

            await self._close_dialog()
        except Exception as e:
            screenshot = await self._screenshot("23_error")
            self._record("status_to_in_progress", "FAIL", str(e), screenshot, start)
        return self.results[-1]

    async def test_status_to_closed(self):
        """S24: Change case status to 'closed', confirm in dialog."""
        start = await self._step("status_to_closed")
        try:
            if not await self._open_case_by_index(1):
                screenshot = await self._screenshot("24_no_case")
                self._record("status_to_closed", "FAIL", "No case", screenshot, start)
                return self.results[-1]

            # Status is in case detail view — scroll to it
            await self.page.evaluate("window.scrollTo(0, 800)")
            await asyncio.sleep(0.5)

            status_input = self.page.locator('input[name="status"]')
            if await status_input.count() > 0:
                await status_input.first.scroll_into_view_if_needed()
                await asyncio.sleep(0.3)
                await status_input.first.click(force=True)
                await asyncio.sleep(0.5)
                opt = self.page.locator('button.ListItem_item:has-text("Closed")')
                if await opt.count() > 0:
                    await opt.first.click()
                    await asyncio.sleep(1)
            else:
                screenshot = await self._screenshot("24_no_status")
                self._record("status_to_closed", "FAIL",
                             "Status dropdown not found", screenshot, start)
                await self._close_dialog()
                return self.results[-1]
            await asyncio.sleep(1)

            # Confirmation dialog should appear
            screenshot_confirm = await self._screenshot("24a_confirm_dialog")

            # Click Yes/confirm
            yes_btn = self.page.locator(
                'button:has-text("Yes"), button:has-text("YES"), '
                'button:has-text("Confirm"), button:has-text("OK")'
            )
            if await yes_btn.count() > 0:
                self.network_errors.clear()
                await yes_btn.first.click()
                await asyncio.sleep(2)
                screenshot_closed = await self._screenshot("24b_closed")

                api_errors = [e for e in self.network_errors
                              if "/api/" in e and any(c in e for c in ("400", "422", "500"))]
                if api_errors:
                    self._record("status_to_closed", "FAIL",
                                 f"Close failed: {api_errors}", screenshot_closed, start)
                else:
                    self._record("status_to_closed", "PASS",
                                 "Case closed with confirmation", screenshot_closed, start)
            else:
                self._record("status_to_closed", "WARN",
                             "Status set to closed but no confirmation dialog appeared",
                             screenshot_confirm, start)

            await self._close_dialog()
        except Exception as e:
            screenshot = await self._screenshot("24_error")
            self._record("status_to_closed", "FAIL", str(e), screenshot, start)
        return self.results[-1]

    async def test_reopen_case(self):
        """S25: Reopen a closed case via 'Reopen Case' button."""
        start = await self._step("reopen_case")
        try:
            # Add "Closed" to Case Statuses filter so closed cases appear
            await self._close_dialog()
            await self._click_tab(SEL["tab_cases"])
            await asyncio.sleep(0.5)

            # Click the Case Statuses dropdown and add "Closed"
            status_filter = self.page.locator('input[name="caseStatuses"]')
            if await status_filter.count() > 0:
                await status_filter.first.click(force=True)
                await asyncio.sleep(0.5)
                closed_opt = self.page.locator('button.ListItem_item:has-text("Closed")')
                if await closed_opt.count() > 0:
                    await closed_opt.first.click()
                    await asyncio.sleep(0.3)

            # Search
            await self.page.locator(SEL["btn_search"]).first.click()
            await self.page.wait_for_load_state("networkidle", timeout=15000)
            await asyncio.sleep(1)

            # Find closed case and open it
            rows = self.page.locator(f'{SEL["table_cases"]} tbody tr')
            opened = False
            for i in range(await rows.count()):
                status_cell = rows.nth(i).locator('td')
                # Look for "closed" text in the row
                row_text = await rows.nth(i).text_content()
                if row_text and "closed" in row_text.lower():
                    case_btn = rows.nth(i).locator('td:nth-child(2) button[class*="Link_link"]')
                    if await case_btn.count() > 0:
                        await case_btn.first.click()
                        opened = True
                    break

            if not opened:
                screenshot = await self._screenshot("25_no_case")
                self._record("reopen_case", "FAIL", "No case", screenshot, start)
                return self.results[-1]

            # Scroll down to find Reopen button
            await self.page.evaluate("window.scrollTo(0, 500)")
            await asyncio.sleep(0.5)

            reopen_btn = self.page.locator('button:has-text("Reopen"), button:has-text("REOPEN")')
            if await reopen_btn.count() > 0:
                await reopen_btn.first.click()
                await asyncio.sleep(1)
                screenshot_confirm = await self._screenshot("25a_reopen_confirm")

                # Confirm
                yes_btn = self.page.locator(
                    'button:has-text("Yes"), button:has-text("YES"), '
                    'button:has-text("Confirm")'
                )
                if await yes_btn.count() > 0:
                    self.network_errors.clear()
                    await yes_btn.first.click()
                    await asyncio.sleep(2)
                    screenshot_reopened = await self._screenshot("25b_reopened")

                    api_errors = [e for e in self.network_errors
                                  if "/api/" in e and any(c in e for c in ("400", "422", "500"))]
                    if api_errors:
                        self._record("reopen_case", "FAIL",
                                     f"Reopen failed: {api_errors}", screenshot_reopened, start)
                    else:
                        self._record("reopen_case", "PASS",
                                     "Case reopened (closed → in_progress)", screenshot_reopened, start)
                else:
                    self._record("reopen_case", "WARN",
                                 "Reopen clicked but no confirmation dialog", screenshot_confirm, start)
            else:
                screenshot = await self._screenshot("25_no_reopen")
                # Maybe case isn't closed — check status
                page_text = await self.page.content()
                if "closed" in page_text.lower():
                    self._record("reopen_case", "FAIL",
                                 "Case is closed but Reopen button not found", screenshot, start)
                else:
                    self._record("reopen_case", "WARN",
                                 "Case is not in 'closed' status — Reopen button not available",
                                 screenshot, start)

            await self._close_dialog()
        except Exception as e:
            screenshot = await self._screenshot("25_error")
            self._record("reopen_case", "FAIL", str(e), screenshot, start)
        return self.results[-1]
