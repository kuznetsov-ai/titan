# TITAN — Testing Interfaces, Transactions And Networks

Автоматическое тестирование без участия человека: UI, API, валидация, интеграции.
AI обходит страницы, делает скриншоты, анализирует баги и генерирует отчёты.

## Возможности

- **Visual Regression** — обход всех страниц, скриншоты, AI-сравнение с baseline
- **E2E Scenarios** — интерактивные тесты (CRUD, формы, навигация, статусы, файлы)
- **AI Analysis** — Claude анализирует скриншоты упавших тестов (root cause + suggestion)
- **Multi-role** — тестирование под разными ролями
- **Slack verification** — проверка доставки файлов в Slack-каналы
- **Отчёты** — .md отчёты с severity P0-P3

## Установка

```bash
python -m venv .venv
source .venv/bin/activate
pip install playwright pyyaml pillow
playwright install chromium
```

## Быстрый старт

```bash
# E2E тесты Case Manager (все 25 сценариев)
.venv/bin/python3 cli.py test --system config/systems/backoffice.yaml --scenario case-manager --headed

# Только конкретные тесты (для отладки)
.venv/bin/python3 cli.py test -s config/systems/backoffice.yaml --scenario case-manager --only S21 S13

# Visual regression — сохранить baselines
.venv/bin/python3 cli.py run -s config/systems/backoffice.yaml --save-baselines

# Visual regression — сравнить с baselines
.venv/bin/python3 cli.py run -s config/systems/backoffice.yaml
```

## Архитектура

```
titan/
├── cli.py                     # CLI: команды `run` и `test`
├── config/
│   ├── loader.py              # YAML → dataclasses
│   └── systems/               # Конфиги целевых систем
│       └── backoffice.yaml
├── core/
│   ├── auth.py                # Авторизация через Playwright
│   ├── crawler.py             # BFS-краулер: обход страниц, скриншоты, JS/network ошибки
│   └── runner.py              # Оркестратор: auth → crawl → analyze → visual diff → report
├── ai/
│   ├── client.py              # Multi-provider AI client (claude_cli, anthropic, openai_compatible)
│   ├── analyst.py             # Анализ скриншотов на баги (P0-P3)
│   └── visual.py              # Visual diff baseline vs current
├── scenarios/
│   ├── base.py                # BaseScenario — общие хелперы для всех E2E
│   ├── constants.py           # Enum'ы из исходного кода (Severity, AbuseType, Process, ...)
│   ├── case_manager/          # Case Manager E2E — 25 сценариев (mixin-архитектура)
│   │   ├── __init__.py        # CaseManagerScenarios + run_all
│   │   ├── selectors.py       # CSS-селекторы
│   │   ├── setup.py           # S0: создание тестовых данных
│   │   ├── cases.py           # S1-S9, S15-S17, S22-S25: CRUD, статусы
│   │   ├── suspects.py        # S10-S11, S18-S20: подозреваемые
│   │   ├── dashboard.py       # S14: дашборд
│   │   ├── settings.py        # S12-S13: настройки
│   │   └── files.py           # S21: файловый upload + Slack
│   └── runner.py              # Запуск сценариев + AI-анализ + plugin loader
├── tests/                     # pytest — unit-тесты самого TITAN (39 тестов)
└── storage_layout/            # gitignored
    ├── baselines/             # Эталонные скриншоты
    └── runs/                  # Результаты прогонов (report.md, ai_analysis.md, screenshots)
```

## Как добавить тесты для нового UI

### Обязательные требования

1. **Исходный код** — нужна ссылка на git-репозиторий или локальный путь к проекту. Без анализа исходников тесты не пишутся.
2. **Список тест-кейсов** — мастер системы (владелец UI) должен предоставить полноценный список кейсов для тестирования. Если кейсы не описаны в репозитории — система не тестируется.
3. **Доступ к UI** — работающий инстанс + учётные данные.

### Шаги

1. Проанализировать исходный код: схемы, хендлеры, валидацию, компоненты UI
2. Мастер системы создаёт `testMe/` папку в своём репо с `howTestMe.yaml` и `ui_test_scenarios.py`
3. Добавить путь к `testMe/` в `config/systems/<system>.yaml` → секция `external_scenarios`
4. Запустить: `titan test --scenario <name> --headed`

### Принципы написания тестов

- **Только через UI** — никаких API-вызовов для создания данных. Всё через интерфейс.
- **Полное покрытие** — ВСЕ вкладки, ВСЕ кнопки, ВСЕ таблицы, ВСЕ поля форм, ВСЕ статусные переходы.
- **Селекторы из кода** — анализируем исходники, не угадываем CSS-классы.
- **Отладка точечная** — не гоняем все тесты каждый раз. `--only S21 S13` для конкретных.

## Конфигурация системы

```yaml
# config/systems/backoffice.yaml
name: backoffice
base_url: http://localhost:3000
environment: test

auth:
  type: login_password
  login_url: /login
  username_selector: "input[name='email']"
  password_selector: "input[name='password']"
  submit_selector: "button:has-text('NEXT')"

roles:
  - name: admin
    username: ${TITAN_USERNAME:<your-email>}
    password: ${TITAN_PASSWORD:<your-password>}

browser:
  type: chromium
  headless: true
  viewport:
    width: 1920
    height: 1080
  timeout: 30000

crawl:
  max_pages: 50
  screenshot_delay: 1500
  ignore_patterns:
    - "/logout"
    - "/api/*"
```

## Case Manager — тестовые сценарии

25 E2E-сценариев, покрывающих весь функционал:

| # | Сценарий | Описание |
|---|----------|----------|
| S0 | Setup | Создание тестовых данных: 2 monitoring + 2 reporting кейса |
| S1 | Page load | Загрузка страницы, табы, кнопка Search |
| S2 | Search | Поиск кейсов, проверка таблицы |
| S3 | Create monitoring | Заполнение формы мониторинг-кейса (7 полей) |
| S4 | Create reporting | Заполнение формы reporting-кейса (6 полей) |
| S5 | Case details | Открытие диалога деталей кейса |
| S6 | Edit case | Редактирование описания кейса |
| S7 | Reporter/Assignee | Проверка что нет "unknown" значений |
| S8 | All tabs | Проверка загрузки всех 6 вкладок |
| S9 | Table columns | Проверка колонок и заполненности данных |
| S10 | Suspects search | Поиск подозреваемых, проверка колонок |
| S11 | Suspect detail | Диалог деталей подозреваемого |
| S12 | Settings | Загрузка таблицы процессов (47 записей) |
| S13 | Edit process | Inline-редактирование процесса |
| S14 | Dashboard | Графики, статистика, фильтры |
| S15 | Comments | Добавление комментария к кейсу |
| S16 | Logs | Загрузка логов кейса |
| S17 | PREV/NEXT | Навигация между кейсами |
| S18 | External links | Проверка внешних ссылок (Backoffice, Restrictions, Toxicity, Ticks) |
| S19 | With updates ON | Поиск подозреваемых с обновлениями |
| S20 | With updates OFF | Поиск подозреваемых без фильтра обновлений |
| S21 | File upload | Загрузка файла в reporting-кейс + проверка в Slack |
| S22 | Update fields | Обновление нескольких полей кейса |
| S23 | Status → in_progress | Смена статуса на "в работе" |
| S24 | Status → closed | Закрытие кейса с подтверждением |
| S25 | Reopen case | Переоткрытие закрытого кейса |

## AI Integration

Поддерживает три провайдера (настраивается в YAML конфиге):

| Провайдер | Описание | API ключ |
|-----------|----------|----------|
| `claude_cli` | Claude Code CLI (`claude --print`) | Не нужен |
| `anthropic` | Anthropic Messages API | `ANTHROPIC_API_KEY` |
| `openai_compatible` | Любой OpenAI-совместимый API (прокси, внутренние LLM, Codex) | `api_base` + `api_key` в конфиге |

Используется для: анализа скриншотов на баги, visual diff, AI-анализа упавших тестов.

## Severity

| Level | Описание | Примеры |
|-------|----------|---------|
| P0 | Нельзя использовать | Краш, белый экран, нет доступа |
| P1 | Основной flow сломан | Кнопка не работает, форма не отправляется |
| P2 | Работает, но плохо | Загрузка >3с, сдвиг элементов |
| P3 | Косметика | Опечатки, мелкие стили |

## Результаты

Сохраняются в `storage_layout/runs/<timestamp>/`:
- `report.md` — основной отчёт (таблица шагов, summary, детали ошибок)
- `ai_analysis.md` — AI-анализ упавших шагов
- `*.png` — скриншоты каждого шага
