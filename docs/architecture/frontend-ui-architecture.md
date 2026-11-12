# Frontend UI and routing architecture

## Scope

The frontend is a React 19 and TypeScript single page application built with Vite 8, Tailwind CSS v4 and shadcn/ui source components. `App.tsx` owns the React Router 7 browser router and session provider; `main.tsx` mounts it under React Strict Mode. Account route components live in `src/pages/`; domain screens live in `src/features/<domain>/` (`profile`, `catalog`, `programs`), each with its typed `api.ts` (request/response DTOs mirroring the DRF serializers) next to its pages and tests. Shared public/authenticated layouts are in `src/components/layout/`, accessible UI primitives in `src/components/ui/`, and cross-feature helpers (enum labels, Ukrainian number/date formatting and plurals, error mapping, the `useResource` loader) in `src/lib/`. `src/app/api.ts` holds only the session/CSRF-aware `request()` core, query building, the paginated envelope type and auth calls.

## Styling and component boundary

`src/styles/tokens.css` is the authoritative Nordic Vitality palette, typography and spacing source. `src/style.css` imports Tailwind and maps those values through CSS-first `@theme inline` aliases; Tailwind utilities and shadcn-derived component classes consume the same semantic roles. `components.json` selects the shadcn `base-nova` style and the existing `@/` alias. The project keeps one exported implementation per primitive in `src/components/ui/`; pages compose those shared primitives and do not introduce local buttons or inputs. Tailwind's Vite plugin is registered alongside the existing React plugin and preserves the `/api/v1` Django proxy. SCSS is not part of the initial stack.

The current primitive set is deliberately small. `Button` uses Base UI's button with CVA variants; its exported `buttonVariants` styles route links consistently. `Switch` and `Checkbox` use Base UI controls while retaining the existing labelled `checked`/`onChange` props. `TextInput`, `Select`, `Card`, `Badge`, `Alert`, `EmptyState`, `Pagination` and `LoadingState` remain the canonical shared wrappers, styled with semantic Tailwind utilities. There is no second generated component catalog. Component files contain no requests; the pages keep the existing Django session and CSRF-aware API client.

## Routes currently implemented

| Path | Access | Page and data source |
|---|---|---|
| `/login` | Public | Login form; A01/A03 through the existing API client. |
| `/register` | Public | Registration form; A01/A02. Registration returns to login and does not sign the user in automatically. |
| `/forgot-password`, `/password-reset` | Public | Password reset request; A07. |
| `/reset-password/:uid/:token` | Public | New password form; A08. The token is moved out of the URL immediately. |
| `/` | Authenticated session | Welcome page with links to profile, catalog and programs. |
| `/profile` | Authenticated session | Create profile when P01 returns 404 `profile_missing` (P02); otherwise overview and edit (P03 sends only changed fields, so an unchanged weight adds no WeightEntry) and weight history with an SVG line chart (P04). |
| `/catalog` | Authenticated session | Workouts (C03) or exercises (C02) with category chips from C01 and debounced search; filters and page are kept in the URL. |
| `/catalog/workouts/:id` | Authenticated session | Ordered exercises with category-specific recommended parameters (C04). |
| `/programs` | Authenticated session | Own programs with status/archive filters (G02). |
| `/programs/recommendation` | Authenticated session | Strategy recommendation with its reason (G01); accepting copies the template (G03). 409 `recommendation_mismatch` reloads the proposal; missing profile links to `/profile`. |
| `/programs/:id` | Authenticated session | Program detail (G04) with rename/description (G05); exercise names are resolved from C02. |
| `/programs/:id/workouts/:entryId` | Authenticated session | Composition editor (G06): add, remove, reorder exercises of the same category; only parameters valid for the category are sent; per-exercise server errors are mapped to readable lines. |
| `/settings` | Authenticated session | Public alias and leaderboard opt-in using A05/A06. |
| `*` | Public fallback | Not-found message. |

`PublicLayout` and `AuthenticatedLayout` provide nested route shells. The authenticated navigation exposes home, profile, catalog, programs and settings. Planned screens (schedule, workout completion, statistics, social features, reports) are added only alongside their real API support; no route or navigation item presents a planned operation as functional.

## Session and access behavior

`AuthProvider` owns `loading`, `authenticated`, `guest`, or `error` bootstrap state. Bootstrap obtains the CSRF cookie with A01, then checks the server session with A05. A confirmed A05 401 means guest and allows protected routes to redirect to `/login`, retaining the requested path for post-login navigation. A network failure or other non-401 error remains an error; protected content stays closed and offers a retry. A failed connection never converts an unknown session into a guest session.

HTTP 401 handling is endpoint-specific. An invalid login is displayed on the login form and does not change auth state. A 401 from any protected request is handled centrally: `request()` calls the handler that `AuthProvider` registers (`setUnauthorizedHandler`), which clears the account, so `RequireAuth` returns to login with the current path. Endpoints under `/api/v1/auth/` are excluded because their 401 is a form error, not a lost session. A network error preserves the account. A 403 remains an API/CSRF or permission error and does not redirect to login. All requests continue to use the shared API client, same-origin credentials, and its CSRF-cookie rotation behavior.

## Page behavior

Login and registration share one typed form component but have separate URLs and mode-specific validation. Client validation preserves the current email check and 12-character registration minimum; the API remains authoritative and field errors are shown next to inputs. Registration success navigates to login with a confirmation. Settings preserve draft values after failed saves, update displayed account state from the A06 response, and show field and request errors. Logout navigates to login after success; a failed network logout keeps the authenticated state and surfaces the error.

The home page links only to implemented sections. No page contains sample workouts, invented metrics, or placeholder domain records; progress values come from the API (draft programs honestly show 0%).

## Navigation and component tests

`BrowserRouter` owns URL changes, nested routes, browser history, and deep links. Tests that render `App` should use a memory history or set the test location before rendering; route tests should assert URL-visible behavior and use the real route tree. Authentication tests should cover the session bootstrap states, login versus private-route 401 behavior, status-0 network failures, and redirects with a return path. Strict Mode can start more than one bootstrap attempt in development, so bootstrap responses are versioned and stale attempts cannot overwrite a later login or retry.
