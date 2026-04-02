from __future__ import annotations

import re

from scenarios.base import BaseScenario, StepResult
from scenarios.case_manager.cases import CasesMixin
from scenarios.case_manager.dashboard import DashboardMixin
from scenarios.case_manager.files import FilesMixin
from scenarios.case_manager.selectors import SEL as SEL  # re-export
from scenarios.case_manager.settings import SettingsMixin
from scenarios.case_manager.setup import SetupMixin
from scenarios.case_manager.suspects import SuspectsMixin


class CaseManagerScenarios(
    SetupMixin, CasesMixin, SuspectsMixin,
    DashboardMixin, SettingsMixin, FilesMixin,
    BaseScenario,
):
    OUTPUT_SUBDIR = "case-manager"

    async def run_all(self, only: list[str] | None = None) -> list[StepResult]:
        """Run Case Manager scenarios. If only is set, run only matching tests."""
        scenarios = [
            # Setup — create test data first
            self.setup_test_data,
            # Cases
            self.test_page_load,
            self.test_search_cases,
            self.test_create_monitoring_case,
            self.test_create_reporting_case,
            self.test_open_case_details,
            self.test_edit_case,
            self.test_case_comments,
            self.test_case_logs,
            self.test_case_prev_next,
            self.test_reporter_assignee,
            # Case updates & status flow
            self.test_update_case_fields,
            self.test_status_to_in_progress,
            self.test_status_to_closed,
            self.test_reopen_case,
            # Suspects
            self.test_suspects_search,
            self.test_suspects_search_with_updates,
            self.test_suspects_search_without_updates,
            self.test_suspect_detail,
            self.test_suspect_detail_links,
            # Dashboard
            self.test_dashboard,
            # Settings
            self.test_settings_processes,
            self.test_settings_edit_process,
            # File uploads
            self.test_reporting_case_file_upload,
            # General
            self.test_all_tabs,
            self.test_table_columns,
        ]

        if only:
            # Filter by S-number (e.g. "S21") or name substring
            only_lower = [o.lower() for o in only]
            def _matches(scenario):
                doc = (scenario.__doc__ or "").lower()
                name = scenario.__name__.lower()
                for o in only_lower:
                    # Exact S-number match: "s21" matches "s21:" but NOT "s2:"
                    s_match = re.search(r'\bs' + re.escape(o.lstrip('s')) + r'[:\s]', doc)
                    if s_match:
                        return True
                    if o in name:
                        return True
                return False
            scenarios = [s for s in scenarios if _matches(s)]

        for scenario in scenarios:
            print(f"    Running: {scenario.__doc__}")
            result = await scenario()
            icon = {"PASS": "PASS", "FAIL": "FAIL", "WARN": "WARN"}[result.status]
            print(f"      [{icon}] {result.description[:120]}")

        return self.results
