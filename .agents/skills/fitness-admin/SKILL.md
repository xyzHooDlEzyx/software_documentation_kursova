---
name: fitness-admin
description: Розвиває Django Admin як адміністративну частину курсового застосунку з коректними правами, атомарними діями й тестами. Використовуй, коли додається або змінюється адміністративний CRUD, дія, inline чи сторінка звіту.
argument-hint: Модель, дія Django Admin або адміністративний сценарій
---

# Django Admin

## Межа відповідальності

Django Admin є реалізованим адміністративним каналом для облікових записів і
каталогу. Вимоги простежуй через `FR`/`UC`, `BR` та REST/Admin межі у
`docs/architecture/rest-api.md`; не створюй паралельний REST CRUD лише тому, що
модель доступна адміністратору.

Поточні реалізації:

- `backend/accounts/admin.py` — список `User` і action деактивації;
- `backend/catalog/admin.py` — `Exercise`, `Workout`, `ProgramTemplate`, їхні
  агрегати, архівація та permission checks;
- `backend/accounts/migrations/0004_administrator_group.py` — група
  `Administrator` і її чинні permissions.

## Доступ і permissions

Наслідуй `CatalogBaseModelAdmin`: доступ вимагає активного staff-користувача та
відповідного Django model permission. Не покладайся лише на `is_staff` і не
розширюй звичайного адміністратора до superuser.

Коли з’являється нова адміністративна модель або custom permission, додай нову
forward data migration. Для permissions використовуй перевірений прийом із
`backend/accounts/migrations/0004_administrator_group.py`: `create_permissions`
і тимчасове `app_config.models_module = True`, після чого додай потрібні права
до групи `Administrator`. Міграція має працювати на чистій та вже оновленій БД.

## Патерни каталогу

- Фізичне видалення shared catalog вимкнено; lifecycle проходить через archive
  actions і guard у `CatalogPublicationService` з `backend/catalog/services.py`.
- `is_archived` є readonly в admin і не редагується обхідним checkbox.
- Join models редагуються лише inline всередині aggregate root; standalone
  admin для `WorkoutExercise` або `ProgramTemplateWorkout` не реєструй.
- `AtomicCompositeAdmin` з `validate_aggregate` зберігає parent та inlines як
  одну перевірену операцію.
- `ExerciseAdminForm` захищає зміни category/`tracks_distance`; нові form-level
  перевірки не повинні дублювати service guard.

Для нового aggregate спершу визнач корінь у `docs/architecture/domain-model.md`
і зв’язки в `docs/architecture/erd.md`, потім відтвори ці принципи малим
спеціалізованим admin class. Не копіюй великий `AtomicCompositeAdmin`, якщо
спільну поведінку можна безпечно повторно використати.

## Адміністративні дії

Action має перевіряти queryset, model permission і допустимість кожного
переходу. Запис виконуй через application service з транзакцією та
`select_for_update()`, якщо action змінює доменний стан. Частковий успіх не
приховуй: або визнач явну атомарність batch, або покажи користувачу точні
відхилені елементи без обходу guard.

Не вставляй бізнес-правила в `ModelAdmin`; посилай service на канонічний `BR`.

## Соціальні моделі та адмін-звіти

`BR-021`/`BR-022` підтверджено власником (D-2026-11-14). `backend/engagement/admin.py`
реалізує `Challenge` (add/change, publish/unpublish через actions з
`permissions=["change"]`, без delete; критерій участі read-only після першого
учасника) і view-only `Achievement` (п'ять визначень створює міграція, не admin).
Спільна база — `config.admin.AdministratorModelAdmin`. Приватні
`CompletedSession`, `ExerciseResult`, `PointTransaction`, `UserAchievement`,
`ChallengeParticipation` в admin не реєструй.

Звіти `R02`/`R03` (D-2026-11-14) — custom read-only Django Admin views з окремим
permission для групи `Administrator`, не REST і не React. Нові права додавай
міграцією за зразком `accounts.0004` / `engagement.0004`.

## Тести

Використовуй pytest-django client із `client.force_login(...)` та імена URL через
`reverse("admin:...")`. Реальні приклади є у
`backend/catalog/tests/test_services_admin.py` і
`backend/catalog/tests/test_tracks_distance.py`.

Перевір щонайменше staff без permission, адміністратора з permission, add/change
сторінки, readonly/delete boundary, action guard, rollback parent+inlines і
видимі form errors. Тестуй повідомлення помилки через rendered form/admin
response, а стан — повторним ORM read.

## Відкрите рішення про звіти

Канал для запланованих `R02`/`R03` ще не погоджено: Django custom Admin views чи
захищений React-екран. Дивись `D-H5` у
`docs/review/senior-review-2026-11-14.md`. Не обирай канал самостійно; зупинись,
покажи вплив на permissions, Use Case і UI та попроси власника вирішити.
