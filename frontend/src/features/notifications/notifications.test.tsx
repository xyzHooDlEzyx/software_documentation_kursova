import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, test, vi } from "vitest";

import App from "@/App";
import { json, mockApi } from "@/test/mockApi";
import { useVisiblePolling } from "./useVisiblePolling";

beforeEach(() => {
  document.cookie = "csrftoken=token; path=/";
});
afterEach(() => {
  vi.useRealTimers();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

test("notification is read only after the explicit action and unread badge uses N01 count", async () => {
  window.history.replaceState(null, "", "/notifications");
  const item = {
    id: 9,
    scheduled_session_id: 92,
    type: "workout_reminder",
    visible_at: "2026-11-18T15:00:00Z",
    status: "pending",
    read_at: null,
    is_current: true,
  };
  const slot = {
    id: 92,
    scheduled_at: "2026-11-18T20:50:00Z",
    status: "planned",
    is_missed: false,
    user_program_id: null,
    user_program_workout_id: null,
    source_workout_id: 8,
    reschedule_history: [],
    completed_session_id: null,
    reminder: { id: 9, visible_at: item.visible_at, status: "pending", is_current: true },
  };
  const workout = { id: 8, name: "Силове тренування Б", description: "", category: "strength", exercises: [] };
  let read = false;
  const { calls } = mockApi({
    "GET /api/v1/notifications/?page=1&page_size=10": () =>
      json({
        count: 1,
        next: null,
        previous: null,
        results: [read ? { ...item, status: "read", read_at: "2026-11-18T15:05:00Z" } : item],
      }),
    "GET /api/v1/notifications/?status=pending&page=1&page_size=1": () =>
      json({ count: read ? 0 : 1, next: null, previous: null, results: read ? [] : [item] }),
    "GET /api/v1/scheduled-sessions/92/": () => json(slot),
    "GET /api/v1/workouts/8/": () => json(workout),
    "POST /api/v1/notifications/9/read/": () => {
      read = true;
      return json({ ...item, status: "read", read_at: "2026-11-18T15:05:00Z" });
    },
  });
  render(<App />);
  expect(await screen.findAllByRole("link", { name: "Сповіщення, непрочитаних: 1" })).toHaveLength(2);
  expect(calls.some((call) => call.method === "POST")).toBe(false);
  expect(await screen.findByRole("link", { name: "Відкрити тренування" })).toHaveAttribute("href", "/schedule/92");
  expect(await screen.findByRole("link", { name: "Силове тренування Б" })).toHaveAttribute("href", "/notifications/9");
  expect(screen.getByText(/Тренування о 18\.11\.2026, 22:50 · нагадування з 18\.11\.2026, 17:00/)).toBeInTheDocument();
  expect(calls.some((call) => call.method === "POST")).toBe(false);
  fireEvent.click(screen.getByRole("button", { name: "Позначити прочитаним" }));
  await waitFor(() => expect(calls.filter((call) => call.method === "POST")).toHaveLength(1));
  expect(await screen.findByText("Сповіщення позначено прочитаним.")).toBeInTheDocument();
});

test("notification detail resolves workout and scheduled time without marking it read", async () => {
  window.history.replaceState(null, "", "/notifications/9");
  const item = {
    id: 9,
    scheduled_session_id: 92,
    type: "workout_reminder",
    visible_at: "2026-11-18T15:00:00Z",
    status: "pending",
    read_at: null,
    is_current: true,
  };
  const slot = {
    id: 92,
    scheduled_at: "2026-11-18T20:50:00Z",
    status: "planned",
    is_missed: false,
    user_program_id: null,
    user_program_workout_id: null,
    source_workout_id: 8,
    reschedule_history: [],
    completed_session_id: null,
    reminder: { id: 9, visible_at: item.visible_at, status: "pending", is_current: true },
  };
  const { calls } = mockApi({
    "GET /api/v1/notifications/9/": () => json(item),
    "GET /api/v1/scheduled-sessions/92/": () => json(slot),
    "GET /api/v1/workouts/8/": () =>
      json({ id: 8, name: "Силове тренування Б", description: "", category: "strength", exercises: [] }),
  });
  render(<App />);
  expect(await screen.findByRole("heading", { name: "Силове тренування Б" })).toBeInTheDocument();
  expect(screen.getByText(/Тренування о 18\.11\.2026, 22:50/)).toBeInTheDocument();
  expect(calls.some((call) => call.method === "POST")).toBe(false);
});

function PollHarness({ refresh }: { refresh: () => void }) {
  useVisiblePolling(refresh, 1000);
  return null;
}

test("polling refreshes on timer and focus, and stops while hidden or unmounted", () => {
  vi.useFakeTimers();
  let visibility = "visible";
  vi.spyOn(document, "visibilityState", "get").mockImplementation(() => visibility as DocumentVisibilityState);
  const refresh = vi.fn();
  const view = render(<PollHarness refresh={refresh} />);
  expect(refresh).toHaveBeenCalledTimes(1);
  act(() => vi.advanceTimersByTime(1000));
  expect(refresh).toHaveBeenCalledTimes(2);
  visibility = "hidden";
  act(() => {
    vi.advanceTimersByTime(2000);
    window.dispatchEvent(new Event("focus"));
  });
  expect(refresh).toHaveBeenCalledTimes(2);
  visibility = "visible";
  act(() => document.dispatchEvent(new Event("visibilitychange")));
  expect(refresh).toHaveBeenCalledTimes(3);
  view.unmount();
  act(() => vi.advanceTimersByTime(2000));
  expect(refresh).toHaveBeenCalledTimes(3);
});
