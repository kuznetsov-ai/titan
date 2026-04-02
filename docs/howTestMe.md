# howTestMe — Как подготовить сервис к тестированию через TITAN

**TITAN** (**T**esting **I**nterfaces, **T**ransactions **A**nd **N**etworks) — автоматическое тестирование UI, API, валидации и интеграций.

Чтобы TITAN мог протестировать ваш сервис, нужно подготовить папку `testMe/` в корне репозитория сервиса.

---

## Зачем это нужно

TITAN не угадывает, что тестировать. Он работает по описанным кейсам. Без папки `testMe/` сервис **не тестируется**.

---

## Папка `testMe/`

Каждая система / интерфейс / отчёт должна содержать папку `testMe/` в корне своего репозитория. Это единая точка входа для TITAN — всё, что нужно для тестирования, лежит здесь.

```
my-service/
├── internal/
├── cmd/
├── ...
└── testMe/
    ├── howTestMe.yaml          # Главный файл: описание сервиса + тест-кейсы
    ├── fixtures/               # Тестовые данные (JSON, CSV, файлы для upload)
    │   ├── test_attachment.png
    │   ├── valid_uuids.json
    │   └── ...
    ├── mocks/                  # Моки внешних сервисов (опционально)
    │   └── ...
    └── docs/                   # Доп. документация (опционально)
        ├── validation_rules.md # Правила валидации полей
        ├── status_flow.md      # Диаграмма статусных переходов
        └── integrations.md     # Описание интеграций (Slack, MinIO, etc.)
```

### Обязательные файлы

| Файл | Описание |
|------|----------|
| `howTestMe.yaml` | Описание сервиса, окружения, тест-кейсов, UI-специфики |

### Опциональные файлы

| Папка/файл | Когда нужен |
|------------|-------------|
| `fixtures/` | Есть файловые аплоады, нужны тестовые данные |
| `mocks/` | Есть внешние зависимости, которые нужно замокать |
| `docs/validation_rules.md` | Сложная валидация, которую трудно описать в YAML |
| `docs/status_flow.md` | Есть статусная машина (new → in_progress → closed → ...) |
| `docs/integrations.md` | Есть интеграции с внешними системами (Slack, Kafka, S3, ...) |

### Пример: Case Manager

```
case-manager/
└── testMe/
    ├── howTestMe.yaml          # 14 тест-кейсов, P0-P2
    ├── fixtures/
    │   └── test_attachment.png # Файл для теста загрузки
    └── docs/
        └── validation_rules.md # Monitoring vs Reporting, critical vs non-critical
```

---

## Структура файла

```yaml
# howTestMe.yaml — описание сервиса для TITAN
service:
  name: case-manager                    # slug сервиса
  repo: git.exness.io/trading-anti-fraud/case-manager  # git-репозиторий
  local_path: /Projects/Case manager/case-manager      # или локальный путь (опционально)
  type: backoffice                      # backoffice | web | api | mixed
  description: "Управление подозрительными кейсами, suspects, дашборд"

# Где взять работающий UI
environment:
  base_url: http://localhost:3000       # URL для тестирования
  setup: docker compose -f docker-compose.bo.yml up -d  # как поднять
  auth:
    method: login_password              # login_password | token | oauth | none
    credentials:
      - role: admin
        username: ${TITAN_USERNAME:<your-email>}
        password: ${TITAN_PASSWORD:<your-password>}
      - role: readonly
        username: viewer@home.app
        password: viewer
  dependencies:                         # что ещё должно быть запущено
    - "docker: case-manager-fix-api-1 (./app api backoffice)"
    - "daemon: ./app daemon slack-sync"
    - "daemon: ./app daemon susp-enricher"
    - "infra: PostgreSQL, Kafka, MinIO, Zookeeper"

# Тест-кейсы — ядро документа
test_cases:
  # ─── UI ──────────────────────────────────
  ui:
    - id: TC-UI-01
      name: "Загрузка главной страницы"
      tab: Cases
      actions:
        - "Открыть /case-manager"
        - "Проверить наличие вкладок: Cases, Suspects, Dashboard, Create Monitoring Case, Create Reporting Case, Settings"
        - "Проверить наличие кнопки Search"
        - "Проверить наличие таблицы кейсов"
      expected: "Страница загружена, все элементы видны, нет JS-ошибок"
      priority: P0

    - id: TC-UI-02
      name: "Поиск кейсов"
      tab: Cases
      preconditions: "Есть хотя бы 1 кейс в системе"
      actions:
        - "Нажать кнопку Search"
        - "Дождаться загрузки таблицы"
      expected: "Таблица содержит строки с данными"
      priority: P0

    - id: TC-UI-03
      name: "Создание Monitoring Case"
      tab: Create Monitoring Case
      actions:
        - "Перейти на вкладку Create Monitoring Case"
        - "Заполнить обязательные поля: title, user_uids (UUID), abuse_type, process, severity, description, jira_tickets"
        - "Нажать Create Monitoring Case"
      expected: "Кейс создан без ошибок (нет 400/422/500)"
      priority: P0
      validation_rules:
        - "title: обязательное"
        - "user_uids: обязательное, формат UUID"
        - "abuse_type: обязательное, выбор из списка"
        - "process: обязательное, выбор из списка"
        - "severity: обязательное (low/medium/high/critical)"
        - "description: обязательное"
        - "jira_tickets: обязательное"
        - "Если severity=critical: link обязателен + files обязательны"

    - id: TC-UI-04
      name: "Создание Reporting Case"
      tab: Create Reporting Case
      actions:
        - "Перейти на вкладку Create Reporting Case"
        - "Заполнить: user_uids, abuse_type, symbol, severity, description"
        - "Если severity != critical: приложить файл + выбрать suspicious_timeframe"
        - "Если severity = critical: заполнить link (файл НЕ нужен)"
        - "Нажать Create Reporting Case"
      expected: "Кейс создан без ошибок"
      priority: P0
      validation_rules:
        - "user_uids: обязательное, формат UUID"
        - "abuse_type: обязательное"
        - "symbol: обязательное"
        - "severity: обязательное"
        - "description: обязательное"
        - "severity != critical → files + suspicious_timeframe обязательны"
        - "severity = critical → link обязателен, files НЕ нужны"

    - id: TC-UI-05
      name: "Просмотр деталей кейса"
      tab: Cases
      preconditions: "Есть кейсы в таблице"
      actions:
        - "Кликнуть на ID кейса в таблице"
        - "Проверить что открылся диалог с полями"
      expected: "Диалог деталей открыт, видны все поля кейса"
      priority: P0

    - id: TC-UI-06
      name: "Редактирование кейса"
      tab: Cases
      preconditions: "Открыт диалог деталей (TC-UI-05)"
      actions:
        - "Изменить description"
        - "Изменить abuse_type (через dropdown)"
        - "Изменить investigation_outcome"
        - "Нажать Save"
      expected: "Изменения сохранены без ошибок"
      priority: P0

    - id: TC-UI-07
      name: "Статусный flow: new → in_progress → closed → reopen"
      tab: Cases
      preconditions: "Есть кейс в статусе new"
      actions:
        - "Открыть кейс → сменить статус на In Progress"
        - "Сменить статус на Closed → подтвердить в диалоге"
        - "Найти закрытый кейс (добавить Closed в фильтр!) → нажать Reopen"
      expected: "Каждый переход без ошибок, статус обновляется"
      priority: P1
      edge_cases:
        - "Закрытые кейсы не видны в поиске по умолчанию — нужно добавить 'Closed' в фильтр caseStatuses"
        - "Закрытие и переоткрытие требуют подтверждения (диалог Yes/Confirm)"

    - id: TC-UI-08
      name: "Загрузка файла + доставка в Slack"
      tab: Create Reporting Case
      preconditions: "Запущен daemon slack-sync"
      actions:
        - "Создать reporting case с файлом (severity=medium)"
        - "Проверить файл в деталях кейса"
        - "Проверить что файл появился в Slack-треде кейса"
      expected: "Файл виден в UI и доставлен в Slack (< 30 сек)"
      priority: P1
      integrations:
        - "MinIO: файл сохраняется в cases/{id}/"
        - "Slack: файл отправляется в тред кейса через EventCaseScreenshotAdded"

    - id: TC-UI-09
      name: "Комментарии и логи"
      tab: Cases
      preconditions: "Открыт диалог деталей кейса"
      actions:
        - "Добавить комментарий"
        - "Переключить на Logs"
        - "Проверить загрузку логов"
      expected: "Комментарий сохранён, логи загружены"
      priority: P1

    - id: TC-UI-10
      name: "Suspects — поиск и детали"
      tab: Suspects
      actions:
        - "Отключить фильтры has_updates и openOnly"
        - "Нажать Search"
        - "Проверить колонки: UID, Country, Cases, Client Profit, Black Flags, Abuse Ratio"
        - "Кликнуть на UUID → проверить детали подозреваемого"
        - "Проверить внешние ссылки: Backoffice, Restrictions, Toxicity, Ticks"
      expected: "Таблица загружена, детали видны, все ссылки присутствуют"
      priority: P1

    - id: TC-UI-11
      name: "Dashboard"
      tab: Dashboard
      actions:
        - "Открыть Dashboard"
        - "Нажать FILTER"
        - "Проверить наличие графиков (Highcharts)"
        - "Проверить статистику (Total cases, Total suspects)"
        - "Проверить фильтры: Process, Severity, Investigation Outcome, Country Code"
      expected: "Графики рендерятся, статистика видна, фильтры доступны"
      priority: P2

    - id: TC-UI-12
      name: "Settings — процессы"
      tab: Settings
      actions:
        - "Открыть Settings"
        - "Проверить таблицу процессов (колонки: Name, Process name)"
        - "Кликнуть Edit на первом процессе"
        - "Проверить что появился inline input"
      expected: "Таблица загружена, inline-редактирование активируется"
      priority: P2

    - id: TC-UI-13
      name: "Навигация PREV/NEXT"
      tab: Cases
      preconditions: "Открыт диалог деталей кейса, есть несколько кейсов"
      actions:
        - "Нажать NEXT"
        - "Нажать PREV"
      expected: "Навигация между кейсами работает без ошибок"
      priority: P2

    - id: TC-UI-14
      name: "Reporter и Assignee"
      tab: Cases
      actions:
        - "Открыть таблицу кейсов"
        - "Проверить что нет значений 'unknown' в колонках Reporter, Assignee, Updated By"
      expected: "Все значения разрезолвлены (не 'unknown')"
      priority: P2
      known_bugs:
        - "Reporter/Assignee могли отображаться как 'unknown' — баг, сейчас исправлен"

  # ─── API (будущие тесты) ──────────────
  # api:
  #   - id: TC-API-01
  #     name: "POST /api/cases/manage — создание кейса"
  #     method: POST
  #     endpoint: /api/cases/manage
  #     body: { ... }
  #     expected_status: 200
  #     expected_body: { "message": "case saved successfully" }

  # ─── Валидация (будущие тесты) ────────
  # validation:
  #   - id: TC-VAL-01
  #     name: "Невалидный UUID отклоняется"
  #     actions: "Ввести 'not-a-uuid' в user_uids → submit"
  #     expected: "422 Validation Error"

# Особенности UI (важно для написания автотестов)
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
    - "Custom Select: клик на input с force=True → ждать button.ListItem_item → кликнуть"
    - "DatePicker: НЕ использовать fill(), кликать пресеты (Last 30 days)"
    - "Submit кнопки: всегда scope через [class*='Button_button'], иначе зацепит табы"
    - "Тосты/нотификации могут перекрывать элементы — нужна retry-логика"
    - "Закрытые кейсы не видны в дефолтном поиске — добавить Closed в фильтр"
```

---

## Секция `ui_elements` — ОБЯЗАТЕЛЬНАЯ сверка с реальным UI

Самая частая причина провала тестов — **несовпадение текстов кнопок, типов полей и названий колонок** между описанием и реальным UI. Описание из кода или документации часто расходится с тем, что рендерится на экране.

### Что нужно сверить (открыть страницу в браузере и записать ТОЧНО):

| Элемент | Что записать | Частые ошибки |
|---------|-------------|---------------|
| **Кнопка submit** | Точный текст: "CREATE REPORT", не "Generate", не "RUN" | Текст из кода vs реальный текст на кнопке |
| **Поля формы** | Тип (textarea / dropdown / date picker / input) + placeholder | Dropdown путают с date picker |
| **Колонки таблицы** | Точные заголовки из `<thead>` | Колонки без текста (иконки, действия) |
| **Кнопки действий** | Точные тексты: "Download", "Fill out", "GDrive" | "GDrive" vs "Google Drive Upload" |
| **Пустое состояние** | Текст при отсутствии данных: "No data found" | — |
| **Формат данных** | Дата: "Apr 02 2026, 11:33:32 AM" | — |

### Формат секции `ui_elements`:

```yaml
ui_elements:
  page:
    title: "LTHVC Check"                     # H1 заголовок — ТОЧНЫЙ текст
  form:
    fields:
      - name: "UUIDs"
        label: "UUIDs (up to 25000)"         # placeholder — ТОЧНЫЙ текст
        type: textarea                       # textarea | select_dropdown | date_picker | text_input
      - name: "ScoringDate"
        label: "Scoring date"
        type: select_dropdown                # НЕ date_picker!
    submit_button:
      text: "CREATE REPORT"                  # ТОЧНЫЙ текст кнопки
  report_log:
    table:
      columns: ["ID", "Date", "Client"]      # ТОЧНЫЕ заголовки
      total_columns: 7                       # включая безымянные
    empty_state: "No data found"
  report_detail_dialog:
    action_buttons:                           # ТОЧНЫЕ тексты кнопок
      - "Fill out"
      - "Copy"
      - "Repeat"
      - "Download"
      - "Logs"
      - "GDrive"
```

### Как сверять:
1. Открыть страницу в браузере
2. Для каждого элемента — скопировать текст как есть
3. Тип поля — кликнуть и посмотреть: открывается календарь (date_picker), выпадающий список (select_dropdown) или просто текстовое поле
4. Колонки — посмотреть `<thead>`, записать только непустые заголовки + общее количество `<th>`
5. Кнопки действий — открыть диалог/строку, записать все видимые тексты кнопок

---

## Формат описания тест-кейса

Каждый кейс должен содержать:

| Поле | Обязательное | Описание |
|------|:---:|----------|
| `id` | да | Уникальный ID: TC-UI-01, TC-API-01, TC-VAL-01 |
| `name` | да | Короткое название на русском или английском |
| `tab` / `endpoint` | да | Для UI — вкладка, для API — endpoint |
| `actions` | да | Список шагов (что делать) |
| `expected` | да | Ожидаемый результат |
| `priority` | да | P0 — нельзя работать, P1 — основной flow, P2 — второстепенное |
| `preconditions` | нет | Что должно быть подготовлено |
| `validation_rules` | нет | Правила валидации полей |
| `edge_cases` | нет | Граничные случаи |
| `integrations` | нет | Внешние системы (Slack, MinIO, Kafka...) |
| `known_bugs` | нет | Известные баги |

---

## Уровень детализации

### Хорошо — точные тексты + бизнес-логика:
```yaml
- id: TC-UI-02
  name: "Отправка пустой формы"
  actions:
    - "Оставить все поля пустыми"
    - "Нажать 'CREATE REPORT'"              # ← ТОЧНЫЙ текст кнопки с экрана
    - "Дождаться ответа (3-5 сек)"
  expected: "Отчёт создан, новая строка в таблице Report Log"
  validation_rules:
    - "UUIDs: required=false"
    - "ScoringDate: required=false, по умолчанию = вчера"
```

### Хорошо — edge cases описаны:
```yaml
- id: TC-UI-04
  name: "Создание Reporting Case"
  actions:
    - "Заполнить user_uids (UUID формат)"
    - "Выбрать abuse_type из dropdown"
    - "Severity = Medium"
    - "Приложить файл (обязательно для non-critical)"
    - "Нажать 'CREATE REPORTING CASE'"       # ← ТОЧНЫЙ текст кнопки
  expected: "201/200, кейс появляется в таблице"
  validation_rules:
    - "severity=critical → link обязателен, файл НЕ нужен"
    - "severity!=critical → файл + timeframe обязательны"
```

### Плохо — неточные тексты кнопок:
```yaml
- id: TC-UI-02
  name: "Отправка формы"
  actions:
    - "Нажать 'Submit'"                      # ← НЕПРАВИЛЬНО! Реальный текст: "CREATE REPORT"
    - "Нажать 'Generate'"                    # ← НЕПРАВИЛЬНО! Такой кнопки нет
  expected: "Отчёт создан"
```
**Результат: тесты провалятся — кнопка не найдена, timeout 30 сек на каждый тест.**

### Плохо — неправильный тип поля:
```yaml
fields:
  - name: "ScoringDate"
    type: date_picker                        # ← НЕПРАВИЛЬНО! Реально это select_dropdown
```
**Результат: тест будет искать календарь, а его нет.**

### Плохо — слишком размыто:
```yaml
- id: TC-01
  name: "Создание отчёта"
  actions: "Создать отчёт"
  expected: "Отчёт создан"
```

### Плохо — CSS-селекторы (не нужно):
```yaml
- id: TC-01
  actions:
    - "Кликнуть на button[class*='Button_button']:has-text('CREATE REPORT')"
    - "Подождать 500мс"
```
Селекторы и тайминги — задача TITAN, не мастера сервиса.

---

## Что TITAN сделает сам

Вам **НЕ нужно** описывать:
- CSS-селекторы
- Тайминги и ожидания
- Как работать с кастомными компонентами (dropdown, datepicker)
- Как делать скриншоты
- Как анализировать ошибки

Вам **НУЖНО** описать:
- Какие поля обязательные и когда
- Какие есть edge cases (critical severity → другие правила)
- Какие интеграции проверять (файл → Slack)
- Какие баги известны
- В каком порядке выполнять (статус: new → in_progress → closed)

---

## Типы тестов

| Тип | Префикс | Что тестирует | Пример |
|-----|---------|---------------|--------|
| UI | TC-UI | Интерфейс: формы, таблицы, навигация | Создание кейса через форму |
| API | TC-API | REST endpoints напрямую | POST /api/cases/manage |
| Validation | TC-VAL | Валидация входных данных | Невалидный UUID → 422 |
| Integration | TC-INT | Связь между системами | Файл → MinIO → Slack |
| Regression | TC-REG | Visual regression скриншоты | Страница не изменилась vs baseline |

---

## Checklist перед передачей в TITAN

- [ ] Папка `testMe/` создана в корне репозитория
- [ ] `testMe/howTestMe.yaml` заполнен
- [ ] Указан git-репозиторий или локальный путь к исходному коду
- [ ] Описаны ВСЕ тест-кейсы (минимум P0 и P1)
- [ ] Указаны правила валидации для каждой формы
- [ ] Описаны edge cases (разное поведение в зависимости от условий)
- [ ] Указаны интеграции (Slack, MinIO, Kafka, etc.)
- [ ] Указаны известные баги
- [ ] Есть рабочий инстанс + credentials для всех ролей
- [ ] Описаны зависимости (какие сервисы/демоны должны работать)
- [ ] Тестовые файлы (fixtures) положены в `testMe/fixtures/`
- [ ] Доп. документация (валидация, статусы, интеграции) в `testMe/docs/`
