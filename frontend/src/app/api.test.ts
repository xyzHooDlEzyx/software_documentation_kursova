import { beforeEach, expect, test, vi } from "vitest";

import { ApiError, login, logout } from "./api";

beforeEach(() => {
  document.cookie = "csrftoken=; Max-Age=0; path=/";
  vi.unstubAllGlobals();
});

test("unsafe requests initialize CSRF and read the latest cookie", async () => {
  const seen: string[] = [];
  vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    if (input === "/api/v1/auth/csrf/") {
      document.cookie = "csrftoken=first; path=/";
      return new Response(JSON.stringify({ csrf_token: "first" }), { status: 200 });
    }
    seen.push((init?.headers as Record<string, string>)["X-CSRFToken"]);
    expect(init?.credentials).toBe("same-origin");
    if (input === "/api/v1/auth/login/") {
      document.cookie = "csrftoken=second; path=/";
      return new Response(JSON.stringify({ id: 1, email: "a@example.test", public_alias: null, leaderboard_opt_in: false }), { status: 200 });
    }
    return new Response(null, { status: 204 });
  }));
  await login("a@example.test", "CorrectHorse2026!");
  await logout();
  expect(seen).toEqual(["first", "second"]);
});

test("API error envelope exposes status and field messages", async () => {
  document.cookie = "csrftoken=ready; path=/";
  vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify({
    error: { code: "validation_error", message: "Некоректні дані.", fields: { email: ["Некоректний email."] }, request_id: "req-test" },
  }), { status: 400 })));
  await expect(login("bad", "secret")).rejects.toMatchObject({
    status: 400,
    code: "validation_error",
    fields: { email: ["Некоректний email."] },
  } satisfies Partial<ApiError>);
});
