# Frontend UI and routing architecture

## Scope

The frontend is a React 19 and TypeScript single page application built with Vite 8, Tailwind CSS v4 and shadcn/ui source components. `App.tsx` owns the React Router 7 browser router and session provider; `main.tsx` mounts it under React Strict Mode. Route components live in `src/pages/`, shared public/authenticated layouts in `src/components/layout/`, and accessible UI primitives in `src/components/ui/`. API calls and their DTOs remain in `src/app/api.ts`.

## Styling and component boundary

`src/styles/tokens.css` is the authoritative Nordic Vitality palette, typography and spacing source. `src/style.css` imports Tailwind and maps those values through CSS-first `@theme inline` aliases; Tailwind utilities and shadcn-derived component classes consume the same semantic roles. `components.json` selects the shadcn `base-nova` style and the existing `@/` alias. The project keeps one exported implementation per primitive in `src/components/ui/`; pages compose those shared primitives and do not introduce local buttons or inputs. Tailwind's Vite plugin is registered alongside the existing React plugin and preserves the `/api/v1` Django proxy. SCSS is not part of the initial stack.

The current primitive set is deliberately small. `Button` uses Base UI's button with CVA variants; its exported `buttonVariants` styles route links consistently. `Switch` and `Checkbox` use Base UI controls while retaining the existing labelled `checked`/`onChange` props. `TextInput`, `Card`, `Alert`, and `LoadingState` remain the canonical shared wrappers, styled with semantic Tailwind utilities. There is no second generated component catalog. Component files contain no requests; the pages keep the existing Django session and CSRF-aware API client.

## Routes currently implemented

| Path | Access | Page and data source |
|---|---|---|
| `/login` | Public | Login form; A01/A03 through the existing API client. |
| `/register` | Public | Registration form; A01/A02. Registration returns to login and does not sign the user in automatically. |
| `/` | Authenticated session | Account welcome page using A05 account data; links only to implemented settings. |
| `/settings` | Authenticated session | Public alias and leaderboard opt-in using A05/A06. |
| `*` | Public fallback | Not-found message. |

`PublicLayout` and `AuthenticatedLayout` provide nested route shells. The authenticated navigation exposes only the home and settings routes. Planned screens are added only alongside their real API support; no route or navigation item presents a planned operation as functional.

## Session and access behavior

`AuthProvider` owns `loading`, `authenticated`, `guest`, or `error` bootstrap state. Bootstrap obtains the CSRF cookie with A01, then checks the server session with A05. A confirmed A05 401 means guest and allows protected routes to redirect to `/login`, retaining the requested path for post-login navigation. A network failure or other non-401 error remains an error; protected content stays closed and offers a retry. A failed connection never converts an unknown session into a guest session.

HTTP 401 handling is endpoint-specific. An invalid login is displayed on the login form and does not change auth state. A 401 from a protected request clears the account and returns to login. A network error preserves the account. A 403 remains an API/CSRF or permission error and does not redirect to login. All requests continue to use the shared API client, same-origin credentials, and its CSRF-cookie rotation behavior.

## Page behavior

Login and registration share one typed form component but have separate URLs and mode-specific validation. Client validation preserves the current email check and 12-character registration minimum; the API remains authoritative and field errors are shown next to inputs. Registration success navigates to login with a confirmation. Settings preserve draft values after failed saves, update displayed account state from the A06 response, and show field and request errors. Logout navigates to login after success; a failed network logout keeps the authenticated state and surfaces the error.

The home page deliberately reports only the current account and links to implemented account settings. It contains no sample workouts, invented metrics, or placeholder domain records.

## Navigation and component tests

`BrowserRouter` owns URL changes, nested routes, browser history, and deep links. Tests that render `App` should use a memory history or set the test location before rendering; route tests should assert URL-visible behavior and use the real route tree. Authentication tests should cover the session bootstrap states, login versus private-route 401 behavior, status-0 network failures, and redirects with a return path. Strict Mode can start more than one bootstrap attempt in development, so bootstrap responses are versioned and stale attempts cannot overwrite a later login or retry.
