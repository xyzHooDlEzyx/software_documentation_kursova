# Фітнес-трекер — курсова робота, варіант 4

Веб-додаток для планування тренувань і відстеження прогресу (дисципліна «Документування ПЗ та шаблони проєктування», варіант 4). Стек: Django + DRF, PostgreSQL, React + TypeScript + Vite.

## Поточний стан

| Частина | Реалізовано | Ще не реалізовано |
|---|---|---|
| Backend (REST) | 47 з 47 REST-операцій контракту та 2 адмін-звіти R02/R03; Phase 8 додає owner-scoped read projections, статистику й leaderboard | PostgreSQL runtime-перевірка Phase 8 у reviewer environment |
| БД | 20 з 20 таблиць ERD, включно з immutable execution snapshots, ledger, досягненнями й челенджами | прикладні сценарії наступних фаз не потребують нових базових сутностей ERD |
| Адмін-частина | Django Admin: каталог, деактивація, челенджі, view-only досягнення та агреговані R02/R03 з period filter, таблицею, inline SVG і CSV | — |
| Frontend | реєстрація, вхід, вихід, відновлення пароля, налаштування рейтингу; профіль та історія ваги (P01–P04), каталог тренувань і вправ (C01–C04), рекомендація, персональні програми, активація й прогрес (G01–G08), тижневий розклад і планування (S01–S04), нагадування з непрочитаним badge (N01–N03) | скасування слотів і архівація програм (S05/G09), виконання тренувань, статистика, соціальні функції, звіти |

Документація: [вимоги](docs/analysis/requirements.md), [Use Case діаграма](docs/analysis/use-case-diagram.md), [бізнес-правила](docs/analysis/business-rules.md), [доменна модель](docs/architecture/domain-model.md), [ERD](docs/architecture/erd.md), [REST API](docs/architecture/rest-api.md), [принципи й GoF](docs/architecture/design-principles.md), [діаграма класів](docs/diagrams/class-diagram.drawio), [рев'ю стану](docs/review/senior-review-2026-11-14.md).

## Передумови та версії

- Python 3.14 (перевірено 3.14.4; `pyproject.toml` налаштовано на `py314`); Django 6.0.9, DRF 3.18.3, psycopg 3.3.6. Для розробки: pytest 9.2.0, pytest-django 4.14.0, Ruff 0.17.3. Версії зафіксовано в `backend/requirements*.txt` і `backend/requirements-dev.lock`.
- Node.js 22.13+ або 24+ з npm, що постачається разом із Node (локально перевірено Node 22.22.1). React 19.3.1, Vite 8.3.5, TypeScript 6.0.2; точні версії — у `frontend/package-lock.json`.
- PostgreSQL 17: локальний сервер або Docker Compose (`compose.yaml`).

## Запуск з нуля

Усі команди — з кореня репозиторію.

### 1. Змінні середовища і залежності

```bash
cp .env.example .env
python3 -c 'import secrets; print(secrets.token_urlsafe(50))'
```

Вставте отриманий ключ у `DJANGO_SECRET_KEY` у `.env` і задайте власний `POSTGRES_PASSWORD`. Потім завантажте змінні в поточний термінал (це потрібно в **кожному** новому терміналі перед `manage.py` чи `pytest`):

```bash
set -a; . ./.env; set +a
```

```bash
python3 -m venv backend/.venv
backend/.venv/bin/python -m pip install -r backend/requirements-dev.lock
npm ci --prefix frontend
```

`.env` і `backend/.venv` ігноруються Git. Пароль у `.env.example` — лише заповнювач.

### 2. PostgreSQL

Варіант А — Docker Compose (порт відкривається лише на `127.0.0.1`):

```bash
docker compose up -d db
```

Якщо Docker Desktop на Linux використовує окремий context: `docker --context desktop-linux compose up -d db`.

Варіант Б — наявний локальний PostgreSQL: створіть роль із правом `CREATEDB` (потрібне для тестів) і базу з назвами з `.env`:

```bash
sudo -u postgres createuser --createdb --pwprompt fitness_app
sudo -u postgres createdb --owner=fitness_app fitness_dev
```

### 3. Міграції, демо-каталог, адміністратор

```bash
backend/.venv/bin/python backend/manage.py migrate
backend/.venv/bin/python backend/manage.py seed_catalog
backend/.venv/bin/python backend/manage.py createsuperuser
```

- `migrate` створює всі таблиці та групу `Administrator` із правами на каталог, деактивацію користувачів і агреговані звіти (`reporting.view_reports`).
- `seed_catalog` заповнює каталог вправ, тренувань і опублікованих шаблонів програм. Без нього каталог і рекомендації програм будуть порожні.
- `createsuperuser` створює технічного суперкористувача. Робочих адміністраторів він призначає в Django Admin: позначка `is_staff` + група `Administrator`.

### 4. Запуск

Backend (термінал 1, з уже завантаженим `.env`):

```bash
backend/.venv/bin/python backend/manage.py runserver localhost:8000
```

Frontend (термінал 2):

```bash
npm --prefix frontend run dev
```

| Що | Адреса |
|---|---|
| Користувацький інтерфейс | http://localhost:5173 |
| Адмін-частина (Django Admin) | http://localhost:8000/admin/ |
| REST API | http://localhost:5173/api/v1/… (через Vite proxy) |

Vite пересилає `/api/v1/*` на Django `:8000`, тому браузер працює з одним origin `:5173`, а CSRF/session cookie лишаються same-origin. Django Admin відкривається напряму на `:8000`.

### Відновлення пароля локально

Лист зі посиланням на скидання пароля локально виводиться в консоль `runserver`, якщо в `.env` задано (це значення вже є в `.env.example`):

```
DJANGO_EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
```

## REST API (реалізовані операції)

Префікс — `/api/v1/`. Повний контракт (47 REST-операцій і 2 адмін-звіти): [docs/architecture/rest-api.md](docs/architecture/rest-api.md).

| ID | Метод і шлях | Доступ |
|---|---|---|
| A01 | `GET auth/csrf/` | Публічний |
| A02 | `POST auth/register/` | Публічний, CSRF, rate limit |
| A03 | `POST auth/login/` | Публічний, CSRF, rate limit (IP та email) |
| A04 | `POST auth/logout/` | Сесія, CSRF |
| A05 / A06 | `GET` / `PATCH me/` | Сесія (PATCH — CSRF) |
| A07 | `POST auth/password-reset/` | Публічний, CSRF, rate limit |
| A08 | `POST auth/password-reset/confirm/` | Публічний, CSRF, rate limit |
| P01 / P02 / P03 | `GET` / `POST` / `PATCH profile/` | Сесія |
| P04 | `GET weight-entries/` | Сесія |
| P05 / R01 | `GET statistics/weight-chart/`, `GET statistics/overview/` | Сесія, обов'язковий Kyiv-період; R01 містить continuous weekly activity |
| C01 | `GET categories/` | Сесія |
| C02 | `GET exercises/` | Сесія |
| C03 / C04 | `GET workouts/`, `GET workouts/{id}/` | Сесія |
| G01 | `GET program-recommendation/` | Сесія, потрібен профіль |
| G02 / G03 | `GET` / `POST user-programs/` | Сесія |
| G04 / G05 | `GET` / `PATCH user-programs/{id}/` | Сесія, лише власні програми |
| G06 | `PUT user-programs/{id}/workouts/{entry_id}/` | Сесія, лише власні програми |
| G07 | `POST user-programs/{id}/activate/` | Сесія, CSRF, лише власні програми |
| G08 | `GET user-programs/{id}/progress/` | Сесія, лише власні програми |
| G09 | `POST user-programs/{id}/archive/` | Сесія, CSRF, лише власні програми |
| S01 / S02 | `GET` / `POST scheduled-sessions/` | Сесія (POST — CSRF), лише власні слоти |
| S03 / S04 | `GET` / `PATCH scheduled-sessions/{id}/` | Сесія (PATCH — CSRF), лише власні слоти |
| S05 | `POST scheduled-sessions/{id}/cancel/` | Сесія, CSRF, лише власні слоти |
| E01 | `POST completed-sessions/` | Сесія, CSRF, профіль та `Idempotency-Key` UUID v4 |
| E02 / E03 | `GET completed-sessions/`, `GET completed-sessions/{id}/` | Сесія, лише власні незмінні факти |
| M01 / M02 | `GET points/summary/`, `GET point-transactions/` | Сесія, власний ledger |
| M03 / M04 | `GET achievements/`, `GET user-achievements/` | Сесія |
| N01 | `GET notifications/` | Сесія, лише власні видимі нагадування |
| N02 | `GET notifications/{id}/` | Сесія, лише власні видимі нагадування |
| N03 | `POST notifications/{id}/read/` | Сесія, CSRF, лише власні видимі нагадування |
| H01 | `GET challenges/` | Сесія; лише опубліковані визначення |
| H02 | `GET challenges/{id}/` | Сесія; прихований/неіснуючий ID повертає 404 |
| H03 | `POST challenges/{id}/join/` | Сесія, CSRF; повтор повертає 200, після завершення — 409 |
| H04 | `GET challenge-participations/` | Сесія, лише власні участі |
| L01 | `GET leaderboard/` | Сесія; публічні лише alias, points і rank |

## Адміністративні звіти

Після входу staff-користувача з permission `reporting.view_reports` звіти доступні з індексу Django Admin:

- R02: `/admin/reports/workout-popularity/`;
- R03: `/admin/reports/average-activity/`.

Обидва вимагають `start_date` і `end_date`, показують лише агрегати, inline SVG без JavaScript і дають CSV у UTF-8 з BOM. Міграція `reporting.0002_administrator_report_permission` додає permission групі `Administrator`; сам `is_staff` доступу не дає.

Безпека: session-автентифікація (`sessionid` HttpOnly), CSRF для всіх змінних запитів, вільний CORS не використовується. Реєстрація не виконує автоматичний вхід; мінімальна довжина пароля — 12 символів. Ліміти запитів налаштовуються змінними `DJANGO_THROTTLE_*`. `DJANGO_NUM_PROXIES` — кількість довірених reverse proxy перед Django: `0` (типово) означає, що IP береться з `REMOTE_ADDR`, а заголовок `X-Forwarded-For` від клієнта ігнорується.

## Перевірки

```bash
backend/.venv/bin/python backend/manage.py check --database default
backend/.venv/bin/python backend/manage.py makemigrations --check --dry-run
cd backend
.venv/bin/python -m pytest
.venv/bin/ruff check .
.venv/bin/ruff format --check .
cd ../frontend
npm run typecheck
npm run lint
npm test
npm run build
npx prettier --check <змінені файли>
```

Frontend-код форматує Prettier (`frontend/.prettierrc.json`): `npm run format -- <файли>` для файлів, які змінюєте.

Backend-тести працюють на окремій тестовій базі PostgreSQL (SQLite не використовується), тому `.env` має бути завантажений, а роль БД — мати право `CREATEDB`.

## Production

Окреме production-розгортання ще не налаштоване. `config.settings.production` вимагає власних секретів, HTTPS та `DJANGO_NUM_PROXIES`, що відповідає реальному proxy; роздача зібраного `frontend/dist` і `collectstatic` ще не описані.

## Діагностика

- **Перевірка з'єднання з БД і proxy:** `backend/.venv/bin/python backend/manage.py showmigrations --plan` відкриває з'єднання з PostgreSQL і показує стан міграцій (`manage.py check` без `--database` з БД не з'єднується). `curl -i http://localhost:5173/api/v1/auth/csrf/` перевіряє проходження запиту через Vite до Django.
- **`Connection refused` на `127.0.0.1:5432`:** PostgreSQL або контейнер `db` не запущено. Перевірте `ss -ltnp | grep 5432`, `systemctl is-active postgresql` або `docker ps`.
- **Docker Engine чи Docker Desktop:** Engine слухає `/var/run/docker.sock` (context `default`), Desktop — `~/.docker/desktop/docker.sock` (context `desktop-linux`). Активний context показує `docker context ls`.
- **API профілю/каталогу/програм повертає 500 про відсутню таблицю:** не застосовано міграції — виконайте `manage.py migrate` (і `seed_catalog`).
- **Тести не стартують:** не завантажено `.env` у цьому терміналі або роль БД не має `CREATEDB` (`sudo -u postgres psql -c "ALTER ROLE fitness_app CREATEDB;"`).
