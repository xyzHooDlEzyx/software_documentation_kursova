import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, test, vi } from "vitest";

import App from "@/App";
import { apiError, json, mockApi } from "@/test/mockApi";
import { clearSessionNameCache } from "./names";
import { reminderDescription } from "./SessionDetailPage";

const workout = { id: 8, name: "Силове А", description: "", category: "strength", exercises: [] };
const baseProgram = {
  id: 41,
  name: "Мій баланс",
  description: "",
  fitness_goal: "maintenance",
  status: "draft",
  is_archived: false,
  source_program_template_id: 12,
  source_program_template_name_snapshot: "Баланс 3",
  bonus_target_sessions: null,
  progress: { total_planned: 1, completed_planned: 0, percent: "0.0" },
  completion_snapshot: null,
  bonus_earned: false,
  workouts: [
    { entry_id: 501, position: 1, source_workout_id: 8, name: "Силовий блок", category: "strength", exercises: [] },
  ],
};
const exercises = { count: 0, next: null, previous: null, results: [] };

beforeEach(() => {
  document.cookie = "csrftoken=token; path=/";
  clearSessionNameCache();
});
afterEach(() => vi.unstubAllGlobals());

test("calendar requests the half-open Monday-to-Monday period and renders resolved names", async () => {
  window.history.replaceState(null, "", "/schedule?week=2026-11-18");
  const { calls } = mockApi({
    "GET /api/v1/scheduled-sessions/?start_date=2026-11-16&end_date=2026-11-23&page=1&page_size=100": () =>
      json({
        count: 1,
        next: null,
        previous: null,
        results: [
          {
            id: 92,
            scheduled_at: "2026-11-18T16:00:00Z",
            status: "planned",
            is_missed: false,
            user_program_id: null,
            user_program_workout_id: null,
            source_workout_id: 8,
          },
        ],
      }),
    "GET /api/v1/workouts/8/": () => json(workout),
  });
  render(<App />);
  expect(await screen.findByText("Силове А")).toBeInTheDocument();
  expect(screen.getByText("Ср, 18.11")).toBeInTheDocument();
  expect(calls.some((call) => call.path.includes("start_date=2026-11-16&end_date=2026-11-23"))).toBe(true);
});

test("successful scheduling keeps the confirmation and resets time to prevent a duplicate submit", async () => {
  window.history.replaceState(null, "", "/programs/41");
  const created = {
    id: 92,
    scheduled_at: "2027-01-15T08:30:00Z",
    status: "planned",
    is_missed: false,
    user_program_id: 41,
    user_program_workout_id: 501,
    source_workout_id: 8,
    reschedule_history: [],
    completed_session_id: null,
    reminder: { id: 5, visible_at: "2027-01-15T07:30:00Z", status: "pending", is_current: true },
  };
  const { calls } = mockApi({
    "GET /api/v1/user-programs/41/": () => json(baseProgram),
    "GET /api/v1/exercises/?page=1&page_size=100": () => json(exercises),
    "POST /api/v1/scheduled-sessions/": () => json(created, 201),
  });
  render(<App />);
  fireEvent.click(await screen.findByRole("button", { name: "Запланувати" }));
  fireEvent.change(screen.getByLabelText("Дата"), { target: { value: "2027-01-15" } });
  const timeInput = screen.getByLabelText("Час (Київ)");
  fireEvent.change(timeInput, { target: { value: "10:30" } });
  fireEvent.click(screen.getAllByRole("button", { name: "Запланувати" })[1]);
  expect(await screen.findByText(/Тренування заплановано/)).toBeInTheDocument();
  expect(timeInput).toHaveValue("");
  fireEvent.click(screen.getAllByRole("button", { name: "Запланувати" })[1]);
  expect(await screen.findByText("Оберіть час.")).toBeInTheDocument();
  expect(screen.getByText(/Тренування заплановано/)).toBeInTheDocument();
  expect(calls.filter((call) => call.method === "POST")).toHaveLength(1);
  expect(screen.getByRole("link", { name: "Відкрити в розкладі" })).toHaveAttribute("href", "/schedule/92");
  fireEvent.click(screen.getByRole("button", { name: "Закрити" }));
  expect(screen.queryByLabelText("Час (Київ)")).not.toBeInTheDocument();
});

test("the schedule form can be closed without submitting", async () => {
  window.history.replaceState(null, "", "/programs/41");
  const { calls } = mockApi({
    "GET /api/v1/user-programs/41/": () => json(baseProgram),
    "GET /api/v1/exercises/?page=1&page_size=100": () => json(exercises),
  });
  render(<App />);
  const toggle = await screen.findByRole("button", { name: "Запланувати" });
  fireEvent.click(toggle);
  expect(toggle).toHaveAttribute("aria-expanded", "true");
  fireEvent.click(screen.getByRole("button", { name: "Скасувати" }));
  expect(screen.queryByLabelText("Час (Київ)")).not.toBeInTheDocument();
  expect(toggle).toHaveAttribute("aria-expanded", "false");
  expect(calls.filter((call) => call.method === "POST")).toHaveLength(0);
});

test("reminder copy distinguishes future, visible, and stale reminders", () => {
  const now = new Date("2026-11-14T20:00:00Z");
  expect(reminderDescription({ visible_at: "2026-11-14T21:00:00Z", status: "pending", is_current: true }, now)).toMatch(
    /^Нагадування з’явиться о /,
  );
  expect(reminderDescription({ visible_at: "2026-11-14T19:00:00Z", status: "pending", is_current: true }, now)).toBe(
    "Нагадування: непрочитане",
  );
  expect(reminderDescription({ visible_at: "2026-11-14T19:00:00Z", status: "read", is_current: false }, now)).toBe(
    "Нагадування: прочитане, неактуальне",
  );
});

test("program scheduling sends exactly one source and Kyiv time, then shows field errors", async () => {
  window.history.replaceState(null, "", "/programs/41");
  let attempts = 0;
  const { calls } = mockApi({
    "GET /api/v1/user-programs/41/": () => json(baseProgram),
    "GET /api/v1/exercises/?page=1&page_size=100": () => json(exercises),
    "POST /api/v1/scheduled-sessions/": () => {
      attempts += 1;
      return attempts === 1
        ? apiError("validation_error", 400, { scheduled_at: ["Час уже минув."] }, "Перевірте час.")
        : json({}, 201);
    },
  });
  render(<App />);
  fireEvent.click(await screen.findByRole("button", { name: "Запланувати" }));
  fireEvent.change(screen.getByLabelText("Дата"), { target: { value: "2027-01-15" } });
  fireEvent.change(screen.getByLabelText("Час (Київ)"), { target: { value: "10:30" } });
  fireEvent.click(screen.getAllByRole("button", { name: "Запланувати" })[1]);
  expect(await screen.findByText("Час уже минув.")).toBeInTheDocument();
  expect(calls.find((call) => call.method === "POST")?.body).toEqual({
    scheduled_at: "2027-01-15T08:30:00Z",
    user_program_workout_id: 501,
    source_workout_id: null,
  });
});

test("reschedule patches the same slot and re-reads its detail", async () => {
  window.history.replaceState(null, "", "/schedule/92");
  let detailLoads = 0;
  const detail = {
    id: 92,
    scheduled_at: "2027-01-15T08:30:00Z",
    status: "planned",
    is_missed: false,
    user_program_id: null,
    user_program_workout_id: null,
    source_workout_id: 8,
    reschedule_history: [],
    completed_session_id: null,
    reminder: { id: 5, visible_at: "2027-01-15T07:30:00Z", status: "pending", is_current: true },
  };
  const { calls } = mockApi({
    "GET /api/v1/scheduled-sessions/92/": () => {
      detailLoads += 1;
      return json(detail);
    },
    "GET /api/v1/workouts/8/": () => json(workout),
    "PATCH /api/v1/scheduled-sessions/92/": () =>
      json({ ...detail, scheduled_at: "2027-01-16T09:00:00Z", reschedule_history: [detail.scheduled_at] }),
  });
  render(<App />);
  await screen.findByRole("heading", { name: "Силове А" });
  fireEvent.change(screen.getByLabelText("Нова дата"), { target: { value: "2027-01-16" } });
  fireEvent.change(screen.getByLabelText("Новий час (Київ)"), { target: { value: "11:00" } });
  fireEvent.click(screen.getByRole("button", { name: "Перенести" }));
  expect(await screen.findByText("Час тренування й нагадування оновлено.")).toBeInTheDocument();
  await waitFor(() => expect(detailLoads).toBeGreaterThan(1));
  expect(calls.find((call) => call.method === "PATCH")?.body).toEqual({ scheduled_at: "2027-01-16T09:00:00Z" });
});

test("cancel confirmation posts S05 and re-reads S03 before showing the cancelled state", async () => {
  window.history.replaceState(null, "", "/schedule/92");
  let detailLoads = 0;
  let programLoads = 0;
  const planned = {
    id: 92,
    scheduled_at: "2027-01-15T08:30:00Z",
    status: "planned",
    is_missed: false,
    user_program_id: 41,
    user_program_workout_id: 501,
    source_workout_id: 8,
    reschedule_history: [],
    completed_session_id: null,
    reminder: { id: 5, visible_at: "2027-01-15T07:30:00Z", status: "pending", is_current: true },
  };
  const cancelled = { ...planned, status: "cancelled", reminder: { ...planned.reminder, is_current: false } };
  const { calls } = mockApi({
    "GET /api/v1/scheduled-sessions/92/": () => {
      detailLoads += 1;
      return json(detailLoads === 1 ? planned : cancelled);
    },
    "GET /api/v1/user-programs/41/": () => {
      programLoads += 1;
      return json({
        ...baseProgram,
        workouts: [{ ...baseProgram.workouts[0], name: programLoads === 1 ? "Старий блок" : "Оновлений блок" }],
      });
    },
    "GET /api/v1/user-programs/41/progress/": () =>
      json({
        user_program_id: 41,
        status: "active",
        is_archived: false,
        total_planned: 0,
        completed_planned: 0,
        percent: "0.0",
        bonus_target_sessions: 3,
        bonus_earned: false,
        completion_snapshot: null,
      }),
    "POST /api/v1/scheduled-sessions/92/cancel/": () =>
      json({ id: 92, status: "cancelled", reminder: cancelled.reminder }),
  });
  render(<App />);
  expect(await screen.findByRole("heading", { name: "Старий блок" })).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Скасувати заняття" }));
  expect(screen.getByRole("button", { name: "Так, скасувати" })).toHaveFocus();
  fireEvent.click(screen.getByRole("button", { name: "Так, скасувати" }));
  expect(await screen.findByText("Заняття скасовано.")).toBeInTheDocument();
  expect(detailLoads).toBe(2);
  expect(programLoads).toBeGreaterThanOrEqual(2);
  expect(calls.some((call) => call.path.endsWith("/progress/"))).toBe(true);
  expect(await screen.findByRole("heading", { name: "Оновлений блок" })).toBeInTheDocument();
  expect(calls.some((call) => call.method === "POST" && call.path.endsWith("/cancel/"))).toBe(true);
  expect(screen.getByText("Скасовано")).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Скасувати заняття" })).not.toBeInTheDocument();
  expect(screen.queryByRole("link", { name: "Завершити тренування" })).not.toBeInTheDocument();
});

test("activation is disabled without slots and maps 400/409 responses", async () => {
  window.history.replaceState(null, "", "/programs/41");
  const noSlots = { ...baseProgram, progress: { ...baseProgram.progress, total_planned: 0 } };
  const first = mockApi({
    "GET /api/v1/user-programs/41/": () => json(noSlots),
    "GET /api/v1/exercises/?page=1&page_size=100": () => json(exercises),
  });
  const view = render(<App />);
  expect(await screen.findByRole("button", { name: "Активувати програму" })).toBeDisabled();
  expect(first.calls.some((call) => call.method === "POST")).toBe(false);
  view.unmount();

  let attempt = 0;
  mockApi({
    "GET /api/v1/user-programs/41/": () => json(baseProgram),
    "GET /api/v1/exercises/?page=1&page_size=100": () => json(exercises),
    "POST /api/v1/user-programs/41/activate/": () => {
      attempt += 1;
      return attempt === 1 ? apiError("validation_error", 400) : apiError("invalid_state", 409);
    },
  });
  render(<App />);
  fireEvent.click(await screen.findByRole("button", { name: "Активувати програму" }));
  expect(await screen.findByText(/Спочатку заплануйте/)).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Активувати програму" }));
  expect(await screen.findByText(/поточному стані/)).toBeInTheDocument();
});
