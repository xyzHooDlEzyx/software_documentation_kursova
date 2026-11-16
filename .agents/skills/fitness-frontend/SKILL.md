---
name: fitness-frontend
description: Створює React-екрани поверх реального DRF API з узгодженою навігацією, станами, дизайном і тестами. Використовуй, коли додається або змінюється користувацький маршрут, API функціонального розділу, UI-компонент чи тест інтерфейсу.
argument-hint: Екран, маршрут або сценарій інтерфейсу
---

# Клієнтська частина

## Джерела й межі

Простеж екран до `FR`/`UC`, `BR` і REST ID. Контракт бери з
`docs/architecture/rest-api.md`, а поточні маршрути — з
`docs/architecture/frontend-ui-architecture.md`. Не вигадуй поля, метрики або
успішні стани, яких не повертає реалізований API.

Стек реалізовано в `frontend/`: React 19, TypeScript, Vite 8, Tailwind CSS v4,
Base UI та shadcn-style source primitives. Не додавай іншу бібліотеку отримання
даних або графіків без реальної потреби й погодження залежності.

## Структура

- `frontend/src/app/api.ts` — єдиний HTTP-шар: `request()`, `withQuery()`,
  `Paginated<T>`, CSRF cookie і `setUnauthorizedHandler`.
- `frontend/src/app/auth/AuthProvider.tsx` — стан сесії.
- `frontend/src/app/router/AppRouter.tsx` і `RequireAuth.tsx` — маршрути й guard.
- `frontend/src/features/` — доменні DTO, API-функції, сторінки й тести;
  наявні підтеки `profile`, `catalog`, `programs`.
- `frontend/src/components/ui/` — спільні примітиви; не створюй локальний
  дубль кнопки, поля, alert, loading або pagination.
- `frontend/src/components/layout/` — оболонки й навігація.
- `frontend/src/lib/labels.ts`, `format.ts`, `errors.ts`, `useResource.ts` —
  спільні labels, formatting, error mapping і resource state.
- `frontend/src/test/mockApi.ts` — `mockApi`, `json`, `apiError` для тестів.
- `frontend/src/styles/tokens.css` — єдине джерело дизайн-токенів.

Жодного `fetch` поза `frontend/src/app/api.ts`. DTO у доменному `api.ts` дзеркалять
фактичні DRF serializers. Decimal із JSON моделюй як `string`, enum показуй через
`frontend/src/lib/labels.ts`, а українські форми чисел — через `plural()` з
`frontend/src/lib/format.ts`.

## Новий функціональний екран

1. Переконайся, що REST-операцію реалізовано; запланований API не відкривай як
   робочий маршрут.
2. Додай DTO й вузькі функції запиту до `api.ts` у відповідній підтеці
   `frontend/src/features/`; для нового домену створи нову підтеку
   `frontend/src/features/<домен>/` із власним `api.ts`.
3. Створи сторінку в тому самому розділі; серверний ресурс завантажуй через
   `useResource` з `frontend/src/lib/useResource.ts`.
4. Передбач завантаження, порожній результат, помилку, готовність та
   успіх/помилку мутації без вигаданих резервних даних.
5. Додай route до `frontend/src/app/router/AppRouter.tsx` і, якщо це основний
   розділ, nav item до
   `frontend/src/components/layout/AuthenticatedLayout.tsx`.
6. Збережи фільтри, сортування і сторінку в параметрах URL, щоб навігація
   назад/уперед і пряме посилання відтворювали стан.
7. Онови таблицю маршрутів у `docs/architecture/frontend-ui-architecture.md` у
   тому самому зрізі; познач заплановане чесно.
8. Додай компонентний/інтеграційний тест поруч із розділом, використовуючи
   `frontend/src/test/mockApi.ts`.

## API та auth

Небезпечні HTTP-запити проходять через `request()` і його CSRF handling. Не
вимикай credentials і не дублюй розбір cookie. Захищений 401 централізовано
передає стан через `setUnauthorizedHandler`; помилки auth-форми не перетворюй на
втрату сесії. 403 показуй як permission/CSRF error відповідно до оболонки з
`backend/accounts/errors.py`.

## UI, мова й доступність

Увесь користувацький текст — українською. Кольори, відступи, типографіку й стани
бери з `docs/architecture/frontend-design-system.md` та
`frontend/src/styles/tokens.css`, не з локальних HEX.

Використовуй семантичні елементи, постійні labels, `aria-describedby` для
підказок/помилок, видимий `focus-visible`, клавіатурну навігацію і текстове
позначення стану. Перевір touch viewport, контраст і `prefers-reduced-motion`.
Успіх показуй лише після успішної відповіді сервера.

## Stitch

`design-reference/` містить прототипи, а
`docs/implementation/stitch-screen-inventory.md` зіставляє їх із функціями та
REST ID. Бери звідти структуру, композицію й перевірені стани UI. Не копіюй scripts,
inline handlers, CDN, демонстраційні записи, зовнішні випадкові assets або жорстко записані
метрики зі Stitch HTML.

## Форматування

Код пишеться читабельним: один JSX-елемент чи вираз на рядок, без стиснення
файлу в кілька довгих рядків. Перед здачею відформатуй **кожен створений або
змінений** файл Prettier (`frontend/.prettierrc.json`, ширина 120):

```bash
npm run format -- <файли>
```

Решту коду масово не переформатовуй, щоб не роздувати диф.

## Перевірка

Тести мають падати на невідомому запиті; `mockApi` уже забезпечує це. Покрий
стан URL, межу auth, завантаження/порожній результат/помилку/успіх, помилки полів
і повторне завантаження після мутації. Повний frontend-комплекс запускає
`fitness-verify`.
