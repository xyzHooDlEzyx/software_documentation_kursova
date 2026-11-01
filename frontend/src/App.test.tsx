import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, test, vi } from "vitest";

import App from "./App";
import type { Account } from "./app/api";

const account = {
  id: 7,
  email: "member@example.test",
  public_alias: null,
  leaderboard_opt_in: false,
};

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function apiError(code: string, status: number, fields = {}) {
  return json({ error: { code, message: "Помилка запиту.", fields, request_id: "req-test" } }, status);
}

beforeEach(() => {
  window.history.replaceState(null, "", "/login");
  document.cookie = "csrftoken=; Max-Age=0; path=/";
});

afterEach(() => {
  vi.unstubAllGlobals();
});

test("guest sees validation before requests", async () => {
  const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
    if (input === "/api/v1/auth/csrf/") {
      document.cookie = "csrftoken=initial; path=/";
      return json({ csrf_token: "initial" });
    }
    return apiError("authentication_required", 401);
  });
  vi.stubGlobal("fetch", fetchMock);
  render(<App />);
  await screen.findByRole("button", { name: "Увійти" });
  fireEvent.click(screen.getByRole("link", { name: "Зареєструватися" }));
  await screen.findByRole("button", { name: "Створити акаунт" });
  fireEvent.change(screen.getByLabelText("Email"), { target: { value: "bad" } });
  fireEvent.change(screen.getByLabelText("Пароль"), { target: { value: "short" } });
  fireEvent.click(screen.getByRole("button", { name: "Створити акаунт" }));
  expect(screen.getByText("Введіть коректну email-адресу.")).toBeInTheDocument();
  expect(screen.getByText("Пароль має містити щонайменше 12 символів.")).toBeInTheDocument();
  expect(fetchMock).toHaveBeenCalledTimes(2);
});

test("register, login, save alias, and logout use the rotated CSRF cookie", async () => {
  let loggedIn = false;
  let current: Account = account;
  const csrfHeaders: string[] = [];
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const path = String(input);
    if (path === "/api/v1/auth/csrf/") {
      document.cookie = "csrftoken=before-login; path=/";
      return json({ csrf_token: "before-login" });
    }
    if (path === "/api/v1/me/" && (!init || init.method === "GET")) {
      return loggedIn ? json(current) : apiError("authentication_required", 401);
    }
    csrfHeaders.push((init?.headers as Record<string, string>)["X-CSRFToken"]);
    if (path === "/api/v1/auth/register/") return json(account, 201);
    if (path === "/api/v1/auth/login/") {
      loggedIn = true;
      document.cookie = "csrftoken=after-login; path=/";
      return json(account);
    }
    if (path === "/api/v1/me/" && init?.method === "PATCH") {
      current = { ...account, public_alias: "Fit", leaderboard_opt_in: true };
      return json(current);
    }
    if (path === "/api/v1/auth/logout/") {
      loggedIn = false;
      return new Response(null, { status: 204 });
    }
    throw new Error(`Unexpected request ${path}`);
  });
  vi.stubGlobal("fetch", fetchMock);
  render(<App />);
  await screen.findByRole("button", { name: "Увійти" });
  fireEvent.click(screen.getByRole("link", { name: "Зареєструватися" }));
  await screen.findByRole("button", { name: "Створити акаунт" });
  fireEvent.change(screen.getByLabelText("Email"), { target: { value: account.email } });
  fireEvent.change(screen.getByLabelText("Пароль"), { target: { value: "CorrectHorse2026!" } });
  fireEvent.click(screen.getByRole("button", { name: "Створити акаунт" }));
  await screen.findByText("Акаунт створено. Тепер увійдіть.");
  fireEvent.change(screen.getByLabelText("Пароль"), { target: { value: "CorrectHorse2026!" } });
  fireEvent.click(screen.getByRole("button", { name: "Увійти" }));
  await screen.findByText(account.email);
  fireEvent.click((await screen.findAllByRole("link", { name: "Налаштування" }))[0]);
  await screen.findByRole("heading", { name: "Налаштування" });
  fireEvent.change(screen.getByLabelText("Псевдонім"), { target: { value: "Fit" } });
  fireEvent.click(screen.getByLabelText("Показувати мене в рейтингу"));
  fireEvent.click(screen.getByRole("button", { name: "Зберегти" }));
  await screen.findByText("Налаштування рейтингу збережено.");
  fireEvent.click(screen.getByRole("button", { name: "Вийти" }));
  await screen.findByText("Ви вийшли з акаунта.");
  expect(window.location.pathname).toBe("/login");
  expect(csrfHeaders).toEqual([
    "before-login", "before-login", "after-login", "after-login",
  ]);
});

test("reload restores the server session and unauthorized settings returns to login", async () => {
  let authenticated = true;
  vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const path = String(input);
    if (path === "/api/v1/auth/csrf/") {
      document.cookie = "csrftoken=current; path=/";
      return json({ csrf_token: "current" });
    }
    if (path === "/api/v1/me/" && !init?.method) return json(account);
    if (path === "/api/v1/me/" && init?.method === "GET") {
      return authenticated ? json(account) : apiError("authentication_required", 401);
    }
    if (path === "/api/v1/me/" && init?.method === "PATCH") {
      authenticated = false;
      return apiError("authentication_required", 401);
    }
    throw new Error(`Unexpected request ${path}`);
  }));
  render(<App />);
  await screen.findByText(account.email);
  fireEvent.click((await screen.findAllByRole("link", { name: "Налаштування" }))[0]);
  await screen.findByRole("heading", { name: "Налаштування" });
  fireEvent.click(screen.getByRole("button", { name: "Зберегти" }));
  await waitFor(() => expect(screen.getByRole("button", { name: "Увійти" })).toBeInTheDocument());
  expect(window.location.pathname).toBe("/login");
});

test("direct settings URL redirects a guest to login", async () => {
  window.history.replaceState(null, "", "/settings");
  vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
    if (String(input) === "/api/v1/auth/csrf/") {
      document.cookie = "csrftoken=guest; path=/";
      return json({ csrf_token: "guest" });
    }
    if (String(input) === "/api/v1/me/") return apiError("authentication_required", 401);
    throw new Error(`Unexpected request ${String(input)}`);
  }));

  render(<App />);

  await screen.findByRole("button", { name: "Увійти" });
  expect(window.location.pathname).toBe("/login");
  expect(screen.queryByRole("heading", { name: "Налаштування" })).not.toBeInTheDocument();
});

test("session bootstrap network error can be retried", async () => {
  let csrfAttempts = 0;
  vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
    if (String(input) === "/api/v1/auth/csrf/") {
      csrfAttempts += 1;
      if (csrfAttempts === 1) throw new TypeError("disconnected");
      document.cookie = "csrftoken=recovered; path=/";
      return json({ csrf_token: "recovered" });
    }
    if (String(input) === "/api/v1/me/") return apiError("authentication_required", 401);
    throw new Error(`Unexpected request ${String(input)}`);
  }));

  render(<App />);

  await screen.findByText("Не вдалося перевірити сесію. Спробуйте ще раз.");
  fireEvent.click(screen.getByRole("button", { name: "Спробувати ще раз" }));
  await screen.findByRole("button", { name: "Увійти" });
  expect(csrfAttempts).toBe(2);
});

test("invalid credentials and network failures are visible", async () => {
  let loginNetworkFailure = false;
  vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
    const path = String(input);
    if (path === "/api/v1/auth/csrf/") {
      document.cookie = "csrftoken=current; path=/";
      return json({ csrf_token: "current" });
    }
    if (path === "/api/v1/me/") return apiError("authentication_required", 401);
    if (path === "/api/v1/auth/login/") {
      if (loginNetworkFailure) throw new Error("disconnected");
      return apiError("invalid_credentials", 401);
    }
    throw new Error(`Unexpected request ${path}`);
  }));
  render(<App />);
  await screen.findByRole("button", { name: "Увійти" });
  fireEvent.change(screen.getByLabelText("Email"), { target: { value: account.email } });
  fireEvent.change(screen.getByLabelText("Пароль"), { target: { value: "WrongPassword2026!" } });
  fireEvent.click(screen.getByRole("button", { name: "Увійти" }));
  await screen.findByText("Помилка запиту.");
  loginNetworkFailure = true;
  fireEvent.click(screen.getByRole("button", { name: "Увійти" }));
  await screen.findByText("Немає зв’язку із сервером.");
});
