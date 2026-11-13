---
name: fitness-model
description: Підтримує Use Case і UML-діаграму класів та перевіряє реальне застосування GoF, GRASP і SOLID. Використовуй, коли змінюється архітектурна модель, діаграма або пояснення патернів.
argument-hint: Діаграма, патерн або архітектурна зміна
---

# Архітектурне моделювання

## Джерела

Перед зміною прочитай релевантні частини:

- `docs/analysis/requirements.md` і `docs/analysis/use-case-diagram.md`;
- `docs/architecture/domain-model.md` та `docs/architecture/erd.md`;
- `docs/architecture/rest-api.md` для меж сценаріїв і операцій;
- `docs/architecture/design-principles.md` для погоджених GoF/GRASP/SOLID;
- `docs/architecture/additional-gof-proposals.md` лише для оцінки альтернатив;
- §1, §3 і Додаток В у `docs/kursova_DPZSP.pdf`.

Не використовуй `docs/PLAN_VARIANT_4.md`. Не копіюй у діаграми повні таблиці
полів, endpoint-інвентар або текст бізнес-правил: посилайся на відповідні ID.

## Діаграма Use Case

Джерелом згенерованої діаграми є
`docs/diagrams/tools/render_use_case_svg.py`. Змінюй дані та компонування у цьому
скрипті, а не `docs/diagrams/use-case-diagram.svg` вручну.

Після зміни виконай з кореня репозиторію:

```bash
python3 docs/diagrams/tools/render_use_case_svg.py
```

Скрипт також перевіряє компонування. Переглянь згенеровані
`docs/diagrams/use-case-diagram.svg` і `docs/diagrams/use-case-diagram.drawio`,
звір акторів та зв’язки з `docs/analysis/use-case-diagram.md`, а доступ — із
`UC`/`FR` та REST ID. Не показуй запланований сценарій як реалізований.

## Діаграма класів

`docs/diagrams/class-diagram.drawio` має бути однією загальною UML-моделлю
системи з пояснювальними сторінками, а не набором суперечливих схем. Підтримуй
узгоджені назви й зв’язки з `docs/architecture/domain-model.md` та
`docs/architecture/erd.md`; фактичні Django-класи звіряй із `backend/`.

На загальній діаграмі додай окрему легенду кольорів GoF за підходом Додатка В.
Колір патерна не повинен одночасно означати модуль. Поточний конфлікт значень
кольорів між сторінками 01 і 04 треба усунути під час наступної правки.

У репозиторії немає автоматизованого експорту draw.io → PNG. Після редагування
експортуй вручну в draw.io через `File → Export as → PNG`, включивши всі сторінки,
що мають PNG-відповідники, або скористайся локально встановленим draw.io desktop
CLI, якщо він доступний. Потім візуально перевір усі наявні PNG:

- `docs/diagrams/class-diagram-overview.png`;
- `docs/diagrams/class-diagram-catalog-planning.png`;
- `docs/diagrams/class-diagram-execution-engagement.png`;
- `docs/diagrams/class-diagram-services-gof.png`.

Наявні PNG застарілі; не вважай їх доказом актуальності до повторного експорту з
`docs/diagrams/class-diagram.drawio`. Перевір читабельність, стрілки, легенду й
відсутність обрізання.

## GoF

- `Strategy` реалізовано в `backend/planning/strategies.py` і використовує
  `ProgramSelectionService` з `backend/planning/services.py`.
- `Observer` спроєктовано в `docs/architecture/design-principles.md` та
  `docs/architecture/domain-model.md`; його класи заплановано для фаз 6–7 і в
  коді ще не реалізовано.
- `Template Method` так само спроєктовано, але заплановані процесори фаз 6–7 ще
  не реалізовано.

`Factory Method`, `State` і `Command` — лише пропозиції у
`docs/architecture/additional-gof-proposals.md`. Не додавай їх без окремої
реальної потреби, погодженої моделі та коду з тестами. Не називай registry або
Django Signal доказом відповідного GoF без структури учасників патерна.

## Перевірка GRASP і SOLID

Використовуй критерії та матрицю з `docs/architecture/design-principles.md`:

- чи відповідальність належить Information Expert і чи контролер тонкий;
- чи зв’язність висока, а coupling не росте без потреби;
- чи services/selectors є виправданими Pure Fabrication/Indirection;
- чи SRP, OCP, LSP, ISP і DIP підтверджені кодом, а не лише підписом UML;
- чи транзакційна межа й власник інваріанта показані однаково в моделі та коді.

У висновку розділяй `IMPLEMENTED`, `DESIGNED` і `PLANNED`; застарілі статусні
твердження в документах перевіряй за фактичним репозиторієм.
