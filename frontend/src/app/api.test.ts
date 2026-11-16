import { beforeEach, expect, test, vi } from "vitest";

import { ApiError, login, logout, request } from "./api";

beforeEach(() => {
  document.cookie = "csrftoken=; Max-Age=0; path=/";
  vi.unstubAllGlobals();
});

test("unsafe requests initialize CSRF and read the latest cookie", async () => {
  const seen: string[] = [];
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      if (input === "/api/v1/auth/csrf/") {
        document.cookie = "csrftoken=first; path=/";
        return new Response(JSON.stringify({ csrf_token: "first" }), { status: 200 });
      }
      seen.push((init?.headers as Record<string, string>)["X-CSRFToken"]);
      expect(init?.credentials).toBe("same-origin");
      if (input === "/api/v1/auth/login/") {
        document.cookie = "csrftoken=second; path=/";
        return new Response(
          JSON.stringify({ id: 1, email: "a@example.test", public_alias: null, leaderboard_opt_in: false }),
          { status: 200 },
        );
      }
      return new Response(null, { status: 204 });
    }),
  );
  await login("a@example.test", "CorrectHorse2026!");
  await logout();
  expect(seen).toEqual(["first", "second"]);
});

test("API error envelope exposes status and field messages", async () => {
  document.cookie = "csrftoken=ready; path=/";
  vi.stubGlobal(
    "fetch",
    vi.fn(
      async () =>
        new Response(
          JSON.stringify({
            error: {
              code: "validation_error",
              message: "Некоректні дані.",
              fields: { email: ["Некоректний email."] },
              request_id: "req-test",
            },
          }),
          { status: 400 },
        ),
    ),
  );
  await expect(login("bad", "secret")).rejects.toMatchObject({
    status: 400,
    code: "validation_error",
    fields: { email: ["Некоректний email."] },
  } satisfies Partial<ApiError>);
});

test("401 on a protected endpoint calls the handler, auth endpoints do not", async () => {
  const { setUnauthorizedHandler, currentUser } = await import("./api");
  const handler = vi.fn();
  setUnauthorizedHandler(handler);
  document.cookie = "csrftoken=ready; path=/";
  vi.stubGlobal(
    "fetch",
    vi.fn(
      async () =>
        new Response(
          JSON.stringify({
            error: { code: "invalid_credentials", message: "Невірні дані.", fields: {}, request_id: "r" },
          }),
          { status: 401 },
        ),
    ),
  );
  await expect(login("a@example.test", "wrong-password")).rejects.toMatchObject({ status: 401 });
  expect(handler).not.toHaveBeenCalled();
  await expect(currentUser()).rejects.toMatchObject({ status: 401 });
  expect(handler).toHaveBeenCalledTimes(1);
  setUnauthorizedHandler(null);
});

test("network failure while fetching the CSRF cookie becomes a typed network error", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn(async () => {
      throw new TypeError("Failed to fetch");
    }),
  );
  await expect(login("a@example.test", "secret")).rejects.toMatchObject({ status: 0, code: "network_error" });
});

test("request merges an extra idempotency header with JSON and CSRF headers", async () => {
  document.cookie = "csrftoken=ready; path=/";
  vi.stubGlobal(
    "fetch",
    vi.fn(async (_input: RequestInfo | URL, init?: RequestInit) => {
      expect(init?.headers).toMatchObject({
        Accept: "application/json",
        "Content-Type": "application/json",
        "X-CSRFToken": "ready",
        "Idempotency-Key": "8e1af87d-5516-4f64-bc87-74806c61cc28",
      });
      return new Response(JSON.stringify({ id: 1 }), { status: 201 });
    }),
  );
  await request(
    "/api/v1/completed-sessions/",
    "POST",
    {},
    {
      headers: { "Idempotency-Key": "8e1af87d-5516-4f64-bc87-74806c61cc28" },
    },
  );
});
