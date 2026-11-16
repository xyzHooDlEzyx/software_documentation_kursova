import { vi } from "vitest";

export const account = { id: 7, email: "member@example.test", public_alias: null, leaderboard_opt_in: false };

export function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
}

export function apiError(
  code: string,
  status: number,
  fields: Record<string, string[]> = {},
  message = "Помилка запиту.",
) {
  return json({ error: { code, message, fields, request_id: "req-test" } }, status);
}

export type Call = { method: string; path: string; body: unknown; headers: Headers };
type Handler = (call: Call) => Response | Promise<Response>;

/**
 * Fetch stub for a signed-in user. `routes` maps "METHOD /path" (query string
 * included when present) to a handler; unknown routes fail the test loudly.
 */
export function mockApi(routes: Record<string, Handler>) {
  const calls: Call[] = [];
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const path = String(input);
    const method = init?.method ?? "GET";
    const body = typeof init?.body === "string" ? JSON.parse(init.body) : undefined;
    const call = { method, path, body, headers: new Headers(init?.headers) };
    calls.push(call);
    if (path === "/api/v1/auth/csrf/") {
      document.cookie = "csrftoken=token; path=/";
      return json({ csrf_token: "token" });
    }
    const handler =
      routes[`${method} ${path}`] ??
      (method === "GET" && path === "/api/v1/me/" ? () => json(account) : undefined) ??
      (method === "GET" && path === "/api/v1/notifications/?status=pending&page=1&page_size=1"
        ? () => json({ count: 0, next: null, previous: null, results: [] })
        : undefined);
    if (!handler) throw new Error(`Unexpected request ${method} ${path}`);
    return handler(call);
  });
  vi.stubGlobal("fetch", fetchMock);
  return { calls, fetchMock };
}
