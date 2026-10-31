/** All browser API calls stay on the Vite origin in local development. */
export function apiFetch(path: `/api/v1/${string}`, init: RequestInit = {}) {
  return fetch(path, { ...init, credentials: "same-origin" });
}
