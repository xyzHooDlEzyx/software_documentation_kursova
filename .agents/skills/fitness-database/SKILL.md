---
name: fitness-database
description: Проєктує PostgreSQL-схему, Django ORM-моделі, міграції та початкові дані з перевіркою цілісності. Використовуй, коли змінюються сутності, зв’язки, обмеження, індекси, міграції або початкове наповнення.
argument-hint: Сутність, зміна схеми або міграція
---

# Робота з базою даних

## Спочатку ERD

Спочатку простеж зміну до `FR`/`UC` у `docs/analysis/requirements.md`, `BR` у
`docs/analysis/business-rules.md` і REST ID у `docs/architecture/rest-api.md`.
Потім узгодь її з `docs/architecture/domain-model.md` та канонічною
`docs/architecture/erd.md`. Не дублюй у навичці або новому документі переліки
полів, constraints чи бізнес-правила.

Якщо вимога має `PROPOSED`, `OPEN` або `CONFLICT`, застосуй правила з
`fitness-requirements`. Зокрема, схема може мати незалежну основу майбутньої
функції, але не повинна вшивати непогоджену поведінку `BR-021`/`BR-022`.

## Фактична схема

Реалізовані моделі знаходяться у:

- `backend/accounts/models.py`: `User`, `Profile`, `WeightEntry`;
- `backend/catalog/models.py`: `Exercise`, `Workout`, `WorkoutExercise`,
  `ProgramTemplate`, `ProgramTemplateWorkout`;
- `backend/planning/models.py`: `UserProgram`, `UserProgramWorkout`,
  `UserProgramExercise`.

`backend/execution/` і `backend/engagement/` поки є порожніми каркасами apps.
`backend/reporting/` — звичайний пакет, не встановлений Django app. Будь-які
майбутні класи з Domain Model називай «заплановано», доки вони не з’являться в
коді та міграціях.

## Моделі та цілісність

- Називай constraint як `<table>_<rule>` і звіряй фізичну назву таблиці з ERD.
- Просту внутрішньорядкову умову закріплюй у PostgreSQL constraint; міжрядковий
  інваріант лишай атомарному service під блокуванням, якщо БД не може виразити його
  коректно.
- Додавай індекс лише під реальний запит selector/report; для нових складних
  індексів обґрунтуй порядок колонок запитом.
- Не створюй таблицю для похідної статистики, якщо канонічна модель визначає її
  як read projection.
- Зберігай узгодженість ORM, ERD, Domain Model і REST-контракту в одному зрізі.

## Міграції

Ніколи не редагуй уже застосовану міграцію. Створюй нову пряму міграцію.
Для перетворення даних використовуй `RunPython`, historical models через
`apps.get_model()` і явну поведінку для непридатних legacy-даних.

Еталон додавання поля → заповнення даних → constraint:
`backend/catalog/migrations/0002_exercise_tracks_distance.py`. Його оновлення
перевіряє `MigrationExecutor` у
`backend/catalog/tests/test_tracks_distance.py`. Інший приклад тестів оновлення —
`backend/planning/tests/test_migrations.py`.

Якщо міграція даних створює права, наслідуй перевірений прийом із
`backend/accounts/migrations/0004_administrator_group.py`: виклик
`create_permissions` та тимчасове `app_config.models_module = True`. Не
імпортуй модель середовища виконання в migration.

Після зміни виконай із завантаженим `.env`:

```bash
set -a; . ./.env; set +a
backend/.venv/bin/python backend/manage.py makemigrations --check --dry-run
backend/.venv/bin/python backend/manage.py migrate
```

Перед створенням міграції команда `makemigrations --check --dry-run` може
очікувано показати незбережені зміни; після додавання migration вона має бути
чистою.

## Початкові дані

`backend/catalog/management/commands/seed_catalog.py` є реалізованою
ідемпотентною командою. Зміни початкового наповнення перевіряй повторним запуском і тестами в
`backend/catalog/tests/test_seed.py`; не створюй production-користувачів і не
фіксуй випадкові PK.

```bash
backend/.venv/bin/python backend/manage.py seed_catalog
```

Інші production seeds додавай лише після погодження відповідних `BR`.

## Безпека операцій

Локальна PostgreSQL працює як service `db` у `compose.yaml` на PostgreSQL 17. Для
звичайної розробки запускай `docker compose up -d db`, застосовуй forward
migrations і seed. Ніколи не видаляй локальну БД, volume або дані для «чистого
старту» без явного дозволу власника. Перед будь-якою destructive operation
покажи точну ціль, наслідки й попроси підтвердження.
