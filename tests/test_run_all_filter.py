from __future__ import annotations

import re

# ---------------------------------------------------------------------------
# Reproduce the filter logic from CaseManagerScenarios.run_all so we can
# test it without Playwright or any async machinery.
# ---------------------------------------------------------------------------

def _matches(doc: str, name: str, only: list[str]) -> bool:
    """Exact replica of the filter closure in CaseManagerScenarios.run_all."""
    only_lower = [o.lower() for o in only]
    doc = doc.lower()
    name = name.lower()
    for o in only_lower:
        s_match = re.search(r'\bs' + re.escape(o.lstrip('s')) + r'[:\s]', doc)
        if s_match:
            return True
        if o in name:
            return True
    return False


# Fake scenario catalogue — mirrors the real docstrings and method names.
SCENARIOS = [
    ("setup_test_data",                "S0: Create test data"),
    ("test_page_load",                 "S1: Verify Case Manager page loads with tabs and search."),
    ("test_search_cases",              "S2: Click SEARCH and verify results table has rows."),
    ("test_create_monitoring_case",    "S3: Fill and submit CREATE MONITORING CASE form."),
    ("test_create_reporting_case",     "S4: Fill and submit CREATE REPORTING CASE form."),
    ("test_open_case_details",         "S5: Click a case ID in table to open details dialog."),
    ("test_edit_case",                 "S6: Click EDIT in case detail dialog, modify description, save."),
    ("test_reporter_assignee",         "S7: Verify Reporter and Assignee are not 'unknown'."),
    ("test_all_tabs",                  "S8: Click each tab and verify content loads without errors."),
    ("test_table_columns",             "S9: Verify expected columns and data population."),
    ("test_suspects_search",           "S10: Open Suspects tab, disable filters, search."),
    ("test_suspect_detail",            "S11: Open suspect detail dialog, verify fields."),
    ("test_settings_processes",        "S12: Open Settings tab, verify Processes table loads."),
    ("test_settings_edit_process",     "S13: Click edit on a process, verify inline edit activates."),
    ("test_dashboard",                 "S14: Open Dashboard, click FILTER, verify charts."),
    ("test_case_comments",             "S15: Open case detail, add a comment, verify it appears."),
    ("test_case_logs",                 "S16: Open case detail, click Logs button, verify logs load."),
    ("test_case_prev_next",            "S17: In case detail, click PREV/NEXT buttons."),
    ("test_suspect_detail_links",      "S18: In suspect detail, verify external links."),
    ("test_suspects_search_with_updates",    "S19: Search suspects with 'With updates' ON."),
    ("test_suspects_search_without_updates", "S20: Search suspects with 'With updates' OFF."),
    ("test_reporting_case_file_upload",      "S21: Create reporting case with file."),
    ("test_update_case_fields",        "S22: Open EDIT, change multiple fields."),
    ("test_status_to_in_progress",     "S23: Change case status from 'new' to 'in_progress'."),
    ("test_status_to_closed",          "S24: Change case status to 'closed'."),
    ("test_reopen_case",               "S25: Reopen a closed case via 'Reopen Case' button."),
]


def _filtered(only: list[str] | None) -> list[str]:
    """Return method names that survive the filter."""
    if only is None:
        return [name for name, _ in SCENARIOS]
    return [name for name, doc in SCENARIOS if _matches(doc, name, only)]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_filter_exact_s1():
    result = _filtered(["S1"])
    assert "test_page_load" in result          # S1
    assert "test_suspects_search" not in result  # S10
    assert "test_suspect_detail" not in result   # S11


def test_filter_exact_s10():
    result = _filtered(["S10"])
    assert "test_suspects_search" in result    # S10
    assert "test_page_load" not in result      # S1


def test_filter_s21():
    result = _filtered(["S21"])
    assert result == ["test_reporting_case_file_upload"]


def test_filter_multiple():
    result = _filtered(["S1", "S21"])
    assert len(result) == 2
    assert "test_page_load" in result
    assert "test_reporting_case_file_upload" in result


def test_filter_none():
    result = _filtered(None)
    assert len(result) == len(SCENARIOS)


def test_filter_by_method_name():
    result = _filtered(["dashboard"])
    assert "test_dashboard" in result
