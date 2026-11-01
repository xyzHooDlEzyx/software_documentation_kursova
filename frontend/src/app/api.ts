export type Account = {
  id: number;
  email: string;
  public_alias: string | null;
  leaderboard_opt_in: boolean;
};

export type ApiErrorBody = {
  error: {
    code: string;
    message: string;
    fields: Record<string, string[]>;
    request_id: string;
  };
};

export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly code: string,
    readonly fields: Record<string, string[]> = {},
    message = "Запит не виконано.",
  ) {
    super(message);
  }
}

/** All browser API calls stay on the Vite origin in local development. */
export function apiFetch(path: `/api/v1/${string}`, init: RequestInit = {}) {
  return fetch(path, { ...init, credentials: "same-origin" });
}

function csrfCookie(): string | null {
  const value = document.cookie
    .split("; ")
    .find((part) => part.startsWith("csrftoken="))
    ?.slice("csrftoken=".length);
  return value ? decodeURIComponent(value) : null;
}

export async function initializeCsrf(): Promise<void> {
  const response = await apiFetch("/api/v1/auth/csrf/");
  if (!response.ok) throw await asApiError(response);
  await response.json();
}

async function asApiError(response: Response): Promise<ApiError> {
  try {
    const body = (await response.json()) as ApiErrorBody;
    if (body.error && typeof body.error.code === "string") {
      return new ApiError(
        response.status,
        body.error.code,
        body.error.fields ?? {},
        body.error.message,
      );
    }
  } catch {
    // An HTML proxy error or interrupted response has no API envelope.
  }
  return new ApiError(response.status, "request_failed");
}

async function request<T>(
  path: `/api/v1/${string}`,
  method: "GET" | "POST" | "PATCH",
  body?: object,
): Promise<T> {
  const unsafe = method !== "GET";
  if (unsafe && !csrfCookie()) await initializeCsrf();
  const headers: Record<string, string> = { Accept: "application/json" };
  if (body !== undefined) headers["Content-Type"] = "application/json";
  if (unsafe) {
    // Read the cookie on every mutation: Django rotates it after login.
    const token = csrfCookie();
    if (!token) throw new ApiError(0, "csrf_unavailable", {}, "Не вдалося отримати CSRF cookie.");
    headers["X-CSRFToken"] = token;
  }
  let response: Response;
  try {
    response = await apiFetch(path, {
      method,
      headers,
      ...(body === undefined ? {} : { body: JSON.stringify(body) }),
    });
  } catch {
    throw new ApiError(0, "network_error", {}, "Немає зв’язку із сервером.");
  }
  if (!response.ok) throw await asApiError(response);
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

export function register(email: string, password: string) {
  return request<Account>("/api/v1/auth/register/", "POST", { email, password });
}

export function login(email: string, password: string) {
  return request<Account>("/api/v1/auth/login/", "POST", { email, password });
}

export function logout() {
  return request<void>("/api/v1/auth/logout/", "POST");
}

export function currentUser() {
  return request<Account>("/api/v1/me/", "GET");
}

export function updateLeaderboard(public_alias: string | null, leaderboard_opt_in: boolean) {
  return request<Account>("/api/v1/me/", "PATCH", {
    public_alias,
    leaderboard_opt_in,
  });
}
