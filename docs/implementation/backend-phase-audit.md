# Аудит фактичної реалізації Django backend

> [!IMPORTANT]
> ### Поточний статус реалізації (Current Implementation Status — 2026-11-14)
> - **Phase 0 (Repository and Tooling):** `COMPLETE` (див. §L).
> - **Phase 1 (Custom User, auth і permissions):** `COMPLETE` (A01–A08, відновлення пароля, UI; див. §M).
> - **Phase 2 (Profile і WeightEntry):** `COMPLETE` (P01–P04, ProfileService, валідація віку, історія ваги; див. §N).
> - **Phase 3 (Shared Catalog і Admin publication):** `COMPLETE` (C01–C04, моделі, atomic publication, seed_catalog; див. §O).
> - **Phase 4 (Selection і персональний склад):** `COMPLETE` (G01–G06, Strategy, персональні копії; див. §P).
> - **Phase 5 (Schedule, activation і reminder core):** `COMPLETE` (G07–G08, S01–S04, N01–N03; див. §Q).
> - **Phases 6–8:** `NOT_STARTED`; S05/G09/E01 свідомо лишаються Phase 7.
> - **Перша незавершена фаза:** **Phase 6 — Execution/Engagement persistence і required policies**.
> *(Нижче збережено оригінальний історичний аудит-бейзлайн від старту робіт; останні підтверджені дані наведено в матриці §B, таблиці §D та розділах верифікації §L–§Q).*

Дата аудиту: 2026-11-01. Обсяг: фактичний стан Phases 0–8; Phases 9–10 розглянуто окремо. Це огляд без змін коду, схеми, даних чи контракту. Статуси нижче стосуються перевіреної реалізації, а не наміру в документації.

Джерела пріоритету: `docs/analysis/requirements.md`, `docs/analysis/business-rules.md`, `docs/architecture/domain-model.md`, `docs/architecture/erd.md`, `docs/architecture/rest-api.md`, `docs/architecture/design-principles.md`, чотиристорінковий `docs/diagrams/class-diagram.drawio`, `docs/implementation/implementation-plan.md`, `README.md`. Межі фаз і DoD взято з `docs/implementation/implementation-plan.md:207-287`. У `docs/architecture/rest-api.md:22-74` тепер **49**, а не 47 операцій: до попередніх 47 додано A07/A08. Позначки CONFIRMED/PROPOSED не прирівнювалися.

## A. Executive Summary

Реалізовано інфраструктурний каркас і частину Phase 1: custom `User`, PostgreSQL-конфігурацію, міграції користувача, A01–A06, базову сесійну авторизацію, CSRF і обмежену дію деактивації в Django Admin. **Жодна фаза не підтверджена як COMPLETE.** Phase 0 — `UNVERIFIED`: system check, lint і smoke-тест працюють, але PostgreSQL, чистий migrate та browser/proxy сценарій нині не підтверджені. Phase 1 — `PARTIAL`: A07/A08, відновлення пароля та його перевірки відсутні; наявні DB-тести не змогли стартувати. Phases 2–8 — `NOT_STARTED`, хоча окремі gate-залежні роботи пізніше залишаються заблокованими рішенням щодо BR-021/022.

**Перша незавершена backend-фаза — Phase 0.** Найближча обмежена задача: відновити доступну локальну PostgreSQL 17 і закрити Phase 0 перевірками чистої ізольованої БД, Django/pytest та Vite proxy/CSRF у браузері; не запускати міграції на існуючій постійній БД в межах аудиту. Перший наступний пакет функціональної розробки після цього — A07/A08 у Phase 1.

## B. Phase Completion Matrix

`✓` = код знайдено; `—` = немає; `?` = є код, виконання не доведено. Статуси використовують лише `COMPLETE`, `PARTIAL`, `NOT_STARTED`, `BLOCKED`, `UNVERIFIED`.

| Phase | Name | Status | Code | API | Database | Tests | Main gaps |
|---|---|---|---|---|---|---|---|
| 0 | Repository and Tooling | COMPLETE *(baseline: UNVERIFIED, див. §L)* | ✓ | routing skeleton ✓ | config ✓, PG 17.11 verified ✓ | 15/15 pytest ✓, FE 12/12 ✓, browser BiDi 7/7 ✓ | Закрито у верифікації 2026-11-01 (§L); історичний baseline збережено нижче. |
| 1 | Custom User, auth і permissions | COMPLETE *(baseline: PARTIAL, див. §L, §M)* | A01–A08 ✓, reset UI ✓ | 8/8 маршрутів ✓ (A01–A08 verified) | User/0001/0002 ✓, clean migrate ✓ | 25/25 pytest ✓, FE 17/17 ✓, browser BiDi 9/9 ✓ | Закрито у верифікації 2026-11-01 (§M); історичний baseline збережено нижче. |
| 2 | Profile і WeightEntry | COMPLETE *(baseline: NOT_STARTED, див. §N)* | Profile, WeightEntry, ProfileService, selectors ✓ | 4/4 маршрути ✓ (P01–P04 verified) | accounts.0003_profile_weightentry ✓, clean migrate + CHECK/Index ✓ | 70/70 pytest ✓ (45 у `test_profile.py`), FE 17/17 ✓ | Закрито у верифікації 2026-11-01 (§N); P05 відноситься до Phase 8. |
| 3 | Shared Catalog і Admin publication | COMPLETE *(baseline: NOT_STARTED, див. §O)* | Exercise, Workout, WorkoutExercise, ProgramTemplate, ProgramTemplateWorkout, CatalogPublicationService, seed_catalog ✓ | 4/4 маршрути ✓ (C01–C04 verified) | catalog.0001_initial ✓, clean migrate + CHECK/Unique/Index + PROTECT ✓ | 118/118 pytest ✓ (48 у `catalog/tests/`), FE 17/17 ✓, ruff 0 errors ✓ | Закрито у верифікації 2026-11-01 (§O); Phase 4 selection strategy tests готові до старту. |
| 4 | Selection і персональний склад | COMPLETE *(baseline: NOT_STARTED, див. §P)* | Strategy, UserProgram/deep copy ✓ | 6/6 | planning.0001/0002 ✓ | 172/172 backend на момент Phase 4 ✓ | Закрито у §P. |
| 5 | Schedule, activation і reminder core | COMPLETE *(baseline: NOT_STARTED, див. §Q)* | policies/selectors/services, React schedule/notifications ✓ | 9/9 | planning.0003, 13/20 ERD tables ✓ | 225 backend ✓; frontend 61/61 ✓ | S05/G09/E01 не входять до Phase 5. |
| 6 | Execution/Engagement persistence і required policies | NOT_STARTED | app shells | 0/3 H | — | — | Незалежні схема/політики не початі; BR-021/022 gate блокує залежні evaluator/handlers/H01–H03. |
| 7 | E01, S05 і G09 atomic scenarios | NOT_STARTED | — | 0/3 | — | — | Немає сервісів, транзакційних інваріантів і PostgreSQL race evidence; E01 додатково залежить від gate. |
| 8 | Read APIs, statistics, reports і leaderboard | NOT_STARTED | reporting shell | 0/12 | — | — | Немає проєкцій, приватних звітів, Django Admin report pages і REST R02/R03. |

Phase 9: React/Vite foundation існує (`frontend/vite.config.ts:6-25`), але наскрізні вертикальні сценарії на всіх API неможливі, бо backend Phases 2–8 ще відсутні. Це не аудит якості frontend. Phase 10: clean PostgreSQL migrate+seed, повні quality gates, E2E, concurrency, privacy та три звіти не доведені (`docs/implementation/implementation-plan.md:282-287`).

## C. Detailed Phase Findings

### Phase 0 — Repository and Tooling — UNVERIFIED

- **Implemented:** `backend/manage.py`, розділені settings (`backend/config/settings/base.py:15-112`, `local.py:9-20`, `test.py:1-8`, `production.py:7-17`), DRF/default session auth, PostgreSQL engine, pinned `backend/requirements.txt`, `backend/requirements-dev.lock`, `.env.example`, optional PostgreSQL 17 `compose.yaml:1-15`, `README.md`, Vite proxy `frontend/vite.config.ts:13-23`, pytest/ruff config `backend/pyproject.toml:1-13`.
- **Missing:** за оглядом файлів обов'язковий Phase 0 source component не відсутній; Docker Compose optional за планом. Окремого доведеного clean-checkout startup немає.
- **Defects:** підтвердженого дефекту коду Phase 0 не виявлено.
- **Unverified:** PostgreSQL connection, застосовані міграції, чисте встановлення, frontend typecheck/build саме в цьому аудиті, browser same-origin `/api/v1/*` cookies/CSRF. `showmigrations --plan` не під'єднався до 127.0.0.1:5432; Docker Desktop socket недоступний.
- **DoD (`implementation-plan.md:211-216`):** Django system check — пройшов; порожній/DB-free test runner — пройшов (1 тест); dependency manifests і конфігурація — наявні; frontend build, PostgreSQL connection, browser proxy/CSRF та clean checkout — не доведені. Отже COMPLETE за правилами аудиту неможливий.
- **Evidence:** `backend/config/api_urls.py:5`, `backend/tests/test_smoke.py:1-20`, `compose.yaml:4-12`, `frontend/vite.config.ts:17-23`; результати команд — §H.

### Phase 1 — Custom User, auth і permissions — PARTIAL

- **Implemented:** `User` і DB constraints (`backend/accounts/models.py:11-37`), manager/email auth (`backend/accounts/managers.py:7-27`, `backend/accounts/authentication.py:6-28`), міграції 0001/0002, A01–A06 routes (`backend/accounts/urls.py:5-10`) та views (`backend/accounts/views.py:23-100`), обмежена Admin-деактивація (`backend/accounts/admin.py:23-62`), whitelist-поля/password validation (`backend/accounts/serializers.py:10-58`), error envelope (`backend/accounts/errors.py:15-23,58-90`). Registration захищено `csrf_protect` і `transaction.atomic`; login має guest CSRF, logout завершує session; A06 блокує порожній alias при opt-in. Це інспекція коду, не успішна PostgreSQL інтеграція.
- **Missing:** A07/A08, `PasswordResetService`, email backend/timeout/throttling для відновлення, відповідні backend/frontend reset тести й UI. Загального owner-selector helper для наступних приватних ID ресурсів поки немає; він не потрібен для A05/A06, що працюють з `request.user`. Administrator group provisioning не автоматизовано; README описує ручне створення.
- **Defects:** доведеного порушення A01–A06 за code review немає. Відсутність A07/A08 — прогалина поточної Phase 1, не дефект наявних маршрутів.
- **Unverified:** 14 DB тестів A01–A06 не виконали тіло через недоступну test database; browser proxy, role 403 і deactivation на працюючому PostgreSQL теж не перевірено цим аудитом. Статуси/JSON перевірялися статично, не HTTP на живому сервері.
- **DoD (`implementation-plan.md:218-223`):** custom User, secure password handling, базовий CSRF/session/admin код і A01–A06 — source evidence є; clean migrate/DB tests/browser proxy — не доведені; A07/A08/reset tests — відсутні. Phase 1 `PARTIAL` незалежно від DB outage.
- **Evidence:** `backend/accounts/tests/test_auth.py:23-347`, `backend/accounts/urls.py:5-10`, `backend/config/settings/base.py:75-106`, `docs/analysis/requirements.md` FR-042, `docs/analysis/business-rules.md` BR-035.

### Phase 2 — Profile і WeightEntry — NOT_STARTED

- **Implemented:** лише `accounts` як app і `User`; Profile/WeightEntry не існують.
- **Missing:** ProfileService, сім фітнес-полів, optional names, датована immutable WeightEntry, P01–P04, owner selectors, міграція, тести.
- **Defects:** немає реалізованого Phase 2 сценарію для оцінки дефекту.
- **Unverified:** немає коду Phase 2 для runtime перевірки.
- **DoD (`implementation-plan.md:225-230`):** усі профільні критерії (імена, вік, Decimal, atomic weight, приватність, сортування) незадоволені. P05 належить Phase 8.
- **Evidence:** єдині backend моделі `backend/accounts/models.py:11-40`; міграції `backend/accounts/migrations/0001_initial.py:10-43`, `0002_remove_user_users_opt_in_alias_required_and_more.py:15-23`; лише accounts routes `backend/config/api_urls.py:5`.

### Phase 3 — Shared Catalog і Admin publication — NOT_STARTED

- **Implemented:** `backend/catalog/apps.py` як оболонка app.
- **Missing:** Exercise/Workout/ProgramTemplate та склади, catalog migration, publication validation, Admin inlines, seed, C01–C04 read-only routes/selectors, tests.
- **Defects:** немає реалізованого сценарію.
- **Unverified:** немає runtime-функцій для перевірки.
- **DoD (`implementation-plan.md:232-237`):** published parent+inlines atomicity, валідність складу, hidden/archive behavior, повторюваний seed і три парні шаблони не реалізовані.
- **Evidence:** `backend/catalog/apps.py:1-5`, `backend/config/settings/base.py:29`, `backend/config/api_urls.py:5`.

### Phase 4 — Selection і персональний склад — NOT_STARTED

- **Implemented:** `backend/planning/apps.py` як оболонка.
- **Missing:** planning.0001, три Strategy, ProgramSelection/Planning services, UserProgram та копійований склад, G01–G06, тести й frontend slice.
- **Defects:** немає реалізованого сценарію.
- **Unverified:** алгоритм добору, deep copy/rollback і блокування не можуть перевірятися без коду.
- **DoD (`implementation-plan.md:239-244`):** exact goal/level/frequency, stable candidate selection, no candidate, копія, G06 membership/owner/state/immutable source — усі не виконані.
- **Evidence:** `backend/planning/apps.py:1-5`, `backend/config/api_urls.py:5`.

### Phase 5 — Schedule, activation і reminder core — NOT_STARTED

- **Implemented:** лише оболонка planning app.
- **Missing:** planning.0002, ScheduledSession/Notification, ReminderService, G07/G08, S01–S04, N01–N03, calendar/reminder tests.
- **Defects:** немає реалізованого сценарію.
- **Unverified:** UTC/Kyiv, видимість, read-only GET і rollback не можна перевірити без коду.
- **DoD (`implementation-plan.md:246-251`):** frozen target, atomic slot/reminder, ID preservation, N01/N02 privacy, repeated read_at — усі не виконані. S05/G09 правильно віднесені до Phase 7 і не є критерієм Phase 5.
- **Evidence:** `backend/planning/apps.py:1-5`, `backend/config/api_urls.py:5`.

### Phase 6 — Execution/Engagement persistence і required policies — NOT_STARTED

- **Implemented:** app shells `backend/execution/apps.py`, `backend/engagement/apps.py`.
- **Missing:** CompletedSession/ExerciseResult, PointTransaction/definitions/participations, migrations, CaloriesEstimator, PointsPolicy, event/required-handler framework, PostgreSQL integrity tests. Залежні від gate evaluator/handler, production seed і H01–H03 теж відсутні.
- **Defects:** немає реалізованого сценарію.
- **Unverified:** немає моделі/політик для тестування.
- **DoD (`implementation-plan.md:253-259`):** незалежні FK/UQ/CHECK, XOR ledger, bonus uniqueness, MET priority, age>60, points bounds не виконані. BR-021/022 лишаються `PROPOSED` (`business-rules.md:87-88`); Business Decision Gate не закритий, тому **залежну частину не реалізовувати на прикладах**. E01 за планом Phase 7, його відсутність сама по собі не причина статусу Phase 6.
- **Evidence:** `backend/config/settings/base.py:31-32`, `backend/config/api_urls.py:5`, `docs/implementation/implementation-plan.md:253-259`.

### Phase 7 — E01, S05 і G09 atomic scenarios — NOT_STARTED

- **Implemented:** нічого у Phase 7.
- **Missing:** WorkoutCompletionService, Template Method processors, dispatcher/handlers, shared program-completion operation, E01/S05/G09, idempotency, locks, snapshots, ledger/bonus, rollback і race tests.
- **Defects:** немає реалізованого сценарію.
- **Unverified:** транзакційні гарантії AR-01–AR-04 не можуть бути продемонстровані.
- **DoD (`implementation-plan.md:261-266`):** committed retry, conflict, no double points, frozen target, S05 repeat, G09 rules, required rollback, immutable history, concurrent connections — нічого не виконано. Публікація E01 залежить і від Phases 4–6, і від погоджених required handlers після gate.
- **Evidence:** `backend/config/api_urls.py:5`, `docs/analysis/business-rules.md:30-33`, `docs/implementation/implementation-plan.md:263-266`.

### Phase 8 — Read APIs, statistics, reports і leaderboard — NOT_STARTED

- **Implemented:** `backend/reporting/__init__.py` є лише package marker; reporting не має Django app/views/queries.
- **Missing:** P05, E02/E03, M01–M04, H04, L01, R01–R03, permissions, aggregation/query services, Django Admin report pages, tests. R02/R03 за контрактом залишаються захищеними REST операціями **додатково** до адмін-інтерфейсу; ні одне, ні інше не реалізовано.
- **Defects:** немає реалізованого сценарію.
- **Unverified:** Kyiv DST, нульові знаменники, архівні джерела, deactivated users, opt-in privacy, read-only GET неможливо перевірити без коду.
- **DoD (`implementation-plan.md:268-273`):** усі projection/report/privacy критерії незадоволені. M03/M04/H04 залежні від BR-021/022 gate.
- **Evidence:** `backend/reporting/__init__.py:1`, `backend/config/settings/base.py:20-33`, `backend/config/api_urls.py:5`, `docs/architecture/rest-api.md:60-74`.

## D. REST API Coverage

Стан **49** операцій, згідно з чинним `docs/architecture/rest-api.md:22-74`. У старій постановці було 47 без A07/A08; чинний документ включає їх у той самий інвентар. `IMPLEMENTED_UNVERIFIED` означає URL+view+статичний огляд, але без DB-backed HTTP перевірки. `BLOCKED` застосовано до операцій, які безпосередньо залежать від незакритого BR-021/022 gate; решта відсутніх маршрутів — `MISSING`. `—` у View/Service/Tests означає, що реалізації немає. Для всіх відсутніх маршрутів фактична реєстрація обмежена `backend/config/api_urls.py:5`.

| ID | Method | URL | Phase | View | Service | Tests | Status | Evidence |
|---|---|---|---:|---|---|---|---|---|
| A01 | GET | `/api/v1/auth/csrf/` | 1 | CsrfView | inline | pytest + live Vite proxy + Firefox BiDi | IMPLEMENTED_AND_VERIFIED *(baseline: IMPLEMENTED_UNVERIFIED)* | `backend/accounts/urls.py:6`; `backend/accounts/views.py:23-27`; §L |
| A02 | POST | `/api/v1/auth/register/` | 1 | RegisterView | inline | pytest + live Vite proxy + Firefox BiDi | IMPLEMENTED_AND_VERIFIED *(baseline: IMPLEMENTED_UNVERIFIED)* | `backend/accounts/urls.py:7`; `backend/accounts/views.py:30-49`; §L |
| A03 | POST | `/api/v1/auth/login/` | 1 | LoginView | inline | pytest + live Vite proxy + Firefox BiDi | IMPLEMENTED_AND_VERIFIED *(baseline: IMPLEMENTED_UNVERIFIED)* | `backend/accounts/urls.py:8`; `backend/accounts/views.py:52-67`; §L |
| A04 | POST | `/api/v1/auth/logout/` | 1 | LogoutView | inline | pytest + live Vite proxy + Firefox BiDi | IMPLEMENTED_AND_VERIFIED *(baseline: IMPLEMENTED_UNVERIFIED)* | `backend/accounts/urls.py:9`; `backend/accounts/views.py:70-75`; §L |
| A05 | GET | `/api/v1/me/` | 1 | MeView | inline | pytest + live Vite proxy + Firefox BiDi | IMPLEMENTED_AND_VERIFIED *(baseline: IMPLEMENTED_UNVERIFIED)* | `backend/accounts/urls.py:10`; `backend/accounts/views.py:78-82`; §L |
| A06 | PATCH | `/api/v1/me/` | 1 | MeView | inline | pytest + live Vite proxy + Firefox BiDi | IMPLEMENTED_AND_VERIFIED *(baseline: IMPLEMENTED_UNVERIFIED)* | `backend/accounts/urls.py:17`; `backend/accounts/views.py:92-112`; §L |
| A07 | POST | `/api/v1/auth/password-reset/` | 1 | PasswordResetRequestView | PasswordResetService.request_reset | pytest + Vitest + Firefox BiDi | IMPLEMENTED_AND_VERIFIED *(baseline: MISSING)* | `backend/accounts/urls.py:18-22`; `backend/accounts/views.py:115-128`; `backend/accounts/services.py:22-53`; §M |
| A08 | POST | `/api/v1/auth/password-reset/confirm/` | 1 | PasswordResetConfirmView | PasswordResetService.confirm_reset | pytest + Vitest + Firefox BiDi | IMPLEMENTED_AND_VERIFIED *(baseline: MISSING)* | `backend/accounts/urls.py:23-27`; `backend/accounts/views.py:131-146`; `backend/accounts/services.py:55-82`; §M |
| P01 | GET | `/api/v1/profile/` | 2 | ProfileView | ProfileService.get_profile | pytest (`test_profile.py`) | IMPLEMENTED_AND_VERIFIED *(baseline: MISSING)* | `backend/accounts/urls.py:30`; `backend/accounts/views.py:165-172`; `backend/accounts/services.py:124-128`; §N |
| P02 | POST | `/api/v1/profile/` | 2 | ProfileView | ProfileService.create_profile | pytest (`test_profile.py`) | IMPLEMENTED_AND_VERIFIED *(baseline: MISSING)* | `backend/accounts/urls.py:30`; `backend/accounts/views.py:174-180`; `backend/accounts/services.py:131-165`; §N |
| P03 | PATCH | `/api/v1/profile/` | 2 | ProfileView | ProfileService.update_profile | pytest (`test_profile.py`) | IMPLEMENTED_AND_VERIFIED *(baseline: MISSING)* | `backend/accounts/urls.py:30`; `backend/accounts/views.py:182-190`; `backend/accounts/services.py:168-199`; §N |
| P04 | GET | `/api/v1/weight-entries/` | 2 | WeightEntryListView | list_user_weight_entries | pytest (`test_profile.py`) | IMPLEMENTED_AND_VERIFIED *(baseline: MISSING)* | `backend/accounts/urls.py:31`; `backend/accounts/views.py:193-245`; `backend/accounts/selectors.py:22-32`; §N |
| P05 | GET | `/api/v1/statistics/weight-chart/` | 8 | — | — | — | MISSING | `docs/architecture/rest-api.md:38`; `backend/config/api_urls.py:5` |
| C01 | GET | `/api/v1/categories/` | 3 | CategoryListView | list_categories | pytest (`test_api.py`) | IMPLEMENTED_AND_VERIFIED *(baseline: MISSING)* | `backend/catalog/urls.py:13`; `backend/catalog/views.py:78-90`; `backend/catalog/selectors.py:9-14`; §O |
| C02 | GET | `/api/v1/exercises/` | 3 | ExerciseListView | list_active_exercises | pytest (`test_api.py`) | IMPLEMENTED_AND_VERIFIED *(baseline: MISSING)* | `backend/catalog/urls.py:14`; `backend/catalog/views.py:93-112`; `backend/catalog/selectors.py:17-28`; §O |
| C03 | GET | `/api/v1/workouts/` | 3 | WorkoutListView | list_active_workouts | pytest (`test_api.py`) | IMPLEMENTED_AND_VERIFIED *(baseline: MISSING)* | `backend/catalog/urls.py:15`; `backend/catalog/views.py:115-134`; `backend/catalog/selectors.py:31-44`; §O |
| C04 | GET | `/api/v1/workouts/{id}/` | 3 | WorkoutDetailView | get_active_workout_detail | pytest (`test_api.py`) | IMPLEMENTED_AND_VERIFIED *(baseline: MISSING)* | `backend/catalog/urls.py:16-20`; `backend/catalog/views.py:137-148`; `backend/catalog/selectors.py:47-62`; §O |
| G01 | GET | `/api/v1/program-recommendation/` | 4 | ProgramRecommendationView | ProgramSelectionService | pytest | IMPLEMENTED_AND_VERIFIED | `backend/planning/urls.py`; §P |
| G02 | GET | `/api/v1/user-programs/` | 4 | UserProgramListCreateView | selectors/service | pytest | IMPLEMENTED_AND_VERIFIED | `backend/planning/urls.py`; §P |
| G03 | POST | `/api/v1/user-programs/` | 4 | UserProgramListCreateView | ProgramSelectionService | pytest | IMPLEMENTED_AND_VERIFIED | `backend/planning/urls.py`; §P |
| G04 | GET | `/api/v1/user-programs/{id}/` | 4 | UserProgramDetailView | selectors/service | pytest | IMPLEMENTED_AND_VERIFIED | `backend/planning/urls.py`; §P |
| G05 | PATCH | `/api/v1/user-programs/{id}/` | 4 | UserProgramDetailView | ProgramPlanningService | pytest | IMPLEMENTED_AND_VERIFIED | `backend/planning/urls.py`; §P |
| G06 | PUT | `/api/v1/user-programs/{id}/workouts/{entry_id}/` | 4 | UserProgramWorkoutCompositionView | ProgramPlanningService | pytest | IMPLEMENTED_AND_VERIFIED | `backend/planning/urls.py`; §P |
| G07 | POST | `/api/v1/user-programs/{id}/activate/` | 5 | UserProgramActivateView | ProgramPlanningService | `test_phase5_api.py` | IMPLEMENTED_AND_VERIFIED | `backend/planning/urls.py`; §Q |
| G08 | GET | `/api/v1/user-programs/{id}/progress/` | 5 | UserProgramProgressView | ProgramPlanningService + selectors | `test_phase5_api.py` | IMPLEMENTED_AND_VERIFIED | `backend/planning/urls.py`; §Q |
| G09 | POST | `/api/v1/user-programs/{id}/archive/` | 7 | — | — | — | MISSING | `docs/architecture/rest-api.md:51`; `backend/config/api_urls.py:5` |
| S01 | GET | `/api/v1/scheduled-sessions/` | 5 | ScheduledSessionListCreateView | selectors | `test_phase5_api.py` | IMPLEMENTED_AND_VERIFIED | `backend/planning/urls.py`; §Q |
| S02 | POST | `/api/v1/scheduled-sessions/` | 5 | ScheduledSessionListCreateView | ProgramPlanningService + ReminderService | `test_phase5_api.py` | IMPLEMENTED_AND_VERIFIED | `backend/planning/urls.py`; §Q |
| S03 | GET | `/api/v1/scheduled-sessions/{id}/` | 5 | ScheduledSessionDetailView | ProgramPlanningService | `test_phase5_api.py` | IMPLEMENTED_AND_VERIFIED | `backend/planning/urls.py`; §Q |
| S04 | PATCH | `/api/v1/scheduled-sessions/{id}/` | 5 | ScheduledSessionDetailView | ProgramPlanningService + ReminderService | `test_phase5_api.py` | IMPLEMENTED_AND_VERIFIED | `backend/planning/urls.py`; §Q |
| S05 | POST | `/api/v1/scheduled-sessions/{id}/cancel/` | 7 | — | — | — | MISSING | `docs/architecture/rest-api.md:56`; `backend/config/api_urls.py:5` |
| E01 | POST | `/api/v1/completed-sessions/` | 7 | — | — | — | BLOCKED | `docs/architecture/rest-api.md:57`; `docs/implementation/implementation-plan.md:263-266` |
| E02 | GET | `/api/v1/completed-sessions/` | 8 | — | — | — | MISSING | `docs/architecture/rest-api.md:58`; `backend/config/api_urls.py:5` |
| E03 | GET | `/api/v1/completed-sessions/{id}/` | 8 | — | — | — | MISSING | `docs/architecture/rest-api.md:59`; `backend/config/api_urls.py:5` |
| M01 | GET | `/api/v1/points/summary/` | 8 | — | — | — | MISSING | `docs/architecture/rest-api.md:60`; `backend/config/api_urls.py:5` |
| M02 | GET | `/api/v1/point-transactions/` | 8 | — | — | — | MISSING | `docs/architecture/rest-api.md:61`; `backend/config/api_urls.py:5` |
| M03 | GET | `/api/v1/achievements/` | 8 | — | — | — | BLOCKED | `docs/architecture/rest-api.md:62`; `docs/analysis/business-rules.md:87` |
| M04 | GET | `/api/v1/user-achievements/` | 8 | — | — | — | BLOCKED | `docs/architecture/rest-api.md:63`; `docs/analysis/business-rules.md:87` |
| H01 | GET | `/api/v1/challenges/` | 6 | — | — | — | BLOCKED | `docs/architecture/rest-api.md:64`; `docs/analysis/business-rules.md:88` |
| H02 | GET | `/api/v1/challenges/{id}/` | 6 | — | — | — | BLOCKED | `docs/architecture/rest-api.md:65`; `docs/analysis/business-rules.md:88` |
| H03 | POST | `/api/v1/challenges/{id}/join/` | 6 | — | — | — | BLOCKED | `docs/architecture/rest-api.md:66`; `docs/analysis/business-rules.md:88` |
| H04 | GET | `/api/v1/challenge-participations/` | 8 | — | — | — | BLOCKED | `docs/architecture/rest-api.md:67`; `docs/analysis/business-rules.md:88` |
| L01 | GET | `/api/v1/leaderboard/` | 8 | — | — | — | MISSING | `docs/architecture/rest-api.md:68`; `backend/config/api_urls.py:5` |
| N01 | GET | `/api/v1/notifications/` | 5 | NotificationListView | selectors | `test_phase5_api.py` | IMPLEMENTED_AND_VERIFIED | `backend/planning/urls.py`; §Q |
| N02 | GET | `/api/v1/notifications/{id}/` | 5 | NotificationDetailView | selectors | `test_phase5_api.py` | IMPLEMENTED_AND_VERIFIED | `backend/planning/urls.py`; §Q |
| N03 | POST | `/api/v1/notifications/{id}/read/` | 5 | NotificationReadView | ReminderService | `test_phase5_api.py` | IMPLEMENTED_AND_VERIFIED | `backend/planning/urls.py`; §Q |
| R01 | GET | `/api/v1/statistics/overview/` | 8 | — | — | — | MISSING | `docs/architecture/rest-api.md:72`; `backend/config/api_urls.py:5` |
| R02 | GET | `/api/v1/reports/workout-popularity/` | 8 | — | — | — | MISSING | `docs/architecture/rest-api.md:73`; `backend/config/api_urls.py:5` |
| R03 | GET | `/api/v1/reports/average-activity/` | 8 | — | — | — | MISSING | `docs/architecture/rest-api.md:74`; `backend/config/api_urls.py:5` |

Підсумок первинної ревізії (baseline): **49 = 0 IMPLEMENTED_AND_VERIFIED + 6 IMPLEMENTED_UNVERIFIED + 0 PARTIAL + 36 MISSING + 7 BLOCKED**. Після закриття інфраструктурного гейту Phase 0 (§L): **49 = 6 IMPLEMENTED_AND_VERIFIED + 0 IMPLEMENTED_UNVERIFIED + 0 PARTIAL + 36 MISSING + 7 BLOCKED**. Після завершення Phase 1 (§M): **49 = 8 IMPLEMENTED_AND_VERIFIED + 0 IMPLEMENTED_UNVERIFIED + 0 PARTIAL + 34 MISSING + 7 BLOCKED**. Після завершення Phase 2 (§N): **49 = 12 IMPLEMENTED_AND_VERIFIED + 0 IMPLEMENTED_UNVERIFIED + 0 PARTIAL + 30 MISSING + 7 BLOCKED**. Після Phase 4 (§P) і Phase 5 (§Q) поточний стан: **31 IMPLEMENTED_AND_VERIFIED з 49**; S05/G09/E01 фізично не опубліковані. Блоковані маршрути також фізично відсутні; `BLOCKED` вказує на необхідне бізнес-рішення, а не на наявність placeholder implementation.

## E. Database and Migration Status

`AUTH_USER_MODEL = "accounts.User"` (`backend/config/settings/base.py:85`) встановлено до залежних доменних міграцій. PostgreSQL engine та змінні підключення — `backend/config/settings/base.py:64-73`. `User` має `UNIQUE(LOWER(email))` і CHECK opt-in alias (`backend/accounts/models.py:24-36`), а також окремий permission `deactivate_user`. `backend/accounts/migrations/0001_initial.py:10-43` створює User; `0002_remove_user_users_opt_in_alias_required_and_more.py:15-23` замінює CHECK. Інших app migrations або domain models немає. Прикладні FK/UQ/CHECK/index для Profile, catalog, planning, execution, engagement відсутні разом з відповідними моделями; не слід оцінювати їх як defect вже реалізованої схеми.

`makemigrations --check --dry-run` повідомив `No changes detected`, але попередив, що не зміг перевірити migration history через PostgreSQL. Це лише відсутність виявленого model-to-migration drift у доступному коді. `showmigrations --plan` завершився помилкою підключення; applied state, чистий migrate, PostgreSQL constraints/locks/transaction behavior не підтверджені. Міграції не застосовувалися, development data не змінювалися. Наявний `compose.yaml:1-15` з локальним Postgres 17; Docker Desktop daemon під час аудиту не працював.

## F. GoF / SOLID / GRASP and Requirement Traceability

| Principle/pattern | Документований намір | Фактичний стан | Тестовий доказ |
|---|---|---|---|
| Strategy | Три interchangeable selection strategies, Phase 4 (`implementation-plan.md:242-244`) | Немає selection service/strategies у `backend/planning` | Немає |
| Observer | Локальний WorkoutCompleted dispatcher з required/optional handlers, Phases 6–7 (`implementation-plan.md:256,264`) | Немає dispatcher/handlers у `backend/execution` або `backend/engagement` | Немає |
| Template Method | Processors фактичних ExerciseResult, Phase 7 (`implementation-plan.md:264`) | Немає processors у `backend/execution` | Немає |
| SOLID/GRASP | Django modular monolith, вузькі app/service відповідальності (`docs/architecture/design-principles.md`) | Accounts має відокремлені serializer, view, manager, auth backend; доменні app лише оболонки. Виміряти відповідальність майбутніх сервісів неможливо | DB-тести auth існують, не виконалися |

Немає підстав зараховувати UML/design-декларації як виконані GoF патерни. У наявному auth slice не знайдено підтвердженого дублювання бізнес-логіки, прихованих signal/save side effects, GET-запису або витоку через чужий object ID. Domain ownership та privacy досі не реалізовані й не перевірені.

| Requirement / decision | Phase | Implementation | Test evidence | Status | Gap |
|---|---:|---|---|---|---|
| FR-001, FR-002; registration/session | 1 | `accounts/views.py:23-75` | `accounts/tests/test_auth.py:58-218`, DB unavailable | IMPLEMENTED_UNVERIFIED | Живий HTTP/PG не перевірено |
| FR-005, BR-028/032; auth/role/deactivation | 1 | `accounts/admin.py:23-62`, `base.py:75-106` | `accounts/tests/test_auth.py:219-347`, DB unavailable | PARTIAL | Лише current-user і Admin; owner ID helper потрібен у подальших фазах |
| FR-028/035, BR-017; alias/opt-in | 1, 8 | `accounts/models.py:16-36`, A06 | `accounts/tests/test_auth.py` DB unavailable | PARTIAL | L01 та opt-in privacy ще немає |
| FR-042, BR-035; recovery | 1 | — | — | MISSING | A07/A08, token/email/throttle/CSRF/reset UX |
| FR-003/004, BR-001/019/034; profile/weight | 2, 8 | — | — | MISSING | P01–P05, Profile/WeightEntry |
| FR-006–010, BR-002–005; catalog | 3 | — | — | MISSING | C01–C04, Admin publication/seed |
| FR-011–016, BR-005/006/007/009; program | 4–5, 7 | — | — | MISSING | G01–G09, frozen target, deep copy |
| FR-017/023–026, BR-023–026; schedule/reminder | 5, 7 | — | — | MISSING | S01–S05/N01–N03, timezone/atomicity |
| FR-018–022/030, BR-010–016/029/030; completion/ledger | 6–8 | — | — | MISSING | E01–E03, immutable snapshots/ledger |
| AR-01–AR-04, D-2026-10-31; completion/cancel/archive concurrency | 7 | — | — | MISSING | E01/S05/G09 shared locks, retries, rollback, race tests |
| BR-021/022 `PROPOSED`; achievement/challenge criteria | 6–8 | — | — | BLOCKED | Gate не закрито; не схвалено threshold/period/join/progress, production seed/handlers/H/M reads не створювати за прикладами |
| FR-028/031–035/040; leaderboard/reports | 8 | — | — | MISSING | P05/L01/R01–R03, privacy/DST/aggregates |

BR-021/022 **залишаються PROPOSED** у `docs/analysis/business-rules.md:87-88`; явного погодження й оновлення авторитетного BR-документа не знайдено. За `implementation-plan.md:256-259` незалежну схему/політики Phase 6 можна розробляти до gate, але evaluator, required Achievement/Challenge handlers, production seed, H01–H03, а далі E01 та залежні read APIs не можна оголошувати готовими. Текст BR містить приклади, що не є затвердженими порогами.

## G. Security and Permissions

Наявні controls: default session auth і `IsAuthenticated` (`backend/config/settings/base.py:75-83`), CSRF middleware та explicit guest register/login protection (`base.py:35-43`, `accounts/views.py:30-31,52-53`), cookie flags `HttpOnly` для session і `SameSite=Lax` (`base.py:100-106`), production Secure/SSL redirect (`production.py:14-17`), password validators (`base.py:90-99`), case-insensitive email identity DB uniqueness (`accounts/models.py:27`), opt-in alias CHECK (`models.py:28-35`), admin permission/deactivation limits (`accounts/admin.py:23-62`), uniform DRF error envelope (`accounts/errors.py:58-90`). Тести на CSRF, session rotation/logout, inactive account та admin perms є, але не виконалися через DB. `CsrfView` GET лише видає token; у `MeView` GET відповідає поточному користувачеві, а PATCH застосовує row lock (`accounts/views.py:78-100`).

Немає API для чужих приватних ID, тому cross-user `404` не був емпірично перевірений і не слід стверджувати наявний витік. Немає Profile/WeightEntry/history/leaderboard/reporting API, тому privacy та admin-only aggregates є майбутніми вимогами, не чинним порушенням наявного endpoint. A07/A08 потребуватимуть anti-enumeration, throttling, одноразових/expired токенів та CSRF тестів. Для R02/R03 окремий admin permission має перевірятися на REST і Django Admin; `is_staff` сам по собі недостатній (`implementation-plan.md:311`).

## H. Automated Tests and Executable Checks

Перевірка виконана в локальному `backend/.venv`; pytest settings — `config.settings.test` (`backend/pyproject.toml:1-4`) з PostgreSQL engine (`base.py:64-73`). Під час тестів pytest-django намагався створити окрему test database (окреме `TEST.NAME` не задане; Django за замовчуванням використовує `test_` + ім'я основної БД), але не під'єднався до серверу; **ізоляція за механізмом pytest-django передбачена, фактичне створення test DB не підтверджене**. Ні один тест не отримав доступ до постійних даних. Перед backend-командами змінні завантажено через `set -a; . .env; set +a` з кореня репозиторію або `set -a; . ../.env; set +a` з `backend`. Значення секретів не записані в звіт.

| Command | Exit | Collected / passed / failed / skipped | PostgreSQL | Result |
|---|---:|---|---|---|
| `backend/.venv/bin/python backend/manage.py check` | 0 | n/a | ні | `System check identified no issues (1 silenced)`; silenced `auth.W004` обґрунтовано custom email constraint (`base.py:87-89`). |
| `backend/.venv/bin/python backend/manage.py makemigrations --check --dry-run` | 0 | n/a | connection attempt failed | `No changes detected`; migration history не перевірена через warning. |
| `backend/.venv/bin/python backend/manage.py showmigrations --plan` | 1 | n/a | ні | `connection refused` на `127.0.0.1:5432`; applied migrations невідомі. |
| `backend/.venv/bin/ruff check backend` | 0 | n/a | ні | `All checks passed!` |
| `backend/.venv/bin/ruff format --check backend` | 0 | n/a | ні | `34 files already formatted` |
| `cd backend && set -a && . ../.env && set +a && .venv/bin/python -m pytest -q --tb=no` | 1 | **15 / 1 / 0 assertions / 0 skipped; 14 setup errors** | ні | `tests/test_smoke.py` пройшов; усі `accounts/tests/test_auth.py` зупинилися на створенні PostgreSQL test DB (`psycopg.OperationalError`). |
| `docker ps --format ...` | 1 | n/a | ні | Docker Desktop socket не існує; daemon недоступний. |

`pytest` команди були запущені один раз із правильним `../.env`; перший пробний запуск із backend cwd помилково шукав `./.env` і дав той самий клас DB setup errors, тому його не зараховано окремим доказом. `pytest` не має test failures у тілі тестів — лише setup errors. Не запускалися migration-from-zero, PostgreSQL concurrency/rollback, HTTP/browser proxy, frontend build/typecheck, manual reports: середовище/відсутня реалізація не дозволяли meaningful verification у межах цього backend аудиту. Встановлення залежностей та зміни БД не виконувалися.

## I. Critical Gaps

| Severity | Finding | Impact / evidence |
|---|---|---|
| HIGH | Не можна підтвердити PostgreSQL execution gate та застосування міграцій | Тестова БД не створюється, 14 auth tests setup errors; `showmigrations` не працює (§H). Це blocker доказу, а не доказ несправності коду. Підтверджених CRITICAL дефектів чинного коду не виявлено. |
| HIGH | Phase 1 recovery не реалізовано | A07/A08 включені до чинних 49 і Phase 1 DoD (`implementation-plan.md:221-223`); користувач не може відновити пароль. |
| HIGH | Відсутні Phases 2–8 domain APIs/models | Немає Profile/catalog/planning/execution/engagement/reporting backend функцій; `backend/config/api_urls.py:5` включає лише accounts. Це обсяг невиконаної дорожньої карти, а не дефект існуючої реалізації. |
| HIGH | BR-021/022 gate не закритий | Блокує залежні criteria/seed/handlers/H і E01 publication (`business-rules.md:87-88`, `implementation-plan.md:256-265`). |
| MEDIUM | Browser same-origin/proxy CSRF smoke не задокументовано результатом цього аудиту | Phase 0/1 DoD неможливо закрити з поточними виконаними перевірками (`implementation-plan.md:216,223`). |
| MEDIUM | Немає test evidence transactional/race/privacy/reporting | Відповідні фази ще не реалізовано; Phase 7/8 не можна зарахувати за схемою або UML (`implementation-plan.md:266,273`). |
| LOW | `design-principles.md` містить застаріле твердження про відсутність коду | Документ описує старіший стан, тому для аудиту реалізації вирішальними були source/tests; це не функціональний дефект. |

## J. First Incomplete Phase

**FIRST INCOMPLETE BACKEND PHASE: PHASE 0 — Repository and Tooling (`UNVERIFIED`).**

1. **Вже є:** проєкти backend/frontend, manifests/lock, `.env.example`, settings, PostgreSQL 17 Compose, README, Vite proxy, Django system check та один DB-free pytest smoke; див. `implementation-plan.md:211-216` і §C/H.
2. **Не доведено:** clean install/clean checkout, робоче з'єднання PostgreSQL, чистий isolated migrate, frontend typecheck/build у межах цього аудиту, браузерний same-origin proxy/CSRF сценарій.
3. **API:** Phase 0 не додає доменних операцій; `/api/v1/` routing skeleton є. A01–A06 із наступної Phase 1 потребують живого PostgreSQL/browser підтвердження.
4. **Правила:** Phase 0 NFR-001/002/004/007 і безпечний session/CSRF dev proxy; доменних BR у Phase 0 немає.
5. **Тести:** DB-free smoke пройшов, але 14 auth integration tests зупинились на setup; browser proxy test відсутній як доказ.
6. **Залежність:** потрібна доступна локальна PostgreSQL 17 або ізольований disposable server з test DB; поточний Docker Desktop daemon недоступний. Найдальша фаза з реальним кодом — Phase 1 (`PARTIAL`), не Phase 0.

## K. Recommended Next Implementation Batch

**Batch: закриття Phase 0 execution gate на ізольованому PostgreSQL та browser proxy.**

- **Goal:** отримати відтворювані результати clean setup/міграцій та same-origin session/CSRF smoke; після цього повторити A01–A06 DB-тести, щоб визначити фактичний стан Phase 1.
- **Dependencies:** запустити локальний PostgreSQL 17/Docker Desktop або інший дозволений disposable PostgreSQL; зберегти існуючу development DB і дані, використовувати нову ізольовану test DB. Перевірити README setup із чистого checkout/venv без зміни production settings.
- **Likely files:** за потреби лише `README.md`, `compose.yaml`, `backend/pyproject.toml`, `backend/tests/test_smoke.py`, frontend proxy smoke tests/config; точні зміни визначити після виконання перевірок. У межах цього аудиту їх не змінювали.
- **API operations:** Phase 0 не додає маршрутів; для proof перевірити A01 GET CSRF і A02/A03/A04 через `http://localhost:5173/api/v1/*`, а також current-user A05. A07/A08 — окремий наступний Phase 1 implementation batch.
- **Business rules:** NFR-001/002/004/007, коректний session/CSRF режим; жодне PROPOSED BR не підвищувати до CONFIRMED.
- **Database changes:** не потрібні за поточним Phase 0 source; виконувати міграції тільки на ізольованій disposable DB, ніколи не на невідомій persistent DB без окремого рішення.
- **Tests to run/add:** `manage.py check`, `makemigrations --check --dry-run`, isolated `migrate`/`showmigrations`, `pytest`, frontend typecheck/build; browser smoke зі справжніми cookies, `X-CSRFToken`, valid/invalid mutation та logout. Додати автоматизований proxy smoke лише якщо перевірка не представлена придатним тестом.
- **Acceptance:** чистий локальний startup на `:5173`/`:8000`, `/api/v1/*` через Vite, PostgreSQL 17 connection/migrations, secure same-origin cookie/CSRF flow, усі існуючі backend тести проходять або кожен remaining failure документований як конкретний Phase 1 defect; build/typecheck проходять. **Complexity: MEDIUM.**

---

## L. Verification Update (2026-11-01) — Закриття інфраструктурного гейту Phase 0

Дата оновлення: 2026-11-01. Попередні розділи A–K збережено як історичний baseline первинного аудиту.

### L.1. Діагностика причини попередньої недоступності PostgreSQL та ізоляція середовища

1. **Фактична причина блокера первинного аудиту:** на хості Ubuntu 26.04 встановлено Docker CLI 29.8.2 та Docker Desktop 4.97.0 (користувацький сервіс `docker-desktop`, контекст `desktop-linux`, сокет `~/.docker/desktop/docker.sock`), тоді як системний Docker Engine (`docker.service` / `/var/run/docker.sock`) та нативний сервер PostgreSQL (`/usr/lib/postgresql`) не встановлені. Під час первинного аудиту демон Docker Desktop не був активний (або звернення виконувалося з ізольованого sandbox без доступу до сокета хоста). Після запуску Docker Desktop основний контейнер проєкту `kursa4-db-1` (`postgres:17`, версія `PostgreSQL 17.11 (Debian 17.11-1.pgdg13+2)`) слухає `127.0.0.1:5432` і змонтований до постійного тому `kursa4_postgres_data`.
2. **Збереження даних розробки та повна ізоляція верифікації:** основний контейнер `kursa4-db-1` (`127.0.0.1:5432`, база `fitness_dev`, том `kursa4_postgres_data`) та файл `.env` не модифікувалися. Для чистої перевірки з нуля створено окремий одноразовий контейнер `kursa4-p0iso-66ac9afc` (`postgres:17`, `--rm`, зберігання у RAM `--tmpfs /var/lib/postgresql/data`, порт `127.0.0.1:55433->5432`, окрема БД `fitness_p0verify` і роль `fitness_p0verify`). Після завершення всіх перевірок тимчасовий контейнер зупинено й автоматично видалено; звірка `kursa4-db-1` підтвердила повну незмінність основної БД (`users = 0`, `django_session = 0`, `django_migrations = 20`).

### L.2. Результати перевірки міграцій, тестів та інструментарію (Phase 0 DoD)

| Перевірка | Команда / Метод | Exit | До оновлення (Baseline §H) | Після оновлення (2026-11-01) | Доказ / Деталі |
|---|---|---:|---|---|---|
| Django system check | `manage.py check` | 0 | `0 issues (1 silenced)` | `0 issues (1 silenced)` | `auth.W004` обґрунтовано індексом `users_email_lower_unique`. |
| Drift моделей/міграцій | `manage.py makemigrations --check --dry-run` | 0 | Warning (без PG) | `No changes detected` (з активною PG 17.11) | Жодного розходження між `accounts.User` та міграціями. |
| Чиста міграція з нуля | `manage.py migrate` (на порожній `fitness_p0verify` `:55433`) | 0 | Не виконувалась | 20/20 міграцій застосовано `OK` | Включно з `accounts.0001_initial` та `accounts.0002_...`; перевірено `UNIQUE(LOWER(email))` та `CHECK (users_opt_in_alias_required)`. |
| План міграцій | `manage.py showmigrations --plan` | 0 | Exit 1 (`connection refused`) | 20/20 `[X]` | Повний ланцюжок `contenttypes`, `auth`, `accounts`, `admin`, `sessions`. |
| Backend тести (`pytest`) | `.venv/bin/python -m pytest -v` | 0 | **15 collected: 1 passed, 14 setup errors** | **15 collected: 15 passed, 0 failed, 0 errors, 0 skipped** (4.16s) | `pytest-django` створив і знищив ізольовану БД `test_fitness_p0verify`; усі 14 інтеграційних тестів у `accounts/tests/test_auth.py` та 1 у `tests/test_smoke.py` пройшли. |
| Python лінтер і форматер | `ruff check .` / `ruff format --check .` | 0 | Passed | Passed (`34 files already formatted`) | Конфігурація `backend/pyproject.toml`. |
| Frontend typecheck / lint | `npm run typecheck` / `npm run lint` | 0 | Не запускались в аудиті | Passed (0 помилок) | TypeScript 6.0.2, ESLint 10.14.0. |
| Frontend unit-тести | `npm test` (`vitest run`) | 0 | Не запускались в аудиті | **3 файли, 12/12 passed** | `api.test.ts` (2), `components.test.tsx` (4), `App.test.tsx` (6) — unit-тести з mocked `fetch`. |
| Frontend production build | `npm run build` | 0 | Не запускався в аудиті | Passed (`125 modules transformed`) | Збірка Vite 8.3.5 без помилок. |

### L.3. Жива верифікація A01–A06, Vite Proxy (`:5173` → `:8000`) та реального браузера

Перевірено на живих процесах `manage.py runserver localhost:8000` (підключеному до ізольованої PostgreSQL 17.11 `:55433`) та `vite --host localhost --port 5173 --strictPort` без жодних моків:

1. **Пряма HTTP-верифікація через Vite proxy (`http://localhost:5173/api/v1/*` — 37/37 перевірок пройдено):**
   - **A01 (`GET /api/v1/auth/csrf/`):** повертає `200 {"csrf_token": ...}` і встановлює cookie `csrftoken` (`SameSite=Lax`, без `HttpOnly`, доступний для читання SPA).
   - **A02 (`POST /api/v1/auth/register/`):** без `X-CSRFToken` → `403 csrf_failed`; невалідні email або пароль < 12 символів → `400 validation_error` з деталізацією у `fields`; валідні дані → `201` (`id`, `email`, `public_alias: null`, `leaderboard_opt_in: false`), не створює `sessionid` (`GET /api/v1/me/` → `401`); повторна реєстрація з іншим регістром (`UPPERCASE`) → `409 email_taken`.
   - **A03 (`POST /api/v1/auth/login/`):** без CSRF або з недовіреним `Origin: http://evil.example` → `403 csrf_failed`; невірний пароль → `401 invalid_credentials`; валідний вхід → `200`, встановлює `sessionid` (`HttpOnly`, `SameSite=Lax`) та ротує `csrftoken`; у тілі JSON відсутні паролі/токени.
   - **A05 (`GET /api/v1/me/`):** анонімно → `401 authentication_required`; у сесії → `200` рівно з 4 полями (`id`, `email`, `public_alias`, `leaderboard_opt_in`).
   - **A06 (`PATCH /api/v1/me/`):** без CSRF → `403 csrf_failed`; збереження `public_alias` та увімкнення `leaderboard_opt_in: true` → `200`; спроба увімкнути opt-in з порожнім/пробільним псевдонімом або стерти псевдонім при активному opt-in → `400 validation_error` (`fields.public_alias`); спроба передати `is_staff` → `400 unknown_field`; невалідний JSON → `400 invalid_json`; вимкнення `leaderboard_opt_in: false` → `200`; збереження підтверджено повторним входом у незалежній сесії.
   - **A04 (`POST /api/v1/auth/logout/`):** без CSRF → `403 csrf_failed`; з актуальним `X-CSRFToken` → `204 No Content`, очищує `sessionid`; подальші A05/A06/A04 повертають `401 authentication_required`.
   - **Маршрутизація proxy vs SPA:** неіснуючий маршрут `/api/v1/does-not-exist/` із браузерним `Accept: text/html` повертає `404` від Django (не перехоплюється SPA fallback `index.html`), тоді як клієнтський маршрут `/settings` віддає `200 text/html` (`<div id="root"></div>`) від Vite.
2. **Реальна браузерна E2E-верифікація у Firefox 159.0 Headless (WebDriver BiDi — 7/7 сценаріїв пройдено):**
   - Відкриття `http://localhost:5173/register` у справжньому браузері Firefox → автоматичне отримання `csrftoken` через A01.
   - Заповнення та сабміт форми реєстрації → редірект на `/login` з банером `«Акаунт створено. Тепер увійдіть.»` без автоматичного логіну.
   - Вхід через форму `/login` → редірект на `/`, відображення `«Вітаємо у Фітнес-трекері»` та email користувача; перевірка у контексті сторінки підтвердила, що `document.cookie` не містить `sessionid` (`HttpOnly`), а `csrftoken` був ротований.
   - Клієнтський перехід у `/settings`, введення псевдоніма `NordicBrowser`, увімкнення перемикача `«Показувати мене в рейтингу»` та натискання `«Зберегти»` → `PATCH /api/v1/me/` із ротованим `X-CSRFToken` повертає `200`, відображається банер `«Налаштування рейтингу збережено.»`.
   - Повне перезавантаження сторінки (`browsingContext.reload` на `/settings`) → сесія відновлюється через `sessionid` cookie та `GET /api/v1/me/`, поле псевдоніма містить `NordicBrowser`, перемикач залишається у стані `checked`.
   - Натискання кнопки `«Вийти»` → `POST /api/v1/auth/logout/` (`204`), редірект на `/login`, перевірка `fetch("/api/v1/me/")` з браузера повертає `401`.

### L.4. Переоцінка статусу фаз та наступний крок

- **PHASE 0 (Repository and Tooling): `COMPLETE`.** Усі критерії Definition of Done (`docs/implementation/implementation-plan.md:211-216`) виконані та підтверджені доказами на ізольованій PostgreSQL 17.11 і в реальному браузері через Vite proxy.
- **PHASE 1 (Custom User, auth і permissions): `PARTIAL` на момент завершення §L (закрито до `COMPLETE` у §M нижче).** Операції A01–A06, кастомна модель `accounts.User`, міграції `0001`/`0002`, адмін-деактивація та всі 14 DB-тестів підтверджені (`IMPLEMENTED_AND_VERIFIED`), однак операції відновлення пароля **A07 (`POST /api/v1/auth/password-reset/`)** та **A08 (`POST /api/v1/auth/password-reset/confirm/`)** і відповідний UI ще не були реалізовані на момент §L.
- **Перша незавершена фаза (на момент §L):** **Phase 1 (`PARTIAL`)**.
- **Наступний обмежений пакет реалізації (на момент §L):** **Phase 1 — реалізація та верифікація A07/A08 (відновлення пароля).**

---

## M. Verification Update (2026-11-01) — Закриття Phase 1 (A07/A08 Password Recovery)

Дата оновлення: 2026-11-01. Попередні розділи A–L збережено як історичну трасу аудиту та закриття Phase 0.

### M.1. Реалізовані компоненти Phase 1 (FR-042, BR-035, A07, A08, D01, D02)

1. **Backend API та сервіс відновлення пароля (`backend/accounts/`):**
   - `backend/accounts/services.py`: реалізовано `PasswordResetService` (`request_reset` / `confirm_reset` та сумісні з UML-клас-діаграмою аліаси `requestReset` / `confirmReset`) із використанням штатного `django.contrib.auth.tokens.default_token_generator` (`PasswordResetTokenGenerator`) без створення зайвих таблиць у БД.
   - **A07 (`POST /api/v1/auth/password-reset/`):** `PasswordResetRequestView` (`AllowAny`, `@method_decorator(csrf_protect, name="dispatch")`), валідація через `PasswordResetRequestSerializer` (`StrictSerializer`), нормалізація email (`strip().lower()`), anti-enumeration (однакова відповідь `200 {"message": "Якщо акаунт із такою адресою існує, ми надішлемо інструкції для відновлення пароля."}` для активних, неіснуючих, деактивованих `is_active=False` та `unusable_password` акаунтів, компенсація часу генерацією фіктивного токена для неактивних/неіснуючих адрес), відправка українськомовного листа (`password_reset_subject.txt`, `password_reset_body.txt`) з посиланням `{FRONTEND_ORIGIN}/reset-password/{uid}/{token}`.
   - **A08 (`POST /api/v1/auth/password-reset/confirm/`):** `PasswordResetConfirmView` (`AllowAny`, `@method_decorator(csrf_protect, name="dispatch")`), валідація через `PasswordResetConfirmSerializer` (`StrictSerializer`, `trim_whitespace=False`), транзакційне блокування рядка користувача `User.objects.select_for_update()` всередині `transaction.atomic()`, перевірка `uid` (`urlsafe_base64_decode`) та `default_token_generator.check_token(user, token)` (помилка `400 reset_token_invalid_or_expired`), валідація `new_password` через `password_validation.validate_password` без передчасного споживання токена (`400 validation_error` з `fields.new_password`), оновлення хешу `user.set_password(new_password)` (що миттєво анулює токен і всі попередні сесії користувача без виклику `login()` чи `update_session_auth_hash()`), відповідь `200 {"message": "Пароль оновлено. Увійдіть із новим паролем."}`.
   - **Throttling та безпека (`backend/accounts/throttling.py`, `backend/accounts/errors.py`, `backend/config/settings/`):** додано `PasswordResetIPThrottle` (`10/hour`), `PasswordResetEmailThrottle` (`5/hour` за SHA-256 від нормалізованого email однаково для існуючих і неіснуючих адрес) та `PasswordResetConfirmIPThrottle` (`10/hour`), мапінг `Throttled` → `429 rate_limit_exceeded` та `ResetTokenInvalidOrExpired` → `400 reset_token_invalid_or_expired` у стандартний конверт помилок із `request_id`. Налаштовано `PASSWORD_RESET_TIMEOUT = 3600`, `SECURE_REFERRER_POLICY = "no-referrer"`, `locmem.EmailBackend` для `local.py`/`test.py` та конфігурований SMTP/filebased backend через змінні середовища.
2. **Frontend React інтеграція (`frontend/src/`):**
   - `frontend/src/app/api.ts`: додано `requestPasswordReset` (`POST /api/v1/auth/password-reset/`) та `confirmPasswordReset` (`POST /api/v1/auth/password-reset/confirm/`) з автоматичним CSRF-bootstrap та передачею `X-CSRFToken`.
   - `frontend/src/pages/AuthPage.tsx`: додано посилання `«Забули пароль?»` на `/forgot-password` у режимі входу.
   - `frontend/src/pages/PasswordResetRequestPage.tsx` (`D02` — `/forgot-password`, `/password-reset`): форма запиту відновлення у дизайн-системі Nordic Vitality з нейтральним повідомленням підтвердження та повторною відправкою.
   - `frontend/src/pages/PasswordResetConfirmPage.tsx` (`D01` — `/reset-password/:uid/:token`, `/reset-password`): негайне очищення адресного рядка у `useLayoutEffect` через `window.history.replaceState({ resetCredentials: next }, "", "/reset-password")` (без збереження `uid`/`token` у `localStorage`, `sessionStorage`, `document.cookie` або логах консолі), підтримка оновлення сторінки та обробка станів успіху й недійсного/простроченого посилання.
   - `frontend/index.html` та `frontend/src/style.css`: додано `<meta name="referrer" content="no-referrer" />` та видалено зовнішній `@import` Google Fonts для унеможливлення витоку URL/реферера на сторонні домени.

### M.2. Результати автоматизованих перевірок та живого E2E-тестування

Усі перевірки з БД виконано на окремому одноразовому контейнері `kursa4-p1iso-66ac9afc` (`postgres:17`, порт `127.0.0.1:55434->5432`, `--tmpfs`) без жодного втручання в основний контейнер розробки `kursa4-db-1` (`127.0.0.1:5432`, база `fitness_dev`).

| Перевірка | Команда / Метод | Exit | Результат | Доказ / Деталі |
|---|---|---:|---|---|
| Django system check & migrations | `manage.py check` / `makemigrations --check --dry-run` | 0 | `0 issues (1 silenced)` / `No changes detected` | Нові таблиці не створювалися (`20/20` міграцій застосовано). |
| Backend тести (`pytest` на PG 17.11) | `.venv/bin/python -m pytest -v` | 0 | **25 collected: 25 passed, 0 failed, 0 errors** (7.40s) | `accounts/tests/test_auth.py` (14), `accounts/tests/test_password_reset.py` (10), `tests/test_smoke.py` (1), включно з тестом конкурентного `confirm_reset` (`ThreadPoolExecutor` + `select_for_update()`). |
| Python лінтер і форматер | `ruff check backend` / `ruff format --check backend` | 0 | Passed (`37 files already formatted`) | Без помилок чи попереджень. |
| Frontend typecheck & lint | `npm run typecheck` / `npm run lint` | 0 | Passed (0 помилок) | Сувора типізація TypeScript та правила ESLint. |
| Frontend тести (`Vitest`) | `npm test` (`vitest run`) | 0 | **4 файли, 17/17 passed** | `api.test.ts` (2), `components.test.tsx` (4), `App.test.tsx` (6), `PasswordReset.test.tsx` (5). |
| Frontend production build | `npm run build` | 0 | Passed (built in 237ms) | Чиста збірка Vite. |
| Реальний браузерний E2E (Firefox 159.0 Headless BiDi) | Наскрізний сценарій через Vite proxy `:5173` → Django `:8000` → PG 17 `:55434` | 0 | **9/9 кроків PASS**, `externalFontRequestsCount: 0` | Перехід `/login` → `/forgot-password` → A07 (`200`) → читання листа з ізольованого outbox → відкриття `/reset-password/{uid}/{token}` з миттєвим scrubbing URL до `/reset-password` і чистотою storage/cookie → A08 (`200`) → відмова входу зі старим паролем (`401`) → вхід із новим паролем (`200`) → перевірка `/settings` і виходу (`204`) → відмова при повторному використанні токена (`400 reset_token_invalid_or_expired`). |
| Незалежне рев’ю (Agent E) | Read-only аудит безпеки та архітектури | — | **PASS** (`0 CRITICAL`, `0 HIGH`, `0 MEDIUM`) | Повна відповідність FR-042, BR-035, `rest-api.md` та Phase 1 DoD. |

### M.3. Оновлений підсумковий статус фаз

- **PHASE 0 (Repository and Tooling): `COMPLETE`.**
- **PHASE 1 (Custom User, auth і permissions): `COMPLETE`.** Усі 8 операцій (`A01–A08`), модель `accounts.User`, сесійна автентифікація, CSRF, відновлення пароля, адміністративна деактивація та відповідні React-екрани реалізовані й підтверджені автоматичними та браузерними E2E-тестами на PostgreSQL 17.11.
- **Перша незавершена фаза (на момент §M):** **PHASE 2 — Profile і WeightEntry (`NOT_STARTED` на момент §M; закрито до `COMPLETE` у §N нижче)**.
- **Рекомендований наступний пакет реалізації (на момент §M):** **Phase 2 — реалізація моделей `Profile` та `WeightEntry`, сервісу `ProfileService` і операцій `P01–P04`**.

---

## N. Verification Update (2026-11-01) — Закриття Phase 2 (Profile і WeightEntry)

Дата оновлення: 2026-11-01. Попередні розділи A–M збережено як історичну трасу аудиту та закриття Phases 0–1.

### N.1. Реалізовані компоненти Phase 2 (FR-003, FR-004, BR-001, BR-012, BR-013, BR-019, BR-027, BR-028, BR-031, BR-032, BR-034, P01–P04)

1. **Доменні моделі та схема PostgreSQL (`backend/accounts/models.py`, `backend/accounts/migrations/0003_profile_weightentry.py`):**
   - Перелічення `Gender` (`male`, `female`, `other`, `prefer_not_to_say`), `FitnessGoal` (`weight_loss`, `muscle_gain`, `maintenance`) та `ExperienceLevel` (`beginner`, `intermediate`, `advanced`).
   - Модель `Profile` (`db_table = "profiles"`): `user = OneToOneField("accounts.User", on_delete=models.CASCADE, primary_key=True, related_name="profile")` (стовпець `user_id` є одночасно PK і FK із каскадним видаленням за `BR-032`), необов'язкові персональні поля `first_name` і `last_name` (`CharField(max_length=150, blank=True, default="", db_default="")` без `NULL` за `BR-034`), 7 фітнес-полів (`date_of_birth`, `weight_kg` `DecimalField(4,1)`, `height_cm` `DecimalField(4,1)`, `gender`, `fitness_goal`, `experience_level`, `workouts_per_week`), `created_at`. Поле `age` не зберігається у БД (`BR-001`, `OQ-05`).
   - Шість PostgreSQL `CheckConstraint` на `Profile`: `profiles_weight_kg_range` (`20.0..500.0`), `profiles_height_cm_range` (`100.0..250.0`), `profiles_workouts_per_week_range` (`1..7`), `profiles_gender_valid`, `profiles_fitness_goal_valid`, `profiles_experience_level_valid`.
   - Модель `WeightEntry` (`db_table = "weight_entries"`): `user = ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="weight_entries")`, `measured_at`, `weight_kg` `DecimalField(4,1)`, `created_at`; PostgreSQL `CheckConstraint` `weight_entries_weight_kg_range` (`20.0..500.0`) та складений індекс `weight_entries_user_meas_idx` на `("user", "-measured_at", "-id")` (`docs/architecture/erd.md` §3.1, §7).
   - Приватність у Django Admin (`BR-028`): `Profile` та `WeightEntry` не зареєстровано в `backend/accounts/admin.py`.
2. **Сервісний шар і селектори (`backend/accounts/services.py`, `backend/accounts/selectors.py`):**
   - `ProfileService`:
     - `calculate_age(date_of_birth, on_date=None)` та `validate_age_on_date(date_of_birth, reference_date)`: обчислення повних років у часовій зоні `Europe/Kyiv` (`ZoneInfo("Europe/Kyiv")`) та перевірка діапазону `19..59` включно (`BR-001`, `OQ-05`).
     - `get_profile(user)`: повертає поточний профіль користувача або підіймає `ProfileMissing` (`404 profile_missing`).
     - `create_profile(user, data)` (аліас `createProfile`): виконується в `transaction.atomic()`, блокує рядок `User` через `select_for_update()` (`BR-012`), перевіряє активність акаунта та відсутність профілю (`409 profile_exists`), валідує `date_of_birth` відносно локальної дати створення в `Europe/Kyiv`, створює `Profile` і атомарно додає первинний `WeightEntry` з однаковим `measured_at = created_at = now` (`BR-019`, `FR-004`).
     - `update_profile(user, data)` (аліаси `updateProfile`, `updateProfileAndWeight`): виконується в `transaction.atomic()`, блокує `User` та `Profile` через `select_for_update()`, при корекції `date_of_birth` перевіряє вік `19..59` станом на локальну дату первинного створення `Profile.created_at` у `Europe/Kyiv` (`BR-001`, `OQ-11`), оновлює змінені поля профілю й атомарно додає новий `WeightEntry` тоді й лише тоді, коли `weight_kg` передано і його значення змінилося.
   - `list_user_weight_entries` та `kyiv_date_range_to_utc` (`backend/accounts/selectors.py`): строго фільтрують `WeightEntry` за `user=request.user`, конвертують піввідкритий інтервал `[start_date, end_date)` локальних дат `Europe/Kyiv` у UTC з урахуванням переходів DST та впорядковують за `("-measured_at", "-id")`.
3. **REST API (`P01`–`P04` у `backend/accounts/{errors,serializers,views,urls}.py`):**
   - **P01 (`GET /api/v1/profile/`):** повертає `200` з 10 полями профілю (включно з динамічним `age` та рядковими `weight_kg`/`height_cm` із 1 знаком після крапки) або `404 profile_missing`.
   - **P02 (`POST /api/v1/profile/`):** валідує 7 обов'язкових фітнес-полів і необов'язкові `first_name`/`last_name` (`StrictSerializer`, відхилення `age` та серверних/невідомих полів із `400 unknown_field`, відхилення `bool`/`float` для цілих і `bool` для десяткових полів), повертає `201 Created` або `409 profile_exists`.
   - **P03 (`PATCH /api/v1/profile/`):** часткове оновлення полів профілю (`200 OK` або `404 profile_missing`), очищення імен через `""`.
   - **P04 (`GET /api/v1/weight-entries/`):** read-only список історії ваги власника з пагінацією (`page`, `page_size` до `100`, `count`, `next`, `previous`, `results`; позамежна сторінка → `400 validation_error`; порожня вибірка на `page=1` → `200` з `results: []`) та парним фільтром `start_date`/`end_date` (`start_date < end_date`). Операція `P05` (`GET /api/v1/statistics/weight-chart/`) не реалізовувалась у Phase 2 і залишена для Phase 8 згідно з планом.

### N.2. Результати автоматизованих перевірок та незалежного рев'ю

Усі перевірки з БД виконано на окремому одноразовому контейнері `kursa4-p2iso-66ac9afc` (`postgres:17`, порт `127.0.0.1:55435->5432`, `--tmpfs`) без втручання в основний контейнер розробки `kursa4-db-1` (`127.0.0.1:5432`, база `fitness_dev`).

| Перевірка | Команда / Метод | Exit | Результат | Доказ / Деталі |
|---|---|---:|---|---|
| Django system check & migrations | `manage.py check` / `makemigrations --check --dry-run` / `migrate` | 0 | `0 issues (1 silenced)` / `No changes detected` / `21/21 applied` | Чисте застосування `accounts.0003_profile_weightentry` на PostgreSQL 17.11. |
| Backend тести (`pytest` на PG 17.11) | `.venv/bin/pytest -v` | 0 | **70 collected: 70 passed, 0 failed, 0 errors** (21.02s) | `test_profile.py` (45), `test_auth.py` (14), `test_password_reset.py` (10), `test_smoke.py` (1) — включно з тестами `CheckConstraint`, rollback, конкурентності (`ThreadPoolExecutor`) та переходів DST у `Europe/Kyiv`. |
| Python лінтер і форматер | `ruff check backend` / `ruff format --check backend` | 0 | Passed | 0 помилок чи попереджень у всьому `backend/`. |
| Frontend регресія (`typecheck`, `lint`, `test`, `build`) | `npm --prefix frontend run typecheck && lint && test && build` | 0 | **4 файли, 17/17 passed**, clean build | Жодних регресій у клієнтському застосунку. |
| Незалежне рев'ю (Agent E) | Read-only аудит архітектури, безпеки, БД та REST контракту | — | **PASS** (`0 CRITICAL`, `0 HIGH`, `0 MEDIUM`, `0 LOW`) | Повна відповідність вимогам Phase 2 DoD. |

### N.3. Проміжний статус після Phase 2

- **PHASE 0 (Repository and Tooling): `COMPLETE`.**
- **PHASE 1 (Custom User, auth і permissions): `COMPLETE`.**
- **PHASE 2 (Profile і WeightEntry): `COMPLETE`.**

---

## O. Verification Update (2026-11-01) — Закриття Phase 3 (Shared Catalog і Admin publication)

Дата оновлення: 2026-11-01. Попередні розділи A–N збережено як історичну трасу аудиту та закриття Phases 0–2.

### O.1. Реалізовані компоненти Phase 3 (FR-006–FR-010, FR-037, FR-038, BR-002–BR-005, C01–C04)

1. **Доменні моделі та схема PostgreSQL (`backend/catalog/models.py`, `backend/catalog/migrations/0001_initial.py`):**
   - Перелічення категорій вправ `ExerciseCategory` (`cardio` = "Кардіо", `strength` = "Силові", `yoga` = "Йога", аліас `Category`).
   - Статуси шаблонів `ProgramTemplateStatus` (`published`, `archived`, аліас `TemplateStatus`).
   - Модель `Exercise` (`db_table = "exercises"`): `name` (160), `description` (text, default ""), `category` (24), 4 поля пакета MET Compendium 2024 (`met_value` Decimal 5,2, `met_activity_code` 5 символів, `met_reference_version` 40, `met_activity_description` text), `is_archived` (bool).
     - Констрейнти: `exercises_category_valid`, `exercises_met_value_pos` (> 0.00), `exercises_met_code_format` (рівно 5 цифр), `exercises_met_pkg_consistent` (усі 4 поля MET або одночасно присутні та непорожні, або одночасно NULL).
     - Індекс: `exercises_arch_cat_name_idx` на `("is_archived", "category", "name")`.
   - Модель `Workout` (`db_table = "workouts"`): `name`, `description`, `category`, MET-поля тренування, `is_archived`.
     - Констрейнти: `workouts_category_valid`, `workouts_met_value_pos`, `workouts_met_code_format`, `workouts_met_pkg_consistent`.
     - Індекс: `workouts_arch_cat_name_idx` на `("is_archived", "category", "name")`.
   - Модель `WorkoutExercise` (`db_table = "workout_exercises"`): `workout` (`CASCADE`), `exercise` (`PROTECT` за `BR-005`), `position` (>0), рекомендовані параметри (`recommended_sets`, `recommended_reps`, `recommended_load_kg` Decimal 6,1, `recommended_duration_min` Decimal 7,2, `recommended_distance_km` Decimal 8,3).
     - Констрейнти: `workout_exercises_workout_pos_uniq` (`UniqueConstraint(workout, position)` — вправа може повторюватися на різних позиціях), `workout_exercises_pos_pos` (>0), `workout_exercises_sets_pos` (>0), `workout_exercises_reps_pos` (>0), `workout_exercises_load_nonneg` (>=0.0), `workout_exercises_dur_pos` (>0.00), `workout_exercises_dist_pos` (>0.000).
   - Модель `ProgramTemplate` (`db_table = "program_templates"`): `name`, `description`, `fitness_goal` (`FitnessGoal`), `experience_level` (`ExperienceLevel`), `workouts_per_week` (1..7), `status` (`published | archived`).
     - Констрейнти: `program_templates_goal_valid`, `program_templates_level_valid`, `program_templates_status_valid`, `program_templates_freq_range`.
     - Частковий індекс: `prog_tmpl_pub_lookup_idx` на `("fitness_goal", "experience_level", "workouts_per_week", "id") WHERE status='published'`.
   - Модель `ProgramTemplateWorkout` (`db_table = "program_template_workouts"`): `program_template` (`CASCADE`), `workout` (`PROTECT`), `position` (>0), `suggested_weekday` (null або 1..7).
     - Констрейнти: `prog_tmpl_workouts_tmpl_pos_uniq`, `prog_tmpl_workouts_pos_pos`, `prog_tmpl_workouts_weekday_rng`.
2. **Сервісний шар доменної публікації (`backend/catalog/services.py` — `CatalogPublicationService`):**
   - `validate_met_metadata(obj)`: перевіряє цілісність пакета MET C2024.
   - `validate_workout_exercise_parameters(we)`: перевіряє сумісність параметрів з категорією (`BR-002`):
     - `strength`: обов'язкові `sets > 0` та `reps > 0`; `load_kg >= 0` опціонально; `duration_min` і `distance_km` заборонені.
     - `cardio`: обов'язкові `duration_min > 0` АБО `distance_km > 0` (або обидва); `sets`, `reps`, `load_kg` заборонені.
     - `yoga`: обов'язкова `duration_min > 0`; `sets`, `reps`, `load_kg`, `distance_km` заборонені.
     - заборона використання архівованих вправ у активних тренуваннях.
   - `validate_persisted_workout(workout)`: активне тренування повинно містити `>= 1` валідну вправу.
   - `validate_persisted_program_template(template)`: опублікований шаблон повинен містити `>= 1` неархівоване тренування, кожне з яких містить `>= 1` вправу (`BR-003`).
   - М'яке архівування (`archive_exercise`, `archive_workout`, `archive_program_template`): перевіряє відсутність активних посилань перед архівацією (`BR-005`).
3. **Django Admin з атомарним відкатом savepoint (`backend/catalog/admin.py`):**
   - Доступ обмежено виключно активним працівникам (`request.user.is_active and request.user.is_staff`).
   - Фізичне видалення сутностей каталогу повністю заборонено (`has_delete_permission = False` за `BR-005`).
   - `AtomicCompositeAdmin`: при збереженні `Workout` та `ProgramTemplate` з inlines (`WorkoutExerciseInline`, `ProgramTemplateWorkoutInline`) обгортає збереження у вкладений savepoint `transaction.atomic()`. Якщо після збереження inlines композиція порушує інваріанти (наприклад, 0 вправ/тренувань, невірні параметри або архівовані посилання), транзакція повністю відкочується (`savepoint_rollback`), скидається `pk`, помилки прив'язуються до форми (`form.add_error`) і повертається HTTP 200 із повідомленнями про помилки без жодного пошкодженого запису в БД (`BR-004`).
4. **Детермінований ідемпотентний seed (`backend/catalog/management/commands/seed_catalog.py`):**
   - Наповнює 10 вправ (включно з верифікованими кодами Compendium 2024 та 1 вправою без MET).
   - Наповнює 6 валідних тренувань (силові спліти А/Б, функціональний мікс, кардіо інтервали/витривалість, хатха-йога).
   - Наповнює 6 опублікованих шаблонів програм: 3 пари для `(beginner, 3 workouts_per_week)` для перевірки стратегій підбору Phase 4 (Weight Loss: висока vs низька частка кардіо; Muscle Gain: 100% vs 33% силових; Maintenance: рівномірний розподіл 1:1:1 vs незбалансований спліт).
   - Ідемпотентність: повторний запуск не дублює рядки, зберігає створені адміністратором користувацькі записи.
5. **Read-Only REST API (`C01`–`C04` у `backend/catalog/{selectors,serializers,views,urls}.py`):**
   - Авторизація: `permission_classes = [IsAuthenticated]` (підтверджена матриця доступу для User/Administrator; доступ Guest позначено як PROPOSED).
   - Сувора валідація query-параметрів (`StrictSerializer`, невідомі параметри → `400 unknown_field`).
   - **C01 (`GET /api/v1/categories/`):** повертає статичні коди й українські лейбли (`cardio`, `strength`, `yoga`).
   - **C02 (`GET /api/v1/exercises/`):** пагінований список активних вправ із фільтрами `category`, `search`, стабільним сортуванням `name, id` та полями MET.
   - **C03 (`GET /api/v1/workouts/`):** пагінований список активних тренувань із `exercise_count`, фільтрами `category`, `search` та стабільним сортуванням.
   - **C04 (`GET /api/v1/workouts/{id}/`):** детальна інформація про тренування із впорядкованим складом `exercises` (`entry_id`, `position`, вкладена вправа, рекомендовані параметри). Архівовані або відсутні тренування повертають `404 not_found`.
   - Захист від мутацій: методи POST/PUT/PATCH/DELETE повертають `405 Method Not Allowed`.

### O.2. Результати автоматизованих перевірок та тестів

Усі перевірки з БД виконано на окремому одноразовому контейнері `kursa4-p3iso-66ac9afc` (`postgres:17`, порт `127.0.0.1:55436->5432`) без втручання в основний контейнер розробки `kursa4-db-1` (`127.0.0.1:5432`, база `fitness_dev`).

| Перевірка | Команда / Метод | Exit | Результат | Доказ / Деталі |
|---|---|---:|---|---|
| Django system check & migrations | `manage.py check` / `makemigrations --check` / `migrate` | 0 | `0 issues (1 silenced)` / `No changes detected` / `22/22 applied` | Чисте застосування `catalog.0001_initial` на PostgreSQL 17.11. |
| Backend тести (`pytest` на PG 17.11) | `.venv/bin/pytest -v` | 0 | **118 collected: 118 passed, 0 failed, 0 errors** (24.57s) | 48 нових тестів у `catalog/tests/` (15 у `test_models.py`, 12 у `test_services_admin.py`, 3 у `test_seed.py`, 18 у `test_api.py`) + 70 попередніх тестів Phases 0–2 без жодної регресії. |
| Python лінтер і форматер | `ruff check backend` / `ruff format --check backend` | 0 | **Passed** | 0 помилок, 54 файли відформатовано за стандартом PEP 8 (88 символів). |
| Перевірка пробілів Git | `git diff --check` | 0 | **Passed** | 0 whitespace дефектів. |
| Frontend регресія (`typecheck`, `lint`, `test`, `build`) | `npm --prefix frontend run typecheck && lint && test && build` | 0 | **4 файли, 17/17 passed**, clean build (dist 333 kB) | Жодних регресій у клієнтському застосунку. |
| Seed ідемпотентність | `manage.py seed_catalog` (2 запуски) | 0 | Стабільні лічильники: 10 вправ, 6 тренувань, 6 шаблонів, 14 вправ тренувань, 18 тренувань шаблонів | Повна стабільність, 0 дублікатів, збереження користувацьких записів. |

### O.3. Оновлений підсумковий статус фаз

- **PHASE 0 (Repository and Tooling): `COMPLETE`.**
- **PHASE 1 (Custom User, auth і permissions): `COMPLETE`.**
- **PHASE 2 (Profile і WeightEntry): `COMPLETE`.**
- **PHASE 3 (Shared Catalog і Admin publication): `COMPLETE`.**
- **Перша незавершена фаза:** **PHASE 4 — Selection і персональний склад (`NOT_STARTED`)**.
- **Рекомендований наступний пакет реалізації:** **Phase 4 — патерн Strategy для рекомендації програм (`SelectionStrategy`, `GoalOrientedStrategy`, `MuscleGainStrategy`, `BalancedStrategy`), глибоке копіювання шаблону в персональний `UserProgram` та REST-операції `G01–G06`**.

## P. Verification Update (2026-11-01) — Phase 4: Selection і персональні програми

Цей розділ фіксує поточний стан і замінює **лише поточні висновки** історичних розділів A–O. Попередні перевірки Phases 0–3 збережені; новий повний backend-прогін підтвердив їхню регресію.

### P.1. Реалізація та відповідність дизайну

| Частина | Фактична реалізація | Доказ |
|---|---|---|
| Домен і PostgreSQL | `UserProgram`, `UserProgramWorkout`, `UserProgramExercise`; `source_program_template` і власник, збережена `fitness_goal`, незалежні входження тренувань/вправ, `PROTECT` для джерел, унікальні позиції, CHECK для цілі/стану/позитивних параметрів і узгодженості майбутнього completion snapshot, індекс власника/архіву/статусу. | `backend/planning/models.py`, `planning.0001_initial`, `planning.0002_align_user_program_with_erd`, PostgreSQL integrity tests. |
| Міграція існуючих чернеток | `0002` додає збережену ціль із джерела та приводить поля до ERD без переписування `0001`, яка могла бути застосована раніше. Міграція зупиняється, якщо стара копія не має джерела або містить бонус/snapshot, що не можна перенести без втрат. | `backend/planning/migrations/0002_align_user_program_with_erd.py`; чистий `migrate` і `makemigrations --check --dry-run`. |
| GoF Strategy | `SelectionStrategy` має `rank`/`sort_key`; три взаємозамінні реалізації окремо оцінюють частку cardio, частку strength або розмах часток cardio/strength/yoga. `ProgramSelectionService` бере реалізацію з явного registry та реально викликає `rank` після спільного фільтра goal+level. Пріоритет: мінімальна різниця частоти → нижча частота → критерій Strategy → менший ID. | `backend/planning/strategies.py`, `backend/planning/services.py`, `backend/planning/tests/test_strategies.py`; усі три пари seed обирають очікувані різні за складом шаблони, включно з тестом, де кращий шаблон має більший ID. |
| Вибір і копіювання | G01 лише читає поточний Profile і опубліковані шаблони. G03 повторно визначає переможця, під блокуванням джерел атомарно копіює ім'я/опис/ціль, кожне входження Workout, кожне входження Exercise та рекомендовані параметри. Історичні `source_*` поля зберігаються; зміни каталогу після копії не змінюють персональний склад. | `ProgramSelectionService`; тести детермінізму, незалежності, rollback, повторного POST і конкурентної зміни джерела. |
| Особисте планування | G02/G04 фільтрують за власником і повертають упорядкований склад; G05 змінює лише назву й опис. G06 бере `UserProgram` lock (порядок для майбутнього E01), потім блокування вправ за ID, перевіряє BR-004 і атомарно замінює лише персональний склад. `source_workout_id` та `category` не змінюються. | `ProgramPlanningService`, G01–G06 API-тести, CSRF/owner/rollback/concurrency тести. |

Три GoF згідно з NFR-007 мають різні фази: **Strategy реалізований і виконується у Phase 4**; **Observer** для завершення тренування та **Template Method** для фактичних результатів залишаються спроєктованими для Phases 6–7. Вони не зараховані як готовий код. SOLID/GRASP у чинному зрізі: views відповідають за HTTP і доступ, serializers — за форму даних, services — за транзакції/правила, Strategy — за змінний критерій складу; owner scope і джерело даних перевіряються сервісом. Пряма залежність сервісу від Django ORM — практичне обмеження DIP, без штучного repository layer.

### P.2. REST coverage і межі фаз

| Операція | Стан | Перевірений контракт |
|---|---|---|
| G01 | IMPLEMENTED | Profile-only input; published exact goal/level; `reason`; 404 без кандидата; без запису. |
| G02 | IMPLEMENTED для Phase 4 draft | Owner-only, status/archived/page/page_size, `id DESC`, draft progress `"0.0"`, bonus false. |
| G03 | IMPLEMENTED | 201 повна глибока копія; 404 недоступний шаблон; 409 інший поточний переможець; atomic rollback. |
| G04 | IMPLEMENTED для Phase 4 draft | Owner-only деталі/склад, нульовий progress, null completion snapshot, bonus false. |
| G05 | IMPLEMENTED | Лише `name`/`description`; 404 чужа копія, 409 completed/archived, 400 недозволені поля. |
| G06 | IMPLEMENTED | Непорожній повний склад, явні `null`, позиції 1..N, BR-004, 404 чужий entry, 409 стан, atomic replacement і lock. |

`progress_percent`, `progress`, `bonus_earned` зараз повертають коректний **draft zero-state**, оскільки Phase 4 не створює ScheduledSession чи PointTransaction. Перед активацією в Phase 5 та виконанням у Phases 6–7 ці поля необхідно підключити до фактичних агрегатів/ledger; активну або завершену програму через G01–G06 створити неможливо. G07–G09, S/E/H та frontend-екрани не входять до цієї реалізації.

Статус рішень не змінено: явне прийняття рекомендації через G03 позначене **PROPOSED** у REST-контракті; правило суцільних позицій G06 теж **PROPOSED**. Реалізація виконує чинний контракт, але це не є мовчазним затвердженням бізнес-правил. BR-021/022 лишаються окремим gate наступних фаз.

### P.3. Верифікація і підсумок

Перевірки з БД проведено на окремому тимчасовому `postgres:17` / **PostgreSQL 17.11** (`kursa4-phase4-review-20261101`, `127.0.0.1:55438`, tmpfs); постійний `kursa4-db-1` на 5432 і його volume не змінювалися. Чиста БД успішно пройшла всі міграції, включно з `planning.0001` і `planning.0002`; `showmigrations planning` показав обидві `[X]`. `manage.py check`: 0 issues (1 silenced); `makemigrations --check --dry-run`: `No changes detected`.

Повна регресія PostgreSQL: **172/172 backend tests passed** (118 попередніх Phases 0–3 + 54 Phase 4). Тести Phase 4 перевірили три seed-пари, власника/CSRF, FK/CHECK/UNIQUE, повторювані входження, незалежність копії, rollback G03/G06, одночасні G03 та G06 через окремі підключення, конкурентну зміну джерела й архівацію вправи. Два окремі тести міграції перевірили перенесення наявної чернетки з `0001` до `0002` та безпечну відмову при непереносному бонусі. Frontend: `typecheck`, ESLint, production build і **17/17 Vitest** passed. `ruff check backend`, `ruff format --check backend`, `git diff --check` passed. Незалежне read-only рев'ю виявило гонку G06 з архівацією вправи; її виправлено блокуванням рядків Exercise та покрито двоконекційним тестом. Інших відкритих CRITICAL/HIGH дефектів для G01–G06 не виявлено.

| Фаза | Поточний стан | Доказ |
|---|---|---|
| 0 | COMPLETE | Історична перевірка §L; regression suite і frontend gates пройшли. |
| 1 | COMPLETE | Історична перевірка §M; auth/recovery regression пройшов. |
| 2 | COMPLETE | Історична перевірка §N; Profile/WeightEntry regression пройшов. |
| 3 | COMPLETE | Історична перевірка §O; catalog/Admin/seed regression пройшов. |
| 4 | COMPLETE для G01–G06 | Домен, Strategy, API, міграції та ізольовані PostgreSQL тести пройшли. |
| 5 | COMPLETE для G07–G08/S01–S04/N01–N03 | Див. §Q; `ScheduledSession`, `Notification`, API, React-зріз і PostgreSQL-тести реалізовано. |
| 6–8 | NOT_STARTED | Observer і Template Method ще не реалізовано; S05/G09/E01 належать Phase 7. |

**Наступна фаза: Phase 6** — persistence execution/engagement і required policies; S05/G09/E01 публікувати разом у Phase 7.

## Q. Verification Update (2026-11-14) — Phase 5: Schedule, activation і reminder core

### Q.1. Реалізований зріз

- Додано `scheduled_sessions` і `notifications`; разом реалізовано **13 з 20** таблиць ERD. Фактичні назви індексів, обмежені 30 символами Django: `sched_sess_user_time_idx`, `sched_sess_prog_status_idx`, `notif_user_status_vis_idx`.
- `ProgramPlanningService` реалізує G07/G08/S02/S04, а `ReminderService` — створення reminder, перенесення того самого запису й idempotent N03. Read-проєкції винесено до `planning/selectors.py`, чисті правила часу/missed/no-op/формату — до `planning/policies.py`. Порядок блокувань: `UserProgram → ScheduledSession → Notification`.
- BR-006 прогрес обчислюється з `ScheduledSession`: нескасовані слоти задають `total_planned`; `completed_planned` дорівнює 0 до Phase 7, `bonus_earned=false` до появи ledger. G07 один раз фіксує `bonus_target_sessions=max(3, initial non-cancelled slots)`.
- Реалізовано маршрути G07–G08, S01–S04, N01–N03. S05/G09/E01 навмисно не зареєстровано до Phase 7 зі спільною оцінкою завершення й ledger.
- React має `/schedule`, `/schedule/:id`, `/notifications`, `/notifications/:id`; S02 доступний із `/programs/:id` та `/catalog/workouts/:id`. Нагадування мають unread badge, polling приблизно раз на 60 секунд і оновлення при focus.

BR-008 (похідний missed, `reschedule_history JSONB`), BR-026 (минулий слот відхиляється, lead <1 години видимий одразу), ідентичний S04 як no-op та клієнтський polling BR-024 лишаються **PROPOSED**: реалізовано як запропоновано, чекає погодження власника.

### Q.2. Верифікація

| Перевірка | Результат |
|---|---|
| Backend regression | **225 tests passed**; Phase 5 покриває ownership/privacy, CSRF, atomic rollback, lock order, idempotent read, UTC whole-second format і concurrent scenarios. |
| Django system checks | `manage.py check --database default` → `System check identified no issues (1 silenced)`. Простий `check` не запускає database-tagged checks на кшталт `models.E034`; smoke test викликає їх із `databases=["default"]`. |
| Frontend Vitest, фінальний запуск 14.11.2026 | **11/11 test files, 61/61 tests passed**. |

### Q.3. Межі

Phase 5 не створює `CompletedSession` або `PointTransaction` і не може закрити програму. Тому S05, G09 і E01 лишаються `NOT_YET_IMPLEMENTED` до Phase 7; Observer і Template Method також не зараховано як реалізований код.
