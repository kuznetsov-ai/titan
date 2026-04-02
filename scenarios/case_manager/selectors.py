from __future__ import annotations

# ── Selectors from source code ──────────────────────────
SEL = {
    # Tabs — CSS modules: button.Tab_tab with text content
    "tab_cases":              'button[class*="Tab_tab"]:has-text("Cases")',
    "tab_suspects":           'button[class*="Tab_tab"]:has-text("Suspects")',
    "tab_dashboard":          'button[class*="Tab_tab"]:has-text("Dashboard")',
    "tab_create_monitoring":  'button[class*="Tab_tab"]:has-text("Create Monitoring Case")',
    "tab_create_reporting":   'button[class*="Tab_tab"]:has-text("Create Reporting Case")',
    "tab_settings":           'button[class*="Tab_tab"]:has-text("Settings")',

    # Buttons
    "btn_search":             'button[type="submit"]:has-text("Search")',
    # Submit buttons — exclude Tab_tab to avoid clicking tabs
    "btn_create_monitoring":  'button[class*="Button_button"]:has-text("Create Monitoring Case")',
    "btn_create_reporting":   'button[class*="Button_button"]:has-text("Create Reporting Case")',

    # Table — CSS modules: table.Table_table
    "table_cases":            'table[class*="Table_table"]',

    # Dialogs — look for modal/dialog containers
    "dialog_details":         '[class*="Dialog"], [class*="Modal"], [class*="dialog"]',
    "dialog_update":          '[class*="Dialog"], [class*="Modal"], [class*="dialog"]',

    # Form fields (name attribute — these come from the schema)
    "field_title":            '[name="title"]',
    "field_user_uids":        '[name="user_uids"]',
    "field_abuse_type":       '[name="abuse_type"]',
    "field_severity":         '[name="severity"]',
    "field_process":          '[name="process"]',
    "field_symbol":           '[name="symbol"]',
    "field_description":      '[name="description"]',
    "field_jira_tickets":     '[name="jira_tickets"]',
    "field_assignee":         '[name="assignee"]',
    "field_decision_due":     '[name="decision_due_date"]',
    "field_link":             '[name="link"]',
    "field_files":            '[name="files"]',
    "field_timeframe":        '[name="suspicious_timeframe"]',
    "field_connections":      '[name="connections"]',
    "field_status":           '[name="status"]',
}
