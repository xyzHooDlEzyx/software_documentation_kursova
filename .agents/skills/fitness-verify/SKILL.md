---
name: fitness-verify
description: Запускає відтворювані комплекси перевірок серверної й клієнтської частин та ручний E2E і фіксує лише перевірені результати. Використовуй, коли треба довести готовність зрізу, знайти регресію або підготувати докази до захисту.
argument-hint: Зріз, сценарій або набір перевірок
---

# Перевірка

## Передумови

Працюй із кореня репозиторію. Backend-команди потребують змінних з `.env`:

```bash
set -a; . ./.env; set +a
```
PostgreSQL має бути доступний, а тестова роль — мати `CREATEDB`. Перевір порт:

```bash
ss -ltn | grep 5432
```
Якщо service `db` не запущений:

```bash
docker compose up -d db
```
Не видаляй volume або dev DB. Якщо використовується інший порт із `.env`, не
роби висновок лише за `5432`: перевір конфігурацію й фактичну помилку Django.

## Перевірки серверної частини

Запускай команди з розділу `README.md` «Перевірки» без заміни settings або БД:

```bash
backend/.venv/bin/python backend/manage.py check --database default
backend/.venv/bin/python backend/manage.py makemigrations --check --dry-run
cd backend
.venv/bin/python -m pytest
.venv/bin/ruff check .
.venv/bin/ruff format --check .
```
Після блоку повернись до кореня перед іншими командами з відносними шляхами. Для
міграційного або початкового зрізу додатково відтвори команди з «Запуск з нуля»:

```bash
backend/.venv/bin/python backend/manage.py migrate
backend/.venv/bin/python backend/manage.py seed_catalog
```
`seed_catalog` запусти вдруге, якщо зріз змінює seed і треба довести
ідемпотентність.

## Перевірки клієнтської частини

Із `frontend/` виконай точний блок README:

```bash
npm run typecheck
npm run lint
npm test
npm run build
```

Не замінюй повний комплекс одним тестовим файлом. Під час діагностики можна
спочатку запустити вузький тест, але перед статусом Done потрібен повний блок.

## Ручний браузерний E2E

`.claude/launch.json` містить конфігурації попереднього перегляду `backend` і
`frontend`. Якщо попередній перегляд недоступний, запусти два процеси:

```bash
set -a; . ./.env; set +a; backend/.venv/bin/python backend/manage.py runserver localhost:8000
npm --prefix frontend run dev
```

Frontend відкривається на `http://localhost:5173` і проксіює `/api/v1` до
Django; admin — `http://localhost:8000/admin/`. Не звертайся з browser UI до
hardcoded API origin `:8000`.

Застарілий лічильник throttling може дати 429 під час ручної перевірки через
Vite proxy, бо всі запити мають одну IP-адресу. Перезапусти `runserver`, щоб
очистити locmem cache, або підвищ `DJANGO_THROTTLE_LOGIN_IP` у локальному `.env`.

Пройди реальний сценарій, пов’язаний із `UC`, `BR` та REST ID зрізу. Перевір
успіх, валідацію, межу неавторизованого/чужого ресурсу, перезавантаження і
навігацію браузера назад/уперед, якщо вони релевантні. Не називай ручним E2E
лише відкриття головної сторінки.

## Локальний тестовий акаунт

Створи звичайного користувача через реєстраційний UI/API. Для admin за потреби
інтерактивно виконай `backend/.venv/bin/python backend/manage.py createsuperuser`.

Згенеруй випадкові email і пароль у тимчасовий файл поза репозиторієм, у session
scratch або `/tmp`, наприклад:

```bash
credentials_file="$(mktemp /tmp/fitness-e2e-credentials.XXXXXX)"
chmod 600 "$credentials_file"
python3 -c 'import secrets; print(f"email=e2e-{secrets.token_hex(6)}@example.test"); print(f"password={secrets.token_urlsafe(24)}")' > "$credentials_file"
```

Використовуй дані лише проти `localhost`; не додавай значення до чату, Git,
fixtures, `.env`, seed або знімків. Повідом власнику шлях до файла, а не значення.
Після перевірки не додавай тестовий акаунт до `seed_catalog`.
## Якщо DB-тести не запускаються

Не переходь на SQLite і не імітуй PostgreSQL constraints. Зафіксуй точну команду,
код завершення та першу змістовну помилку. Розрізняй: service недоступний,
неправильні змінні `.env`, роль без `CREATEDB`, непридатна міграція або дефект.

Без доступної PostgreSQL можна чесно виконати Ruff і frontend-перевірки, але backend
pytest познач як `NOT RUN`, а не `PASS`. Вкажи, яка перевірка та який доказ
залишилися.

## Звіт про результат

Для кожної команди наведи точну назву, `PASS`/`FAIL`/`NOT RUN`, кількість тестів
із фактичного виводу та ключову помилку. Для E2E наведи сценарій і спостережений
результат без облікових даних. Не стверджуй про успішний комплекс, безпеку
конкурентного доступу, міграцію або стан UI, яких не запускав і не бачив.
