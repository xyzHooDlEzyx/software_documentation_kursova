import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, test, vi } from "vitest";

import App from "./App";
import { clearResetCredentialsMemory } from "./pages/PasswordResetConfirmPage";

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function apiError(
  code: string,
  status: number,
  fields: Record<string, string[]> = {},
  message = "Помилка запиту.",
) {
  return json(
    {
      error: {
        code,
        message,
        fields,
        request_id: "req-reset-test",
      },
    },
    status,
  );
}

beforeEach(() => {
  clearResetCredentialsMemory();
  window.history.replaceState(null, "", "/login");
  document.cookie = "csrftoken=; Max-Age=0; path=/";
  window.localStorage.clear();
  window.sessionStorage.clear();
});

afterEach(() => {
  vi.unstubAllGlobals();
});

test("navigates from login to password reset request page (D02) and back to login", async () => {
  const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
    const path = String(input);
    if (path === "/api/v1/auth/csrf/") {
      document.cookie = "csrftoken=csrf-nav; path=/";
      return json({ csrf_token: "csrf-nav" });
    }
    if (path === "/api/v1/me/") {
      return apiError("authentication_required", 401);
    }
    throw new Error(`Unexpected request ${path}`);
  });
  vi.stubGlobal("fetch", fetchMock);

  render(<App />);

  await screen.findByRole("button", { name: "Увійти" });
  fireEvent.click(screen.getByRole("link", { name: "Забули пароль?" }));

  await screen.findByRole("heading", { name: "Відновлення пароля" });
  expect(window.location.pathname).toBe("/forgot-password");

  fireEvent.click(screen.getByRole("link", { name: "Повернутися до входу" }));
  await screen.findByRole("button", { name: "Увійти" });
  expect(window.location.pathname).toBe("/login");
});

test("D02 validates email, submits password reset with CSRF, shows generic confirmation, and handles errors without losing email", async () => {
  let resetMode: "success" | "rate_limit" | "network" = "success";
  const resetRequests: { init?: RequestInit }[] = [];

  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const path = String(input);
    if (path === "/api/v1/auth/csrf/") {
      document.cookie = "csrftoken=csrf-d02; path=/";
      return json({ csrf_token: "csrf-d02" });
    }
    if (path === "/api/v1/me/") {
      return apiError("authentication_required", 401);
    }
    if (path === "/api/v1/auth/password-reset/" && init?.method === "POST") {
      resetRequests.push({ init });
      if (resetMode === "rate_limit") {
        return apiError(
          "rate_limit_exceeded",
          429,
          {},
          "Забагато спроб відновлення пароля. Спробуйте пізніше.",
        );
      }
      if (resetMode === "network") {
        throw new TypeError("network down");
      }
      return json({
        message:
          "Якщо акаунт із такою адресою існує, ми надішлемо інструкції для відновлення пароля.",
      });
    }
    throw new Error(`Unexpected request ${path}`);
  });
  vi.stubGlobal("fetch", fetchMock);

  window.history.replaceState(null, "", "/forgot-password");
  render(<App />);

  await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2));
  await screen.findByRole("heading", { name: "Відновлення пароля" });

  // 1. Client validation rejects invalid email without calling POST /api/v1/auth/password-reset/
  const emailInput = screen.getByLabelText("Електронна пошта");
  fireEvent.change(emailInput, { target: { value: "invalid-email" } });
  fireEvent.click(screen.getByRole("button", { name: "Надіслати інструкції" }));

  expect(screen.getByText("Введіть коректну email-адресу.")).toBeInTheDocument();
  expect(resetRequests).toHaveLength(0);

  // 2. Valid email submits POST /api/v1/auth/password-reset/ with X-CSRFToken and credentials: "same-origin"
  fireEvent.change(emailInput, { target: { value: "member@example.test" } });
  fireEvent.click(screen.getByRole("button", { name: "Надіслати інструкції" }));

  await screen.findByText(
    "Якщо акаунт із такою адресою існує, ми надішлемо інструкції для відновлення пароля.",
  );
  expect(screen.getByRole("button", { name: "Надіслати повторно" })).toBeInTheDocument();
  expect(resetRequests).toHaveLength(1);
  expect(resetRequests[0].init?.credentials).toBe("same-origin");
  expect((resetRequests[0].init?.headers as Record<string, string>)["X-CSRFToken"]).toBe(
    "csrf-d02",
  );
  expect(JSON.parse(String(resetRequests[0].init?.body))).toEqual({
    email: "member@example.test",
  });

  // 3. API error (429 rate_limit_exceeded and network error) surfaces in error alert without losing typed email
  resetMode = "rate_limit";
  fireEvent.click(screen.getByRole("button", { name: "Надіслати повторно" }));
  await screen.findByText("Забагато спроб відновлення пароля. Спробуйте пізніше.");
  expect(screen.getByLabelText("Електронна пошта")).toHaveValue("member@example.test");

  resetMode = "network";
  fireEvent.click(screen.getByRole("button", { name: "Надіслати повторно" }));
  await screen.findByText("Немає зв’язку із сервером.");
  expect(screen.getByLabelText("Електронна пошта")).toHaveValue("member@example.test");
});

test("D01 scrubs recovery token from URL immediately and never stores it in localStorage, sessionStorage, or cookies", async () => {
  const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
    const path = String(input);
    if (path === "/api/v1/auth/csrf/") {
      document.cookie = "csrftoken=csrf-d01; path=/";
      return json({ csrf_token: "csrf-d01" });
    }
    if (path === "/api/v1/me/") {
      return apiError("authentication_required", 401);
    }
    throw new Error(`Unexpected request ${path}`);
  });
  vi.stubGlobal("fetch", fetchMock);

  window.history.replaceState(null, "", "/reset-password/uid-41/secret-token-xyz");
  render(<App />);

  expect(window.location.pathname).toBe("/reset-password");
  expect(window.location.href).not.toContain("secret-token-xyz");
  expect(window.location.href).not.toContain("uid-41");
  expect(window.location.pathname).not.toContain("secret-token-xyz");
  expect(window.location.pathname).not.toContain("uid-41");

  expect(JSON.stringify(window.localStorage)).not.toContain("secret-token-xyz");
  expect(JSON.stringify(window.localStorage)).not.toContain("uid-41");
  expect(JSON.stringify(window.sessionStorage)).not.toContain("secret-token-xyz");
  expect(JSON.stringify(window.sessionStorage)).not.toContain("uid-41");
  expect(document.cookie).not.toContain("secret-token-xyz");
  expect(document.cookie).not.toContain("uid-41");

  expect(
    screen.getByRole("heading", { name: "Встановлення нового пароля" }),
  ).toBeInTheDocument();
  await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2));
});

test("D01 preserves form state on intentional browser refresh and renders invalid link state on direct navigation without token", async () => {
  const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
    const path = String(input);
    if (path === "/api/v1/auth/csrf/") {
      document.cookie = "csrftoken=csrf-refresh; path=/";
      return json({ csrf_token: "csrf-refresh" });
    }
    if (path === "/api/v1/me/") {
      return apiError("authentication_required", 401);
    }
    throw new Error(`Unexpected request ${path}`);
  });
  vi.stubGlobal("fetch", fetchMock);

  // Initial navigation with uid & token scrubs URL and saves to history.state
  window.history.replaceState(null, "", "/reset-password/uid-41/secret-token-xyz");
  const firstRender = render(<App />);
  await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2));
  expect(window.location.pathname).toBe("/reset-password");
  expect(
    screen.getByRole("heading", { name: "Встановлення нового пароля" }),
  ).toBeInTheDocument();
  firstRender.unmount();

  // Simulate browser refresh: in-memory variable is reset on page reload, but history.state persists
  const savedHistoryState = window.history.state as unknown;
  clearResetCredentialsMemory();
  window.history.replaceState(savedHistoryState, "", "/reset-password");

  const refreshedRender = render(<App />);
  await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(4));
  expect(
    screen.getByRole("heading", { name: "Встановлення нового пароля" }),
  ).toBeInTheDocument();
  expect(screen.getByLabelText("Новий пароль")).toBeInTheDocument();
  refreshedRender.unmount();

  // Direct link to /reset-password without token parameters or history state renders Invalid/Expired Link state
  clearResetCredentialsMemory();
  window.history.replaceState(null, "", "/reset-password");

  render(<App />);
  await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(6));
  expect(
    screen.getByText("Термін дії посилання вичерпано або посилання недійсне."),
  ).toBeInTheDocument();

  fireEvent.click(screen.getByRole("link", { name: "Запросити нове посилання" }));
  await screen.findByRole("heading", { name: "Відновлення пароля" });
  expect(window.location.pathname).toBe("/forgot-password");
});

test("D01 handles client validation, server field validation, expired token error, and successful password reset", async () => {
  let confirmMode: "field_error" | "expired" | "success" = "field_error";
  const confirmCalls: { init?: RequestInit }[] = [];

  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const path = String(input);
    if (path === "/api/v1/auth/csrf/") {
      document.cookie = "csrftoken=csrf-confirm; path=/";
      return json({ csrf_token: "csrf-confirm" });
    }
    if (path === "/api/v1/me/") {
      return apiError("authentication_required", 401);
    }
    if (path === "/api/v1/auth/password-reset/confirm/" && init?.method === "POST") {
      confirmCalls.push({ init });
      if (confirmMode === "field_error") {
        return apiError(
          "validation_error",
          400,
          { new_password: ["Цей пароль занадто поширений."] },
          "Перевірте введені дані.",
        );
      }
      if (confirmMode === "expired") {
        return apiError(
          "reset_token_invalid_or_expired",
          400,
          {},
          "Термін дії посилання вичерпано або посилання недійсне.",
        );
      }
      return json({
        message: "Пароль оновлено. Увійдіть із новим паролем.",
      });
    }
    throw new Error(`Unexpected request ${path}`);
  });
  vi.stubGlobal("fetch", fetchMock);

  window.history.replaceState(null, "", "/reset-password/uid-41/secret-token-xyz");
  const firstRender = render(<App />);
  await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2));

  // 1. Client validation rejects short password (< 12 chars) and mismatched confirmation without calling A08
  fireEvent.change(screen.getByLabelText("Новий пароль"), {
    target: { value: "short" },
  });
  fireEvent.change(screen.getByLabelText("Підтвердження нового пароля"), {
    target: { value: "different" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Зберегти новий пароль" }));

  expect(
    screen.getByText("Пароль має містити щонайменше 12 символів."),
  ).toBeInTheDocument();
  expect(screen.getByText("Паролі не співпадають.")).toBeInTheDocument();
  expect(confirmCalls).toHaveLength(0);

  // 2. Server 400 validation_error on fields.new_password displays server validator message and keeps form usable
  fireEvent.change(screen.getByLabelText("Новий пароль"), {
    target: { value: "CommonPass123!" },
  });
  fireEvent.change(screen.getByLabelText("Підтвердження нового пароля"), {
    target: { value: "CommonPass123!" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Зберегти новий пароль" }));

  await screen.findByText("Цей пароль занадто поширений.");
  expect(screen.getByLabelText("Новий пароль")).toBeInTheDocument();
  expect(confirmCalls).toHaveLength(1);

  // 3. Server 400 reset_token_invalid_or_expired transitions to Invalid/Expired Link state and clears history.state
  confirmMode = "expired";
  fireEvent.change(screen.getByLabelText("Новий пароль"), {
    target: { value: "StrongerPass2026!" },
  });
  fireEvent.change(screen.getByLabelText("Підтвердження нового пароля"), {
    target: { value: "StrongerPass2026!" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Зберегти новий пароль" }));

  await screen.findByRole("heading", { name: "Посилання недійсне" });
  expect(
    screen.getByText("Термін дії посилання вичерпано або посилання недійсне."),
  ).toBeInTheDocument();
  expect(window.history.state).toBeNull();
  firstRender.unmount();

  // 4. Successful POST /api/v1/auth/password-reset/confirm/ (200 OK)
  confirmMode = "success";
  window.history.replaceState(null, "", "/reset-password/uid-99/valid-token-abc");
  render(<App />);
  await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(6));

  fireEvent.change(screen.getByLabelText("Новий пароль"), {
    target: { value: "BrandNewPass2026!" },
  });
  fireEvent.change(screen.getByLabelText("Підтвердження нового пароля"), {
    target: { value: "BrandNewPass2026!" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Зберегти новий пароль" }));

  await screen.findByText("Пароль оновлено. Увійдіть із новим паролем.");
  expect(confirmCalls).toHaveLength(3);
  const lastCall = confirmCalls[2];
  expect(lastCall.init?.credentials).toBe("same-origin");
  expect((lastCall.init?.headers as Record<string, string>)["X-CSRFToken"]).toBe(
    "csrf-confirm",
  );
  expect(JSON.parse(String(lastCall.init?.body))).toEqual({
    uid: "uid-99",
    token: "valid-token-abc",
    new_password: "BrandNewPass2026!",
  });
  expect(window.history.state).toBeNull();

  // Does NOT auto-login; clicking "Перейти до входу" navigates to /login as guest
  fireEvent.click(screen.getByRole("link", { name: "Перейти до входу" }));
  await screen.findByRole("button", { name: "Увійти" });
  expect(window.location.pathname).toBe("/login");
});
