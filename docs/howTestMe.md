# howTestMe — How to prepare your service for TITAN testing

**TITAN** (**T**esting **I**nterfaces, **T**ransactions **A**nd **N**etworks) — automated testing of UI, API, validation, and integrations.

To enable TITAN testing for your service, create a `testMe/` folder in your repository root.

> **IMPORTANT: All test cases, descriptions, comments, and documentation must be written in English.** No Russian or other non-English text in `howTestMe.yaml`, `ui_test_scenarios.py`, or any other files inside `testMe/`. This ensures consistency across all Exness repositories.

---

## Why

TITAN does not guess what to test. It works from described test cases. Without a `testMe/` folder, the service **will not be tested**.

---

## `testMe/` folder structure

Every system / interface / report must have a `testMe/` folder in its repository root. This is the single entry point for TITAN — everything needed for testing lives here.

```
my-service/
├── internal/
├── cmd/
├── ...
└── testMe/
    ├── howTestMe.yaml          # Main file: service description + test cases
    ├── ui_test_scenarios.py    # Playwright E2E scenarios for TITAN runner
    ├── fixtures/               # Test data (JSON, CSV, files for upload)
    │   ├── test_attachment.png
    │   ├── valid_uuids.json
    │   └── ...
    ├── mocks/                  # External service mocks (optional)
    │   └── ...
    └── docs/                   # Additional documentation (optional)
        ├── validation_rules.md # Field validation rules
        ├── status_flow.md      # State machine diagram
        └── integrations.md     # External integrations (Slack, MinIO, etc.)
```

### Required files

| File | Description |
|------|-------------|
| `howTestMe.yaml` | Service description, environment, test cases, UI specifics |
| `ui_test_scenarios.py` | Playwright test class with `run_all()` method |

### Optional files

| Path | When needed |
|------|-------------|
| `fixtures/` | File uploads, test data needed |
| `mocks/` | External dependencies that need mocking |
| `docs/validation_rules.md` | Complex validation hard to describe in YAML |
| `docs/status_flow.md` | State machine (new → in_progress → closed → ...) |
| `docs/integrations.md` | External system integrations (Slack, Kafka, S3, ...) |

### Example: Case Manager

```
case-manager/
└── testMe/
    ├── howTestMe.yaml          # 14 test cases, P0-P2
    ├── ui_test_scenarios.py    # 25 Playwright scenarios
    ├── fixtures/
    │   └── test_attachment.png # File for upload test
    └── docs/
        └── validation_rules.md # Monitoring vs Reporting, critical vs non-critical
```

---

## `howTestMe.yaml` structure

```yaml
# howTestMe.yaml — service description for TITAN
service:
  name: case-manager                    # service slug
  repo: git.exness.io/trading-anti-fraud/case-manager  # git repository
  local_path: /Projects/Case manager/case-manager      # local path (optional)
  type: backoffice                      # backoffice | web | api | mixed
  description: "Suspicious cases management, suspects, dashboard"

# Where to find the running UI
environment:
  base_url: http://localhost:3000       # URL for testing
  setup: docker compose -f docker-compose.bo.yml up -d  # how to start
  auth:
    method: login_password              # login_password | token | oauth | none
    credentials:
      - role: admin
        username: ${TITAN_USERNAME:<your-email>}
        password: ${TITAN_PASSWORD:<your-password>}
  dependencies:                         # what else must be running
    - "docker: case-manager-fix-api-1 (./app api backoffice)"
    - "daemon: ./app daemon slack-sync"
    - "infra: PostgreSQL, Kafka, MinIO, Zookeeper"

# Test cases — the core of the document
test_cases:
  ui:
    - id: TC-UI-01
      name: "Page load"
      tab: Cases
      actions:
        - "Open /case-manager"
        - "Verify tabs: Cases, Suspects, Dashboard, Create Monitoring Case, Create Reporting Case, Settings"
        - "Verify Search button present"
        - "Verify cases table present"
      expected: "Page loaded, all elements visible, no JS errors"
      priority: P0

    - id: TC-UI-02
      name: "Search cases"
      tab: Cases
      preconditions: "At least 1 case exists"
      actions:
        - "Click Search button"
        - "Wait for table to load"
      expected: "Table contains data rows"
      priority: P0

    - id: TC-UI-03
      name: "Create Monitoring Case"
      tab: Create Monitoring Case
      actions:
        - "Navigate to Create Monitoring Case tab"
        - "Fill required fields: title, user_uids (UUID), abuse_type, process, severity, description, jira_tickets"
        - "Click 'Create Monitoring Case'"
      expected: "Case created without errors (no 400/422/500)"
      priority: P0
      validation_rules:
        - "title: required"
        - "user_uids: required, UUID format"
        - "abuse_type: required, select from list"
        - "process: required, select from list"
        - "severity: required (low/medium/high/critical)"
        - "description: required"
        - "jira_tickets: required"
        - "If severity=critical: link required + files required"

  # api:
  #   - id: TC-API-01
  #     name: "POST /api/cases/manage — create case"
  #     method: POST
  #     endpoint: /api/cases/manage
  #     expected_status: 200

  # validation:
  #   - id: TC-VAL-01
  #     name: "Invalid UUID rejected"
  #     actions: "Enter 'not-a-uuid' in user_uids → submit"
  #     expected: "422 Validation Error"

# UI specifics (important for writing automated tests)
ui_specifics:
  framework: "Backoffice (schema-driven, CSS Modules)"
  selector_patterns:
    tabs: 'button[class*="Tab_tab"]:has-text("...")'
    buttons: 'button[class*="Button_button"]:has-text("...")'
    tables: 'table[class*="Table_table"]'
    dropdowns: 'input[name="field_name"] → button.ListItem_item'
    dialogs: '[class*="Dialog_content"]'
    dialog_close: 'button[class*="Dialog_close"]'
    file_input: '[class*="FileInput"]'
    switches: 'label (sibling of hidden checkbox input)'
  gotchas:
    - "Custom Select: click input with force=True → wait for button.ListItem_item → click"
    - "DatePicker: do NOT use fill(), click presets (e.g. 'Last 30 days')"
    - "Submit buttons: always scope via [class*='Button_button'] to avoid matching tabs"
    - "Toast notifications may block clicks — retry logic needed"
    - "Closed cases hidden from default search — add 'Closed' to caseStatuses filter"
```

---

## `ui_elements` section — MANDATORY UI verification

The most common cause of test failures is **mismatch between button texts, field types, and column names** in the description vs the actual UI. Code-based or documentation-based descriptions often diverge from what renders on screen.

### What to verify (open the page in browser and record EXACTLY):

| Element | What to record | Common mistakes |
|---------|---------------|-----------------|
| **Submit button** | Exact text: "CREATE REPORT", not "Generate", not "RUN" | Text from code vs actual button text |
| **Form fields** | Type (textarea / dropdown / date picker / input) + placeholder | Dropdown confused with date picker |
| **Table columns** | Exact headers from `<thead>` | Columns without text (icons, actions) |
| **Action buttons** | Exact texts: "Download", "Fill out", "GDrive" | "GDrive" vs "Google Drive Upload" |
| **Empty state** | Text when no data: "No data found" | — |
| **Data format** | Date: "Apr 02 2026, 11:33:32 AM" | — |

### `ui_elements` format:

```yaml
ui_elements:
  page:
    title: "LTHVC Check"                     # H1 heading — EXACT text
  form:
    fields:
      - name: "UUIDs"
        label: "UUIDs (up to 25000)"         # placeholder — EXACT text
        type: textarea                       # textarea | select_dropdown | date_picker | text_input
      - name: "ScoringDate"
        label: "Scoring date"
        type: select_dropdown                # NOT date_picker!
    submit_button:
      text: "CREATE REPORT"                  # EXACT button text
  report_log:
    table:
      columns: ["ID", "Date", "Client"]      # EXACT headers
      total_columns: 7                       # including unnamed columns
    empty_state: "No data found"
  report_detail_dialog:
    action_buttons:                           # EXACT button texts
      - "Fill out"
      - "Copy"
      - "Repeat"
      - "Download"
      - "Logs"
      - "GDrive"
```

### How to verify:
1. Open the page in browser
2. For each element — copy the text as-is
3. Field type — click and observe: calendar opens (date_picker), dropdown list (select_dropdown), or plain text field
4. Columns — inspect `<thead>`, record non-empty headers + total `<th>` count
5. Action buttons — open dialog/row, record all visible button texts

---

## Test case format

Each test case must contain:

| Field | Required | Description |
|-------|:---:|-------------|
| `id` | yes | Unique ID: TC-UI-01, TC-API-01, TC-VAL-01 |
| `name` | yes | Short name **in English** |
| `tab` / `endpoint` | yes | For UI — tab name, for API — endpoint |
| `actions` | yes | Step-by-step actions **in English** |
| `expected` | yes | Expected result **in English** |
| `priority` | yes | P0 — blocking, P1 — main flow, P2 — secondary |
| `preconditions` | no | What must be prepared |
| `validation_rules` | no | Field validation rules |
| `edge_cases` | no | Edge cases |
| `integrations` | no | External systems (Slack, MinIO, Kafka...) |
| `known_bugs` | no | Known bugs |

---

## Level of detail

### How detailed should test cases be?

**Very detailed.** TITAN is an AI-driven automation tool, not a human QA engineer. It cannot guess business logic, validation rules, or expected behavior from context. Every test case must be explicit and self-contained.

**The rule: if someone who has never seen your service reads the test case, they must understand exactly what to do and what to expect.**

Each test case should describe:

1. **Every field in the form** — name, type, whether required or optional, valid/invalid values, default value
2. **Every button** — exact text as displayed on screen (case-sensitive!)
3. **Every dropdown option** — all available values listed explicitly
4. **Every validation rule** — what happens when input is invalid, what error message appears
5. **Every state transition** — from → to, what triggers it, what confirmation is needed
6. **Every edge case** — what changes when severity=critical vs medium, what happens with empty input, what happens at boundaries (max length, min date)
7. **Every integration** — what external system is affected (Slack, MinIO, Kafka), what to verify there
8. **Every table column** — exact header text, data format, sort order
9. **Every dialog/modal** — what triggers it, what buttons are inside, what happens on close
10. **Every error scenario** — invalid UUID, missing required field, network error, timeout

### What "too vague" looks like and why it fails:

| Vague description | Why TITAN can't work with it | What to write instead |
|---|---|---|
| "Fill the form" | Which fields? What values? | "Fill: title='Test', user_uids='<valid UUID>', abuse_type=select 'Arbitrage', severity=select 'Medium'" |
| "Submit" | Which button? What text? | "Click 'CREATE REPORT' button" |
| "Check the table" | Which columns? What data? How many rows? | "Verify table has columns: ID, Date, Client. Verify at least 1 row. Verify newest row has status '✓'" |
| "It should work" | What does "work" mean? | "No 400/422/500 errors. New row appears in Report Log. Status changes to 'processing' within 5 sec" |
| "Test validation" | Which field? What input? What error? | "Enter 'not-a-uuid' in UUIDs field → click 'CREATE REPORT' → expect 422 error with message 'invalid uuids not-a-uuid'" |
| "Test all statuses" | Which statuses? What transitions? What order? | "new → in_progress (click Status dropdown, select 'In Progress'). in_progress → closed (select 'Closed', confirm in Yes/No dialog). closed → in_progress (add 'Closed' to filter, find case, click 'Reopen', confirm)" |

### Minimum required detail per field:

```yaml
fields:
  - name: "UUIDs"                              # field name attribute
    label: "UUIDs (up to 6000)"                # exact placeholder/label text
    type: textarea                             # textarea | text_input | select_dropdown | date_picker | date_range_picker | checkbox | file_upload
    required: false                            # true | false
    default: ""                                # default value if any
    max_length: 6000                           # max input length
    validation: "uuid.Parse() per UUID"        # validation logic
    valid_example: "550e8400-e29b-41d4-a716-446655440000"  # example valid input
    invalid_example: "not-a-uuid"              # example invalid input
    error_message: "invalid uuids {value}"     # exact error text
    delimiter: "newline or comma"              # for multi-value fields
    notes: "UUIDs are deduplicated and sorted" # any special behavior

  - name: "Status"
    label: "Status"
    type: select_dropdown
    required: false
    default: "All"
    options:                                   # ALL available options listed
      - "All"
      - "Enabled"
      - "Disabled"
    notes: "Affects which users appear in results"

  - name: "ScoringDate"
    label: "Scoring date"
    type: select_dropdown                      # NOT date_picker!
    required: false
    default: "yesterday (UTC)"
    min_value: "2021-01-01"
    notes: "Dropdown with predefined dates, not a calendar"
```

### Minimum required detail per test case:

```yaml
- id: TC-UI-07
  name: "Status flow: new → in_progress → closed → reopen"
  preconditions:
    - "At least 1 case exists in status 'new'"
    - "daemon slack-sync is running (for Slack notifications)"
  actions:
    - "Open case detail dialog (click case ID in table)"
    - "Scroll to Status field"
    - "Click Status dropdown (input[name='status'], force click)"
    - "Select 'In Progress' from dropdown options"
    - "Wait 2 sec for API response"
    - "Verify: no 400/422/500 errors, status updated"
    - "Click Status dropdown again"
    - "Select 'Closed'"
    - "Confirmation dialog appears with 'Yes'/'No' buttons"
    - "Click 'Yes' to confirm"
    - "Verify: case status is now 'closed'"
    - "Go to Cases tab, add 'Closed' to caseStatuses filter (closed cases are HIDDEN by default!)"
    - "Click Search"
    - "Find the closed case in results"
    - "Open case detail"
    - "Click 'Reopen' button"
    - "Confirmation dialog appears"
    - "Click 'Yes'"
    - "Verify: case status is now 'in_progress'"
  expected: "All 3 transitions succeed without errors. Each status change reflected in UI immediately."
  priority: P1
  edge_cases:
    - "Closed cases are NOT visible in default search — filter must include 'Closed' status"
    - "Both close and reopen require confirmation dialog (Yes/No)"
    - "Status dropdown uses custom Select component — requires force click on input"
  integrations:
    - "Slack: status change events sent to case thread"
  known_bugs:
    - "Previously status dropdown was not scrollable — fixed in v2.3"
```

### Good — exact texts + business logic:
```yaml
- id: TC-UI-02
  name: "Submit empty form"
  actions:
    - "Leave all fields empty"
    - "Click 'CREATE REPORT'"              # ← EXACT button text from screen
    - "Wait for response (3-5 sec)"
  expected: "Report created, new row in Report Log table"
  validation_rules:
    - "UUIDs: required=false"
    - "ScoringDate: required=false, defaults to yesterday"
```

### Good — edge cases described:
```yaml
- id: TC-UI-04
  name: "Create Reporting Case"
  actions:
    - "Fill user_uids (UUID format)"
    - "Select abuse_type from dropdown"
    - "Severity = Medium"
    - "Attach file (required for non-critical)"
    - "Click 'CREATE REPORTING CASE'"       # ← EXACT button text
  expected: "201/200, case appears in table"
  validation_rules:
    - "severity=critical → link required, file NOT needed"
    - "severity!=critical → file + timeframe required"
```

### Bad — wrong button texts:
```yaml
- id: TC-UI-02
  name: "Submit form"
  actions:
    - "Click 'Submit'"                      # ← WRONG! Actual text: "CREATE REPORT"
    - "Click 'Generate'"                    # ← WRONG! No such button
  expected: "Report created"
```
**Result: tests will fail — button not found, 30 sec timeout per test.**

### Bad — wrong field type:
```yaml
fields:
  - name: "ScoringDate"
    type: date_picker                        # ← WRONG! Actually select_dropdown
```
**Result: test will look for a calendar that doesn't exist.**

### Bad — too vague:
```yaml
- id: TC-01
  name: "Create report"
  actions: "Create report"
  expected: "Report created"
```

### Bad — CSS selectors (not needed):
```yaml
- id: TC-01
  actions:
    - "Click button[class*='Button_button']:has-text('CREATE REPORT')"
    - "Wait 500ms"
```
Selectors and timings are TITAN's job, not the service owner's.

---

## What TITAN handles automatically

You do **NOT** need to describe:
- CSS selectors
- Timings and waits
- How to interact with custom components (dropdown, datepicker)
- How to take screenshots
- How to analyze errors

You **DO** need to describe:
- Which fields are required and when
- What edge cases exist (critical severity → different rules)
- Which integrations to verify (file → Slack)
- Known bugs
- Execution order (status: new → in_progress → closed)

---

## Test types

| Type | Prefix | What it tests | Example |
|------|--------|---------------|---------|
| UI | TC-UI | Interface: forms, tables, navigation | Create case via form |
| API | TC-API | REST endpoints directly | POST /api/cases/manage |
| Validation | TC-VAL | Input validation | Invalid UUID → 422 |
| Integration | TC-INT | Cross-system communication | File → MinIO → Slack |
| Regression | TC-REG | Visual regression screenshots | Page unchanged vs baseline |

---

## Language requirement

**All content in `testMe/` must be in English:**
- `howTestMe.yaml` — test case names, descriptions, actions, expected results
- `ui_test_scenarios.py` — class names, method names, docstrings, comments, print messages
- `docs/*.md` — all documentation
- `fixtures/` — file names

This is a hard requirement. PRs with non-English text in `testMe/` will be rejected.

---

## Checklist before submitting to TITAN

- [ ] `testMe/` folder created in repository root
- [ ] `testMe/howTestMe.yaml` filled out **in English**
- [ ] `testMe/ui_test_scenarios.py` created **in English**
- [ ] Git repository or local path to source code specified
- [ ] ALL test cases described (at minimum P0 and P1)
- [ ] Validation rules specified for each form
- [ ] Edge cases described (different behavior depending on conditions)
- [ ] Integrations specified (Slack, MinIO, Kafka, etc.)
- [ ] Known bugs listed
- [ ] Working instance + credentials for all roles available
- [ ] Dependencies described (which services/daemons must be running)
- [ ] Test fixtures placed in `testMe/fixtures/`
- [ ] Additional docs (validation, statuses, integrations) in `testMe/docs/`
- [ ] **All text is in English — no Russian or other languages**
