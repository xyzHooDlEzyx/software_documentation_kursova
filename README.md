# Фітнес-трекер — курсова робота, варіант 4

Репозиторій містить документацію архітектури та каркас Phase 0: Django/DRF API, React/TypeScript/Vite frontend і конфігурацію PostgreSQL. Бізнес-моделей, користувацьких сторінок і REST-операцій поки немає. Подальші інкременти описані в [плані реалізації](docs/implementation/implementation-plan.md).

## Передумови та версії

- Python 3.14.4 використано для локальної перевірки; Django 6.0 підтримує Python 3.12–3.14.
- Node.js 22.22.1 і npm 9.2.0 використано для frontend перевірки; цей набір Vite/Vitest/jsdom вимагає Node.js 22.13+ або 24+.
- PostgreSQL: локальний сервер або необов'язковий Docker Compose з `postgres:17`.
- Backend: Django 6.0.9, DRF 3.18.3, psycopg 3.3.6; для розробки pytest 9.2.0, pytest-django 4.14.0, Ruff 0.17.3. Версії зафіксовано в `backend/requirements*.txt` і повному dev-lockfile.
- Frontend: React 19.3.1, Vite 8.3.5, TypeScript 6.0.2; точні прямі й транзитивні версії зафіксовано у `frontend/package-lock.json`.

## Важливо перед першим запуском БД

**Не запускайте `python manage.py migrate` у Phase 0.** У Phase 1 спочатку буде створено `accounts.User` і встановлено `AUTH_USER_MODEL`; лише після цього дозволена перша міграція. Інакше Django може застосувати auth-міграції зі стандартним User і ускладнити перехід. Phase 0 запускає `check` і smoke-тести без доступу до БД. Admin, seed і користувацькі endpoint також належать наступним фазам.

## Локальне налаштування

Із кореня репозиторію:

```bash
cp .env.example .env
python3 -c 'import secrets; print(secrets.token_urlsafe(50))'
# Вставте отриманий ключ у DJANGO_SECRET_KEY в .env і задайте власний POSTGRES_PASSWORD.
set -a
. ./.env
set +a

python3 -m venv backend/.venv
backend/.venv/bin/python -m pip install -r backend/requirements-dev.lock
npm ci --prefix frontend
```

`.env` і `backend/.venv` ігноруються Git. Пароль у `.env.example` — лише заповнювач; не використовуйте його як справжній пароль. Для виробничого запуску потрібні окремі секрети, HTTPS та `config.settings.production`.

### PostgreSQL

Можна використати вже наявний PostgreSQL: створіть роль і базу із назвами з `.env` та надайте ролі права власника. Наприклад, для локального сервера з системним користувачем `postgres` (виконайте вручну, якщо маєте відповідні права):

```bash
sudo -u postgres createuser --pwprompt fitness_app
sudo -u postgres createdb --owner=fitness_app fitness_dev
```

Укажіть пароль, який ввели у `createuser`, у локальному `.env`. Якщо роль/БД вже існують, налаштуйте `.env` відповідно до них. Альтернатива без змін системного PostgreSQL — Docker Compose, якщо Docker доступний:

```bash
docker compose up -d db
```

Compose читає `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` і `POSTGRES_PORT` з `.env` та відкриває порт лише на `127.0.0.1`. Docker не потрібен для запуску із наявною PostgreSQL.

### Backend

У терміналі з уже завантаженим `.env`:

```bash
backend/.venv/bin/python backend/manage.py check
backend/.venv/bin/python backend/manage.py runserver localhost:8000
```

База має бути доступна для `runserver`, але міграції Phase 0 **не застосовуються**. Префікс `/api/v1/` підготовлено; поки він повертає Django 404, бо endpoint ще не створені. `reporting` є звичайним Python-пакетом; п'ять порожніх Django apps — `accounts`, `catalog`, `planning`, `execution`, `engagement`.

### Frontend і dev proxy

В іншому терміналі:

```bash
npm --prefix frontend run dev
```

Відкрийте `http://localhost:5173`. Vite пересилає `/api/v1/*` на Django `http://localhost:8000`; браузер звертається лише до origin `:5173`, а frontend API helper використовує відносні шляхи та `credentials: "same-origin"`. `changeOrigin: false` зберігає сумісні Host/Origin для CSRF; `DJANGO_CSRF_TRUSTED_ORIGINS` обмежений конкретним dev origin. Немає permissive CORS або вимкнення CSRF. У локальному HTTP secure-cookie прапорці вимкнені; у production HTTPS увімкнені. Endpoint A01, login/logout і повні cookie/CSRF тести належать Phase 1.

## Перевірки Phase 0

```bash
backend/.venv/bin/python backend/manage.py check
cd backend
.venv/bin/python -m pytest
.venv/bin/ruff check .
.venv/bin/ruff format --check .
cd ../frontend
npm run typecheck
npm run lint
npm test
npm run build
```

Smoke-тест Django не запитує БД і не запускає міграції. Пізніші інтеграційні тести використовуватимуть PostgreSQL, зокрема для транзакцій і `select_for_update()`; SQLite не замінює ці перевірки.
