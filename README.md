# Фітнес-трекер — курсова робота, варіант 4

Репозиторій містить документацію архітектури та повну реалізацію Phase 0 і Phase 1: кастомний `accounts.User`, Django session authentication, CSRF-захищений REST API A01–A08 (включно з відновленням пароля) та React-екрани реєстрації, входу, налаштувань і скидання пароля (`D01`/`D02`). Наступні інкременти описані в [плані реалізації](docs/implementation/implementation-plan.md).

## Передумови та версії

- Python 3.14.4 використано для локальної перевірки; Django 6.0 підтримує Python 3.12–3.14.
- Node.js 22.22.1 і npm 9.2.0 використано для frontend перевірки; цей набір Vite/Vitest/jsdom вимагає Node.js 22.13+ або 24+.
- PostgreSQL: локальний сервер або необов'язковий Docker Compose з `postgres:17`.
- Backend: Django 6.0.9, DRF 3.18.3, psycopg 3.3.6; для розробки pytest 9.2.0, pytest-django 4.14.0, Ruff 0.17.3. Версії зафіксовано в `backend/requirements*.txt` і повному dev-lockfile.
- Frontend: React 19.3.1, Vite 8.3.5, TypeScript 6.0.2; точні прямі й транзитивні версії зафіксовано у `frontend/package-lock.json`.

## Міграції та кастомний User

`AUTH_USER_MODEL = "accounts.User"` встановлено до першої міграції. Початковий `accounts.0001_initial` створює таблицю `users` з email-ідентичністю; `accounts.0002` уточнює DB `CHECK` для псевдоніма та opt-in без зміни застосованого `0001`. На новій базі запускайте `migrate` лише з цими файлами в коді. Не створюйте стандартний `auth.User` і не скидайте вже заповнену БД для переходу на іншу модель.

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
sudo -u postgres createuser --createdb --pwprompt fitness_app
sudo -u postgres createdb --owner=fitness_app fitness_dev
```

Укажіть пароль, який ввели у `createuser`, у локальному `.env`. Якщо роль/БД вже існують, налаштуйте `.env` відповідно до них. Альтернатива без змін системного PostgreSQL — Docker Compose, якщо Docker доступний:

```bash
docker compose up -d db
```

Compose читає `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` і `POSTGRES_PORT` з `.env` та відкриває порт лише на `127.0.0.1`. Якщо Docker Desktop на Linux використовує окремий context, запускайте `docker --context desktop-linux compose up -d db`. Docker не потрібен для запуску із наявною PostgreSQL.

### Backend

У терміналі з уже завантаженим `.env`:

```bash
backend/.venv/bin/python backend/manage.py check
backend/.venv/bin/python backend/manage.py migrate
backend/.venv/bin/python backend/manage.py runserver localhost:8000
```

`reporting` є звичайним Python-пакетом. Доменні таблиці пізніших фаз ще не створено. Технічний superuser створюється через `createsuperuser`; у Django Admin він може призначити існуючому користувачу `is_staff` і групу `Administrator` з правом `accounts.deactivate_user`. Працівник із цим правом бачить лише список акаунтів і дію деактивації, без редагування ролей або приватних профілів.

### Frontend і dev proxy

В іншому терміналі:

```bash
npm --prefix frontend run dev
```

Відкрийте `http://localhost:5173`. Vite пересилає `/api/v1/*` на Django `http://localhost:8000`; браузер звертається лише до origin `:5173`, а frontend API helper використовує відносні шляхи та `credentials: "same-origin"`. `changeOrigin: false` зберігає сумісні Host/Origin для CSRF. Перед POST/PATCH клієнт бере cookie через A01 і передає поточний `csrftoken` у `X-CSRFToken`; після входу Django ротирує token, а клієнт читає новий cookie для наступної дії. `sessionid` має HttpOnly і не зберігається в React. У production обидва cookie мають Secure та потрібен HTTPS. Вільний CORS не використовується.

### API Phase 1

| ID | Метод і шлях | Успіх | Доступ |
|---|---|---:|---|
| A01 | `GET /api/v1/auth/csrf/` | 200 | Публічний |
| A02 | `POST /api/v1/auth/register/` | 201 | Публічний, CSRF |
| A03 | `POST /api/v1/auth/login/` | 200 | Публічний, CSRF |
| A04 | `POST /api/v1/auth/logout/` | 204 | Сесія, CSRF |
| A05 | `GET /api/v1/me/` | 200 | Сесія |
| A06 | `PATCH /api/v1/me/` | 200 | Сесія, CSRF |
| A07 | `POST /api/v1/auth/password-reset/` | 200 | Публічний, CSRF, Throttling |
| A08 | `POST /api/v1/auth/password-reset/confirm/` | 200 | Публічний, CSRF, Throttling |

Реєстрація не виконує автоматичний вхід і не створює профіль. Мінімальна довжина пароля — 12 символів; застосовуються стандартні Django validators. Сесія триває 7 днів без подовження від кожного запиту. Після деактивації вхід і чинна сесія блокуються. Пароль і хеш не повертаються API. Профіль, тренування й звіти належать наступним фазам.

## Перевірки Phase 1

```bash
backend/.venv/bin/python backend/manage.py check
backend/.venv/bin/python backend/manage.py makemigrations --check --dry-run
backend/.venv/bin/python backend/manage.py showmigrations
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

Backend тести створюють окрему PostgreSQL test-базу, тому роль БД має дозволяти її створення. Для тестів завантажте `.env` перед запуском команд. Жоден тест не використовує SQLite. HTTP-сценарій через Vite origin `:5173` перевірено: A01 → A02 → A03 → A05 → A06 → A04 → 401 для A05. Виробниче розгортання та доменні функції Phase 2+ ще не реалізовані.

### Діагностика підключення до PostgreSQL і proxy

- **Перевірка живого з'єднання з PostgreSQL та Vite proxy:** `backend/.venv/bin/python backend/manage.py showmigrations --plan` (перевіряє TCP-підключення і стан міграцій у PostgreSQL; `manage.py check` без прапорців не відкриває з'єднання з БД) та `curl -i http://localhost:5173/api/v1/auth/csrf/` (перевіряє проходження `/api/v1/*` через Vite `:5173` до Django `:8000` і видачу `csrftoken`).
- **`Connection refused` на `127.0.0.1:5432`:** локальний сервер PostgreSQL або контейнер `db` не запущено. Перевірте `ss -ltnp | grep 5432`, статус системного сервісу (`systemctl is-active postgresql`) або запущених контейнерів.
- **Docker Engine проти Docker Desktop на Linux:** системний Docker Engine слухає `/var/run/docker.sock` (контекст `default`), тоді як Docker Desktop працює у власній VM і слухає `~/.docker/desktop/docker.sock` (контекст `desktop-linux`, сервіс `systemctl --user is-active docker-desktop`). Перевірте активний контекст через `docker context ls` і використовуйте `docker --context desktop-linux compose up -d db`, якщо запущено саме Docker Desktop.
- **Нова сесія термінала або запуск `pytest`:** змінні з `.env` не підвантажуються автоматично — перед командами `manage.py` чи `pytest` у кожному новому терміналі виконайте `set -a; . ./.env; set +a` з кореня репозиторію (або `set -a; . ../.env; set +a` із каталогу `backend/`). Для `pytest` роль PostgreSQL повинна мати право `CREATEDB` (у контейнері `postgres:17` воно надається `POSTGRES_USER` автоматично; для локального сервера: `sudo -u postgres psql -c "ALTER ROLE fitness_app CREATEDB;"`).
