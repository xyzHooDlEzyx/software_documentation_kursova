# Інвентар Google Stitch і план інтеграції React

Стан перевірки: 01.11.2026. Це аудит **референсів**, а не затвердження макетів або свідчення готовності API. Пріоритет мають [вимоги](../analysis/requirements.md), [бізнес-правила](../analysis/business-rules.md), [REST-контракт](../architecture/rest-api.md) і [план фаз](./implementation-plan.md). Статус `CANDIDATE` означає придатну основу після узгодження з контрактом; `NEEDS_REVIEW` — невирішене рішення щодо вигляду, стану або даних; `VARIANT` — корисний стан чи адаптація тієї самої сторінки. Жоден експорт не позначено як формально схвалений.

## A. Експорти й поточний застосунок

Перевірено **40 `code.html`**: 15 у `stitch_web_platform/` (12 desktop, 2 mobile, 1 root), 16 desktop у `stitch_web_platform(1)/stitch_web_platform/`, 9 desktop у `stitch_web_platform(2)/stitch_web_platform/`. Разом **37 desktop**, **2 mobile**, **1 root**. Є **38 `screen.png`**; зображення відсутні для C07 і C09. Три `nordic_vitality/DESIGN.md` мають однаковий SHA-256 `45d5cc171196a4f418c9f642e2cdc7c390a2de8724e874dca8cdc849ea04bc0f`.

Усі 40 HTML-файлів прочитано як джерела структури, текстів і дій. Візуально переглянуто 38 наявних PNG (частину через контактні аркуші). **C07 і C09 оцінено лише за HTML**. PNG є знімками референсу, а не готовими UI-ресурсами. Підрахунок логічних сторінок: **37**; три додаткові файли — D12 (порожній стан історії ваги), M01 (мобільний вхід) і M02 (мобільна комбінація профілю та ваги). Застарілі версії між трьома архівами не доведені; `desktop_16` і суфікс `(2)` не означають хронології. Редакційний дефект окремого екрана не робить його «старою версією».

Після аудиту React 19/TypeScript/Vite доповнено React Router 7, Tailwind CSS v4 і конфігурацією shadcn/ui для наявного застосунку. Зараз є маршрути `/login`, `/register`, `/` і `/settings`, спільні public/authenticated layouts та UI-примітиви. `frontend/src/app/api.ts` використовує відносні `/api/v1/`, `credentials: "same-origin"`, A01 для cookie `csrftoken`, `X-CSRFToken` для небезпечних методів і повторне читання cookie після login. Vite проксіює `/api/v1` до Django `:8000`. **Реалізовані лише A01–A06**; A07/A08 і доменні операції нижче описані контрактом, але не працюють. Імена/прізвища — необов'язкові поля Profile, не поля register. R02/R03 — Django Admin, не React.

## B. Повний інвентар HTML

У колонці «Назва» наведено функціональне призначення; назву `<title>` і основний заголовок звірено з HTML. ID у **першій колонці** (`D`, `M`, `A`, `C`) позначає Stitch-файл; ID у колонці **API** позначає REST-операцію, навіть коли літери збігаються. Групи `login`, `profile`, `weight` показують функціональне перекриття; `—` означає окремий екран. Усі джерела — точні відносні шляхи від кореня репозиторію.

| ID | Екран (HTML title / головний зміст) | Source HTML | Варіант | Статус | Група | API | Фаза API → UI |
|---|---|---|---|---|---|---|---|
| D00 | Головна панель / Головна | `design-reference/stitch_web_platform/code.html` | root desktop | NEEDS_REVIEW | — | A05, R01, M01, S01 | 8 → 9 |
| D01 | Відновлення доступу / новий пароль і підтвердження | `design-reference/stitch_web_platform/desktop_1/code.html` | desktop | NEEDS_REVIEW | — | A08 | 1+ → 9 |
| D02 | Відновлення пароля / запит листа | `design-reference/stitch_web_platform/desktop_2/code.html` | desktop | CANDIDATE | — | A07 | 1+ → 9 |
| D03 | Мій профіль / огляд | `design-reference/stitch_web_platform/desktop_3/code.html` | desktop | CANDIDATE | profile | A05, P01 | 2 → 9 |
| D04 | Вхід до кабінету / login | `design-reference/stitch_web_platform/desktop_4/code.html` | desktop | NEEDS_REVIEW | login | A01, A03 | 1 → 9 |
| D05 | Каталог тренувань / пошук | `design-reference/stitch_web_platform/desktop_5/code.html` | desktop | CANDIDATE | — | C01, C03 | 3 → 9 |
| D06 | Реєстрація / email, пароль | `design-reference/stitch_web_platform/desktop_6/code.html` | desktop | NEEDS_REVIEW | — | A01, A02 | 1 → 9 |
| D07 | Присідання зі штангою / деталі вправи | `design-reference/stitch_web_platform/desktop_7/code.html` | desktop | NEEDS_REVIEW | — | C02 | 3 → 9 |
| D08 | Редагування профілю / фітнес-поля | `design-reference/stitch_web_platform/desktop_8/code.html` | desktop | NEEDS_REVIEW | — | P01–P03 | 2 → 9 |
| D09 | Історія ваги / графік і журнал | `design-reference/stitch_web_platform/desktop_9/code.html` | desktop | CANDIDATE | weight | P01, P03–P05 | 2/8 → 9 |
| D10 | Каталог вправ / фільтри | `design-reference/stitch_web_platform/desktop_10/code.html` | desktop | CANDIDATE | — | C01, C02 | 3 → 9 |
| D11 | Деталі тренування / послідовність вправ | `design-reference/stitch_web_platform/desktop_11/code.html` | desktop | CANDIDATE | — | C04 | 3 → 9 |
| D12 | Історія ваги / порожній стан | `design-reference/stitch_web_platform/desktop_12/code.html` | desktop | VARIANT | weight | P04, P05 | 2/8 → 9 |
| M01 | Вхід / мобільна адаптація | `design-reference/stitch_web_platform/mobile_1/code.html` | mobile | VARIANT | login | A01, A03 | 1 → 9 |
| M02 | Мій профіль та історія ваги / мобільний складений вигляд | `design-reference/stitch_web_platform/mobile_2/code.html` | mobile | VARIANT, NEEDS_REVIEW | profile, weight | A05, P01, P03–P05 | 2/8 → 9 |
| A01 | Деталі запланованого тренування | `design-reference/stitch_web_platform(1)/stitch_web_platform/desktop_1/code.html` | desktop | CANDIDATE | — | S03, S04, S05, E01 | 5/7 → 9 |
| A02 | Редагування персональної програми / відкритий picker | `design-reference/stitch_web_platform(1)/stitch_web_platform/desktop_2/code.html` | desktop | CANDIDATE | — | G04–G06, C02 | 4 → 9 |
| A03 | Рекомендована програма / прийняття | `design-reference/stitch_web_platform(1)/stitch_web_platform/desktop_3/code.html` | desktop | CANDIDATE | — | G01, G03 | 4 → 9 |
| A04 | Мої програми / список | `design-reference/stitch_web_platform(1)/stitch_web_platform/desktop_4/code.html` | desktop | CANDIDATE | — | G02 | 4 → 9 |
| A05 | Календар тренувань / місяць і день | `design-reference/stitch_web_platform(1)/stitch_web_platform/desktop_5/code.html` | desktop | CANDIDATE | — | S01, S03 | 5 → 9 |
| A06 | Перенесення тренування / форма | `design-reference/stitch_web_platform(1)/stitch_web_platform/desktop_6/code.html` | desktop | CANDIDATE | — | S03, S04 | 5 → 9 |
| A07 | Тренування завершено / результат | `design-reference/stitch_web_platform(1)/stitch_web_platform/desktop_7/code.html` | desktop | CANDIDATE | — | E01 response, E03 | 7/8 → 9 |
| A08 | Завершення тренування / фактичні результати | `design-reference/stitch_web_platform(1)/stitch_web_platform/desktop_8/code.html` | desktop | NEEDS_REVIEW | — | S03 або C04, E01 | 7 → 9 |
| A09 | Скасування тренування / підтвердження | `design-reference/stitch_web_platform(1)/stitch_web_platform/desktop_9/code.html` | desktop | CANDIDATE | — | S03, S05, G08 | 7 → 9 |
| A10 | Деталі завершеного тренування / історичний факт | `design-reference/stitch_web_platform(1)/stitch_web_platform/desktop_10/code.html` | desktop | CANDIDATE | — | E03 | 8 → 9 |
| A11 | Моя статистика / підсумки | `design-reference/stitch_web_platform(1)/stitch_web_platform/desktop_11/code.html` | desktop | CANDIDATE | — | R01, P05 | 8 → 9 |
| A12 | Запланувати тренування / дата й джерело | `design-reference/stitch_web_platform(1)/stitch_web_platform/desktop_12/code.html` | desktop | CANDIDATE | — | G04 або C04, S02 | 5 → 9 |
| A13 | Історія тренувань / фільтри | `design-reference/stitch_web_platform(1)/stitch_web_platform/desktop_13/code.html` | desktop | CANDIDATE | — | E02 | 8 → 9 |
| A14 | Деталі моєї програми / стан і склад | `design-reference/stitch_web_platform(1)/stitch_web_platform/desktop_14/code.html` | desktop | NEEDS_REVIEW | — | G04, G07–G09, S01 | 5/7 → 9 |
| A15 | Мої бали / підсумок | `design-reference/stitch_web_platform(1)/stitch_web_platform/desktop_15/code.html` | desktop | CANDIDATE | — | M01, M02 | 8 → 9 |
| A16 | Історія нарахування балів | `design-reference/stitch_web_platform(1)/stitch_web_platform/desktop_16/code.html` | desktop | CANDIDATE | — | M02 | 8 → 9 |
| C01 | Каталог челенджів | `design-reference/stitch_web_platform(2)/stitch_web_platform/desktop_1/code.html` | desktop | NEEDS_REVIEW | — | H01 | 6/8 → 9 |
| C02 | Каталог досягнень | `design-reference/stitch_web_platform(2)/stitch_web_platform/desktop_2/code.html` | desktop | NEEDS_REVIEW | — | M03 | 8 → 9 |
| C03 | Рейтинг користувачів / opt-in діалог | `design-reference/stitch_web_platform(2)/stitch_web_platform/desktop_3/code.html` | desktop | NEEDS_REVIEW | — | A05, A06, L01 | 1/8 → 9 |
| C04 | Деталі челенджу / вступ | `design-reference/stitch_web_platform(2)/stitch_web_platform/desktop_4/code.html` | desktop | NEEDS_REVIEW | — | H02, H03 | 6/8 → 9 |
| C05 | Мої досягнення | `design-reference/stitch_web_platform(2)/stitch_web_platform/desktop_5/code.html` | desktop | NEEDS_REVIEW | — | M04 | 8 → 9 |
| C06 | Мої сповіщення / список | `design-reference/stitch_web_platform(2)/stitch_web_platform/desktop_6/code.html` | desktop | CANDIDATE | — | N01, N03 | 5 → 9 |
| C07 | Деталі сповіщення | `design-reference/stitch_web_platform(2)/stitch_web_platform/desktop_7/code.html` | desktop, PNG немає | NEEDS_REVIEW | — | N02, N03 | 5 → 9 |
| C08 | Мої челенджі | `design-reference/stitch_web_platform(2)/stitch_web_platform/desktop_8/code.html` | desktop | NEEDS_REVIEW | — | H04 | 8 → 9 |
| C09 | Налаштування акаунта / публічний рейтинг | `design-reference/stitch_web_platform(2)/stitch_web_platform/desktop_9/code.html` | desktop, PNG немає | NEEDS_REVIEW | — | A05, A06 | 1 → 9 |

## C. Вибрані основи для сторінок

Посилання ID ведуть до **точного Source HTML у таблиці B**. За відсутності альтернативного експорту вибір означає «єдиний наявний візуальний кандидат», не схвалення всіх полів чи текстів. Упевненість оцінює відповідність **призначення** сторінки; примітка фіксує невирішене. Три `VARIANT` використовуються всередині відповідних сторінок, тому окремих сторінок тут 37.

| Сторінка | Кандидат (Source HTML ID) | Альтернативи / стани | Чому цей кандидат | Упевненість / невизначеність |
|---|---|---|---|---|
| Головна | D00 | — | Єдиний dashboard | Середня; вилучити метрики без джерела в R01/M01/S01 |
| Запит reset | D02 | — | Окрема email-форма A07 | Висока; лишити однакове підтвердження для будь-якої адреси |
| Новий пароль | D01 | — | Покриває A08 і success | Середня; розвести success/invalid-token стани, захистити URL токена |
| Профіль | D03 | M02 (mobile) | Огляд Profile | Висока; показувати тільки P01/A05, не демодані |
| Вхід | D04 | M01 (mobile) | Повна desktop-форма | Середня; «запам'ятати мене» не має API-ефекту; M01 має session-ended overlay |
| Каталог тренувань | D05 | — | Пошук і картки C03 | Висока; фільтри лише контрактні |
| Реєстрація | D06 | — | Email/password форма відповідає A02 | Середня; виправити підказку 8→12 і звірити Django validators |
| Вправа | D07 | — | Єдиний detail-макет | Низька; C02 дає список, окремого `GET /exercises/{id}/` немає; деталь — із C02 або needs review |
| Редагування/створення профілю | D08 | — | Можна використати форму для P02/P03 | Середня; email read-only через A05, вік обчислює сервер |
| Історія ваги | D09 | D12 empty, M02 mobile | Єдиний повний графік/журнал | Висока; дані лише P04/P05, запис через P03 |
| Каталог вправ | D10 | — | Пошук і фільтри C02 | Висока; віддалені фото не входять в API |
| Деталі тренування | D11 | — | Склад C04 | Висока; shared каталог read-only |
| Деталі слота | A01 | — | S03 з контекстними діями | Висока; E01/S05 активні лише за серверним станом |
| Редактор програми | A02 | — | G05/G06 й picker C02 | Висока; заборонити edit completed/archived, не чіпати source Workout |
| Рекомендація | A03 | — | G01 з явним прийняттям G03 | Висока; обробити 404 без кандидата, 409 застарілої рекомендації |
| Мої програми | A04 | — | Стани/список G02 | Висока; archived — окремий фільтр, не статус |
| Календар | A05 | — | S01 для діапазону Kyiv | Висока; missed — похідна ознака |
| Перенесення | A06 | — | S04 форма | Висока; оновлюється той самий slot/reminder |
| Підсумок завершення | A07 | — | Відповідь E01 | Висока; цифри лише із відповіді сервера, без локального нарахування |
| Форма фактичних результатів | A08 | — | E01 payload | Середня; перевірити структуру nullable actual-значень та retry-key |
| Підтвердження скасування | A09 | — | S05 modal/state | Висока; повторний S05=200, після нього перечитати G08 |
| Завершене заняття | A10 | — | E03 snapshot | Висока; жодних edit/delete |
| Моя статистика | A11 | — | R01/P05 | Висока; період Kyiv, no-data state |
| Планування | A12 | — | S02 | Висока; один із program/shared source, reminder створює сервер |
| Історія занять | A13 | — | E02 | Висока; окремий світлий фон — перевірити після токенізації |
| Деталі програми | A14 | — | G04/G08 та контекстні G07/G09 | Середня; `<title>`/H1 помилково «Мій баланс», уточнити копірайт; G09 лише після допустимого стану |
| Мої бали | A15 | — | M01 summary + M02 recent | Висока; жодних локальних балів |
| Історія балів | A16 | — | M02 | Висока; бонус +50 — окрема ledger-транзакція за BR |
| Каталог челенджів | C01 | — | H01 | Середня; критерії BR-022 ще не підтверджено |
| Каталог досягнень | C02 | — | M03 | Середня; критерії BR-021 ще не підтверджено |
| Рейтинг | C03 | — | L01 з A06 modal | Середня; видимі лише public_alias/points/rank; перевірити приватність |
| Деталі челенджу | C04 | — | H02/H03 | Середня; прогрес і пороги тільки з backend після gate |
| Мої досягнення | C05 | — | M04 | Середня; snapshot нагороди, пороги не хардкодити |
| Список сповіщень | C06 | — | N01 | Висока; mark read лише через N03 |
| Деталі сповіщення | C07 | — | N02/N03 | Середня; PNG відсутній, HTML скрипт маркування потребує перевірки |
| Мої челенджі | C08 | — | H04 | Середня; прогрес із CompletedSession після вступу |
| Налаштування акаунта | C09 | — | A05/A06; popup C03 | Середня; PNG відсутній, не показувати незадокументовані account mutations |

## D. Відсутні MVP-сторінки

**0 доведено відсутніх окремих React-сторінок**, якщо D08 використати і для першого P02, і для P03, а D01 — для success/expired-token станів. Окремий екран для кожної REST-операції не потрібний. Це не означає готовність усіх станів: потрібно спроєктувати P02 empty/first-profile, A08 invalid/expired link, порожні колекції, 401/403/404/409 та помилки форм. Для D07 вирішити, чи detail отримує вибрану вправу зі списку C02; окремої детальної API-операції немає. R02/R03 і CRUD shared каталогу належать Django Admin та **не є пропущеними React-сторінками**.

## E. Спільні компоненти й структура

Мінімальний каркас: `AppShell` з responsive `Sidebar`/top bar/mobile navigation, `PageHeader`/breadcrumb, `ContentContainer`; `Button`, `Card`, `Badge`, `Field` (input/select/checkbox), `Modal`/`ConfirmDialog`, `Alert`, `EmptyState`, `LoadingState`, пагінація. Доменно перевикористовувати тільки повторювані `WorkoutCard`, `ProgramCard`, `SessionCard`, `ExerciseResultFields`, `WeightHistoryChart`, `PointsSummary`, `NotificationCard`. Achievement/Challenge cards варто виділити після підтвердження їхніх реальних полів. Візуальні джерела: оболонка D00/D03/A04/C06, форми D04/D06/D08/A12, картки D05/D10/A04/C01, діалоги A02/A09/C03, графіки D09/A11.

Пропозиція без негайної перебудови: лишити `frontend/src/app/api.ts` точкою входу HTTP; додавати DTO і API-функції у `app/` або `features/<feature>/api.ts`, сторінки в `pages/` чи `features/<feature>/`, спільні елементи в `components/`, токени в `styles/`. `App.tsx` і наявний auth-зріз змінювати лише малими інтеграційними кроками; маршрутизатор не додавати до появи потреби в реальних deep links A08/деталей. Session bootstrap через A05, A01 перед unsafe-діями, `credentials:"same-origin"` та CSRF header зберегти. Server state перечитувати після mutation, особливо S05→G08; локальний state — лише введення/відкриті діалоги. Не показувати hardcoded Stitch-дані як реальні дані користувача; до появи endpoint показувати явний недоступний стан або не відкривати маршрут.

## F. Nordic Vitality: токени

Три `DESIGN.md` ідентичні, тож **конфліктів між архівами немає**. Усередині самого документа YAML-палітра й prose розходяться: YAML `primary #002620`, `secondary #006b54`, `background #e8fef6`, `on-surface #0c1f1a`; prose називає `#173C35`, `#27866C`, `#F6F8F5`, `#182B26`. У HTML переважають YAML-класи, але A13 візуально світліший; остаточний canvas/кнопку треба звірити на перших інтегрованих екранах. До узгодження не змішувати випадково обидві палітри в одному компоненті.

Майбутній `styles/tokens.css` може мати семантичні `--color-background`, `--color-surface`, `--color-surface-raised`, `--color-text`, `--color-text-muted`, `--color-primary`, `--color-primary-hover`, `--color-accent-lime`, `--color-accent-orange`, `--color-success/warning/error/info`, `--color-border`, `--color-focus`; шкали `--space-1/2/4/6/8`, `--radius-sm/md/lg/pill`, `--shadow-card/hover/modal`, `--font-ui`. Початкові значення для screen-accurate prototype брати з YAML: surface `#e8fef6`, white container `#ffffff`, primary `#002620`, primary-container `#173c35`, secondary `#006b54`, text `#0c1f1a`, error `#ba1a1a`. Prose lime `#C5EA78` й orange `#F4A261` — акценти, не заміна semantic success/error. Manrope із системним fallback; перевірити українську кирилицю й контраст.

Сітка 8px із 4px кроком для дрібних елементів; desktop sidebar 260px, header 72px, 12 колонок/24px gutters/32px margins; tablet 8 колонок/16px gutters; mobile одна або дві колонки/16px margins, bottom nav 56px. Cards 16px radius, inputs/buttons 10–12px, badges pill. Картки — тонка межа і легка тінь, modals — виразніша тінь/overlay. Стани primary/secondary/outline/destructive/focus/disabled задавати семантичними варіантами. Брейкпойнти спершу перевірити в HTML і viewport-тестах, не вважати кожен `sm:/md:/lg:` доказом якісної мобільної версії.

## G. Мапа інтеграції API

`G` = гість, `U` = автентифікований власник; усі приватні ID перевіряє backend, чужий і відсутній ресурс повертають однаковий 404. Кожна mutation потребує CSRF; `U` додатково потребує auth session. 401 веде до входу, 403 CSRF — до безпечного оновлення cookie, 400 показує `fields`, 404/409 мають окремі повідомлення. Нижче `GET → mutation` позначає дані й дію; «—» означає read-only. API ID деталізовані в [REST-контракті](../architecture/rest-api.md), не нові маршрути. Фаза в B — найраніший backend зріз, React доводиться в 9-й; A07/A08 — додаткове незавершене завдання фази 1.

| Сторінки / джерела | GET → mutation | Права, параметри й суттєві помилки |
|---|---|---|
| D04/M01 вхід, D06 реєстрація | A01 → A03/A02; після успіху A05 | G; email/password; 400 validators, 401 credentials, 403 CSRF, 429; remember-me не передавати |
| D02 reset request, D01 reset confirm | A01 → A07/A08 | G; email або `uid,token,new_password`; 200 без enumeration, 400 invalid/expired token чи password; прибрати token з URL і сторонні ресурси |
| D03 профіль, D08 форма, M02 адаптація | A05/P01 → P02 або P03 | U; P02 лише без Profile; сім обов'язкових fitness полів і optional first/last; 404 profile_missing, 409 profile_exists, 400 межі; email read-only |
| D09/D12/M02 вага | P01/P04/P05 → P03 | U; P04 `page,page_size`, P05 `start_date,end_date` Kyiv, P03 `weight_kg` decimal-string; 400 period/value, 404 no Profile; порожні точки `[]` |
| D05 workout catalog | C01/C03 → — | G/U; `category,search,page,page_size`; 400 filter, 429 |
| D10 exercise catalog, D07 exercise detail | C01/C02 → — | G/U; C02 `category,search,page,page_size`; 400 filter; D07 без окремого detail endpoint, потрібен доступний елемент C02 |
| D11 workout detail | C04 → — | G/U; `workout id`; 404 hidden/missing; no catalog mutation |
| A03 recommendation | G01 → G03 | U + Profile; `program_template_id` поточної рекомендації; 404 profile/recommendation, 409 stale ID |
| A04 programs | G02 → — | U; `status`, `archived`, `page,page_size`; 400 filter, 401 |
| A02 editor | G04/C02 → G05/G06 | U owner; program/entry IDs, full nonempty exercises array; 400 composition, 404 foreign, 409 completed/archived |
| A14 program detail | G04/G08/S01 → G07/G09 | U owner; program ID; G07 потребує ≥1 noncancelled slot, G09 409 active/planned; після змін reread G08 |
| A05 calendar | S01 → — | U; `start_date,end_date` разом, optional `status,user_program_id,page,page_size`; 400 period/status, 404 чужа програма |
| A12 schedule | G04 або C04, S01 → S02 | U; timezone-aware `scheduled_at`, рівно одне program/shared джерело; 400 past/ambiguous, 404 source, 409 state |
| A01 scheduled detail | S03 → переходи до S04/S05/E01 | U owner; slot ID; 404 foreign; для action серверний status/is_missed, не локальна дата як істина |
| A06 reschedule | S03 → S04 | U owner; `scheduled_at`; 400 time, 404, 409 closed/cancelled; той самий ID |
| A09 cancel | S03 → S05; потім G08 | U owner; `{}`; 404 чужий, 409 лише нове недозволене скасування; retry already-cancelled = 200 |
| A08 completion form, A07 result | S03 або C04 → E01; результат E01/E03 | U; `Idempotency-Key` UUID v4, duration decimal-string, фактичні `results`; 400 form/key, 404 source, 409 state/key race; бали/kcal лише з E01 |
| A13 history, A10 historical detail | E02/E03 → — | U owner; E02 `start_date,end_date,source_workout_id,page,page_size`; 400 filter, 404 foreign fact; snapshots immutable |
| A11 statistics, D00 dashboard | R01/P05 та за потреби M01/S01 → — | U; R01/P05 обов'язкові Kyiv `start_date,end_date`; 400 period; нулі/no-data, не фіктивні кроки чи сон |
| A15 points, A16 transaction history | M01/M02 → — | U; M01 optional `start_date,end_date` парою, M02 також `point_kind,page,page_size`; 400 filter; ledger authoritative |
| C02 achievement catalog, C05 my achievements | M03/M04 → — | U; `page,page_size`; BR-021 gate, read-only; no user-triggered unlock |
| C01 challenge catalog, C04 detail, C08 my challenges | H01/H02/H04 → H03 на C04 | U; H01 `state,page,page_size`, H04 `status,page,page_size`; H03 `{}`, 200 retry, 404 hidden, 409 expired; BR-022 gate |
| C03 leaderboard, C09 settings | A05/L01 → A06 | U; L01 `period,anchor_date,page,page_size`, A06 `public_alias,leaderboard_opt_in`; 400 alias/period, 403 CSRF; public list лише alias/points/rank |
| C06 notifications, C07 detail | N01/N02 → N03 | U owner; N01 `status,is_current,page,page_size`; N02/N03 notification ID; 404 foreign/invisible/cancelled; read лише за явною дією, retry 200 |

R02/R03 споживає лише Django Admin з окремим permission. API-операції C01–C04 catalog GET доступні гостю; це не привід надавати гостьовий доступ до власних програм чи фактів. Уся пагінація та фільтри обмежені саме задокументованими параметрами. Decimal-значення передавати рядками; дати періоду тлумачити в `Europe/Kyiv` з `[start,end)`. Наявний `api.ts` підтримує тільки GET/POST/PATCH; майбутній G06 PUT вимагатиме розширення того самого CSRF-aware клієнта.

## H. Конфлікти й технічні ризики

| Пріоритет | Де | Ризик / рішення перед реалізацією |
|---|---|---|
| Високий | D06 | Підказка «Мін. 8 символів» суперечить Django `MinimumLengthValidator` 12; форма не має активних name/consent полів, і їх не слід додавати через HTML-коментарі. Показувати валідатори сервера. |
| Високий | D04/M01 | «Запам'ятати мене» не має контрактного параметра; cookie в backend уже має 7-денний строк. Прибрати нефункціональний toggle або окремо погодити зміну сесійної політики. |
| Високий | D01/D02 | A07/A08 ще не реалізовані. A07 не розкриває існування email; A08 token не має потрапляти в логи, referer, сторонні fonts/scripts на reset route. |
| Високий | D08/D09/D12 | Email не змінюється P03, `age` read-only; новий `WeightEntry` створює P02/P03 лише при реальній зміні ваги. Графік і порожній стан з persisted P04/P05, не з намальованих точок. |
| Високий | A02/A14/A01/A09 | `draft/active/completed` — status, `is_archived` окремо; G07, G09, E01, S05 залежать від server-state і lock. Прогрес та бонус не обчислювати з карток; після S05 перечитати G08. |
| Високий | A07/A08/A10/A15/A16 | E01 використовує фактичні вправи й один idempotency key для повтору тієї самої спроби; calories/points/server snapshot є авторитетними. Історичні факти не редагуються, bonus +50 лише окремим ledger-записом за умовами BR. |
| Високий | C01/C02/C04/C05/C08 | Критерії BR-021/022 ще `PROPOSED` і проходять Business Decision Gate фази 6. Будь-які числа, нагороди, дати й progress у HTML — демо; не вшивати їх як правила. |
| Високий | C03/C09 | Opt-in й непорожній public alias обов'язкові для публічного списку. Не виводити email, first/last name, приватний Profile або чужу історію. |
| Високий | C06/C07 | N01/N02 GET не позначають read; N03 тільки явна дія. `is_current=false` і `status=read` — різні ознаки; невидимий/cancelled reminder дає 404. |
| Середній | D00/A11 | Макетні метрики на кшталт steps, pulse, sleep та графіки можуть не мати джерела в R01/P05/M01/S01. Прибрати чи замінити підтриманими даними, не вигадувати endpoint. |
| Середній | D07 | C02 не має detail GET; не будувати маршрут, що при refresh потребує неіснуючого API. Залишити detail у контексті списку або переглянути потребу. |
| Середній | Усі HTML | 40/40 використовують Tailwind CDN; 90 `<script>`, 29 `<style>`, 81 inline-style attributes, 42 inline event attributes і 681 `href="#"`/порожніх посилань. Це прототипи, не production JSX: переносити лише структуру, тексти й перевірені стани; `onclick`/JS переписати типізованими React handlers. |
| Середній | D07/D10 та всі fonts/icons | D07 містить Unsplash image, D10 — шість Googleusercontent image URLs. Є зовнішні Manrope/Material Symbols. Локальних app-asset фото немає; PNG — screenshots, не фото. Для інтеграції потрібні погоджені ліцензовані локальні assets або нейтральні placeholder без залежності від випадкових URL. |
| Середній | C07/C09, A02/A03/A05/A09/A13 | PNG C07/C09 відсутні; деякі інші PNG мають обрізання/чорну смугу або нетиповий фон. Перевірити HTML у browser на вузьких і широких viewport перед точним копіюванням. |
| Середній | Усі HTML | У 38/40 є responsive utility breakpoints, але це не доводить keyboard/mobile UX. Audit не знайшов duplicate `id` у межах файлу, проте при збиранні кількох фрагментів в одну React-сторінку ID можуть зіткнутися. Перевірити label/control, focus trap, Escape, aria-live, контраст, touch target і 320px layout. |

## I. Порядок малих інтеграційних зрізів

1. **Foundation без доменних mock.** Узгодити palette-конфлікт на D04/D06/D03, винести мінімальні токени/поле/кнопку/alert і responsive auth layout. Чинний A01–A06 frontend зберегти; D04/M01/D06 підключити до нього, перевірити cookies/CSRF, 400/401/403, mobile/keyboard. Це перший рекомендований batch, бо API вже існує.
2. **Reset A07/A08 (додаток фази 1).** Після backend реалізації D02/D01 з безпечним token route, generic confirmation, invalid/expired state та throttling. Не завантажувати зовнішні ресурси на token route.
3. **Профіль/вага (фаза 2).** D03/D08/M02, D09/D12 з P01–P04; P05 chart підключити у фазі 8. Перший профіль через P02 на тій самій формі; перевірити відсутній профіль і persisted вагу.
4. **Read-only каталог (фаза 3).** D05/D10/D11, рішення D07 без нового API; типізовані DTO, фільтри, пагінація й 404.
5. **Програми (фаза 4).** A03/A04/A02/A14 тільки G01–G06; activation/сесійні кнопки з'являються з фазою 5. Перевірити stale recommendation і owner 404.
6. **Планування й нагадування (фаза 5).** A05/A12/A01/A06/C06/C07, G07, S01–S04, N01–N03. Після state mutation перечитати canonical GET; окремо перевірити Kyiv DST та видимість reminder.
7. **Execution (фаза 7).** A08/A07/A09 із E01/S05/G09 разом після транзакційної backend готовності фази 6. Перевірити idempotency, 409, rollback, повторне S05=200 і G08 refresh.
8. **Read projections (фаза 8), UI polish (фаза 9).** A10/A13/A11/D00/A15/A16/C03/C09 й P05/E02–E03/M01–M02/L01/R01. Achievement/challenge екрани C01/C02/C04/C05/C08 лише після BR-021/022 gate та API. Завершити маршрути, responsive/a11y, E2E з реальною PostgreSQL, без показу демоданих як persisted.

Для кожного зрізу: один реальний API-flow, loading/empty/error/success, доступ/owner, mobile+desktop viewport, keyboard і типізований payload; тестувати ту саму поведінку, а не повторювати статичний макет. Ніяких iframe, копій CDN-скриптів або нових бібліотек у межах цього аудиту.
