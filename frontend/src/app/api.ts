export type Account = {
  id: number;
  email: string;
  public_alias: string | null;
  leaderboard_opt_in: boolean;
};

export type MessageResponse = {
  message: string;
};

/** Page envelope shared by all paginated list endpoints. */
export type Paginated<T> = {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
};

export type HttpMethod = "GET" | "POST" | "PATCH" | "PUT" | "DELETE";
type ApiPath = `/api/v1/${string}`;

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
export function apiFetch(path: ApiPath, init: RequestInit = {}) {
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
      return new ApiError(response.status, body.error.code, body.error.fields ?? {}, body.error.message);
    }
  } catch {
    // An HTML proxy error or interrupted response has no API envelope.
  }
  return new ApiError(response.status, "request_failed");
}

let unauthorizedHandler: (() => void) | null = null;

/**
 * Registers the single place that reacts to an expired session. Auth endpoints
 * are excluded: their 401 (e.g. invalid credentials) is a form error, not a
 * lost session.
 */
export function setUnauthorizedHandler(handler: (() => void) | null) {
  unauthorizedHandler = handler;
}

/** Appends defined, non-empty query parameters to an API path. */
export function withQuery(
  path: ApiPath,
  params: Record<string, string | number | boolean | null | undefined>,
): ApiPath {
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null || value === "") continue;
    query.set(key, String(value));
  }
  const text = query.toString();
  return (text ? `${path}?${text}` : path) as ApiPath;
}

export type RequestOptions = {
  headers?: Record<string, string>;
};

export async function request<T>(
  path: ApiPath,
  method: HttpMethod,
  body?: object,
  options: RequestOptions = {},
): Promise<T> {
  const unsafe = method !== "GET";
  if (unsafe && !csrfCookie()) {
    try {
      await initializeCsrf();
    } catch (reason) {
      if (reason instanceof ApiError) throw reason;
      throw new ApiError(0, "network_error", {}, "Немає зв’язку із сервером.");
    }
  }
  const headers: Record<string, string> = { Accept: "application/json", ...options.headers };
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
  if (!response.ok) {
    const error = await asApiError(response);
    if (response.status === 401 && !path.startsWith("/api/v1/auth/")) unauthorizedHandler?.();
    throw error;
  }
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

export function requestPasswordReset(email: string) {
  return request<MessageResponse>("/api/v1/auth/password-reset/", "POST", { email });
}

export function confirmPasswordReset(uid: string, token: string, new_password: string) {
  return request<MessageResponse>("/api/v1/auth/password-reset/confirm/", "POST", {
    uid,
    token,
    new_password,
  });
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
