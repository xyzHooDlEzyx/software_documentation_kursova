---
name: fitness-backend
description: Реалізує Django REST Framework API, прикладні сервіси, селектори, авторизацію й інтеграційні тести фітнес-додатка. Використовуй, коли змінюється поведінка серверної частини, REST-операція, транзакція або межа безпеки.
argument-hint: REST ID, серверний сценарій або помилка
---

# Серверна частина

## Контракт і структура

Починай із `FR`/`UC`, `BR` і конкретного ID з 49 операцій у
`docs/architecture/rest-api.md`. Не копіюй таблицю операцій, поля чи бізнес-правила
до коментарів коду або навички. Доменні межі звіряй із
`docs/architecture/domain-model.md`, дані — з `docs/architecture/erd.md`.

Стек зафіксовано: Python 3.14, Django 6, DRF і PostgreSQL 17. Settings розділено
на `backend/config/settings/base.py`, `local.py`, `test.py`, `production.py`.

Реалізовані Django apps:

- `backend/accounts/` — облікові записи, профіль, вага, auth, throttling і
  спільні API errors;
- `backend/catalog/` — каталог, публікація, Django Admin і `seed_catalog`;
- `backend/planning/` — персональні програми, `Strategy` і planning services;
- `backend/execution/`, `backend/engagement/` — поки порожні каркаси apps.

`backend/reporting/` поки звичайний пакет і не входить до `INSTALLED_APPS`.
Заплановані класи не подавай як наявні.

## Шари

Дотримуйся напряму:

`views` (HTTP, auth, permissions) → `serializers` (форма/типи) → `services`
(транзакції, блокування, бізнес-інваріанти) / `selectors` (читання).

- Для writable input успадковуйся від `StrictSerializer` у
  `backend/accounts/serializers.py`, щоб невідомі поля не ігнорувалися.
- Views не повинні координувати кілька записів або містити бізнес-рішення.
- Сервіс запису володіє `transaction.atomic()` і повертає контрольований
  результат; selector не змінює стан.
- Чужий і відсутній приватний ID мають однакову відповідь 404. Спочатку обмеж
  вибірку власником, потім виконай пошук.

## Помилки та пагінація

Усі API-помилки проходять через `exception_handler` у
`backend/accounts/errors.py` і оболонку
`{error:{code,message,fields,request_id}}`. Використовуй наявні доменні коди
`profile_missing`, `profile_exists`, `recommendation_unavailable`,
`recommendation_mismatch`, `invalid_state`, `email_taken`, `unknown_field`,
`invalid_credentials`, `reset_token_invalid_or_expired`; новий код додавай лише
коли REST-контракт справді розрізняє новий випадок.

`_paginate_queryset` і `_extract_query_data` дублюються у
`backend/catalog/views.py` та `backend/planning/views.py`. Це відомий борг:
використай наявну копію в цих модулях, але не додавай четверту; при наступному
спільному споживачі краще окремим малим рефакторингом виділити helper і покрити його
тестами.

## Транзакції та GoF

Порядок блокувань для запланованих фаз 5–7 визначено в Domain Model і REST design:
`UserProgram` → запланований `ScheduledSession` → пов’язані рядки. Сам
`ScheduledSession` ще не реалізовано. Новий service має дотримуватися цього
порядку, `select_for_update()` і однієї атомарної межі.

`Strategy` уже реалізовано в `backend/planning/strategies.py` і викликається
`ProgramSelectionService`. `Observer` та `Template Method` спроєктовано, але їхні
учасники заплановано для фаз 6–7. Не підмінюй їх Django Signals і не додавай
`Factory Method`, `State` або `Command` без потреби за
`docs/architecture/additional-gof-proposals.md`.

## Тести

Тести виконуються через pytest-django лише на PostgreSQL; роль повинна мати
`CREATEDB`. API security cases використовують `APIClient(enforce_csrf_checks=True)`.
Приклади є в `backend/accounts/tests/` і `backend/planning/tests/test_api.py`.

`backend/conftest.py` очищає throttle cache до й після кожного тесту. Не дублюй
цей fixture локально. Міграції перевіряй через `MigrationExecutor`, як у
`backend/catalog/tests/test_tracks_distance.py` та
`backend/planning/tests/test_migrations.py`.

Тести конкурентного запису з двома PostgreSQL connections додавай лише там, де їх прямо вимагає
локальний `docs/implementation/implementation-plan.md` або конкретний ризик
конкурентного запису; не імітуй перегони БД звичайними послідовними mocks.

## Безпека

Throttles визначено у `backend/accounts/throttling.py`, scopes і rates — у
`backend/config/settings/base.py`. `REST_FRAMEWORK["NUM_PROXIES"]` читається з
`DJANGO_NUM_PROXIES`; не довіряй proxy headers без узгодженої топології.
Email backend задає `DJANGO_EMAIL_BACKEND`, а `.env.example` використовує console
backend. Не вимикай CSRF і не послаблюй session auth заради тесту чи dev proxy.
