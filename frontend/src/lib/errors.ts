import { ApiError } from "@/app/api";

export function errorMessage(reason: unknown, fallback = "Не вдалося виконати запит. Спробуйте ще раз.") {
  return reason instanceof ApiError ? reason.message : fallback;
}

/** Field messages from the API error envelope, joined per field. */
export function fieldErrors(reason: unknown): Record<string, string> {
  if (!(reason instanceof ApiError)) return {};
  return Object.fromEntries(Object.entries(reason.fields).map(([field, messages]) => [field, messages.join(" ")]));
}

export function isApiError(reason: unknown, status: number, code?: string) {
  return reason instanceof ApiError && reason.status === status && (code === undefined || reason.code === code);
}
