import { fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, expect, test, vi } from "vitest";

import App from "@/App";
import { apiError, json, mockApi } from "@/test/mockApi";

const workout = {
  id: 8,
  name: "Силове А",
  description: "",
  category: "strength",
  exercises: [
    { entry_id: 1, position: 1, exercise: { id: 17, name: "Присідання", category: "strength", tracks_distance: false }, recommended_sets: 3, recommended_reps: 10, recommended_load_kg: "20.0", recommended_duration_min: null, recommended_distance_km: null },
    { entry_id: 2, position: 2, exercise: { id: 18, name: "Віджимання", category: "strength", tracks_distance: false }, recommended_sets: 2, recommended_reps: 8, recommended_load_kg: null, recommended_duration_min: null, recommended_distance_km: null },
  ],
};

const completion = {
  id: 600,
  scheduled_session_id: null,
  source_workout_id: 8,
  completed_at: "2026-11-15T10:00:00Z",
  duration_min: "45.00",
  estimated_calories: null,
  missing_calorie_reason: "missing_met",
  workout_points: 18,
  program: null,
};

beforeEach(() => {
  document.cookie = "csrftoken=token; path=/";
  sessionStorage.clear();
});
afterEach(() => vi.unstubAllGlobals());

function fillStandaloneForm() {
  fireEvent.change(screen.getByLabelText("Загальна тривалість, хв"), { target: { value: "45" } });
  const second = screen.getByRole("group", { name: /2\. Віджимання/ });
  fireEvent.click(within(second).getByRole("checkbox", { name: "Виконано" }));
}

test("E01 sends one source, checked exercises, fixed decimal strings and an idempotency header", async () => {
  window.history.replaceState(null, "", "/catalog/workouts/8/complete");
  const { calls } = mockApi({
    "GET /api/v1/workouts/8/": () => json(workout),
    "POST /api/v1/completed-sessions/": () => json(completion, 201),
  });
  render(<App />);
  await screen.findByRole("heading", { name: "Завершити тренування" });
  fillStandaloneForm();
  fireEvent.click(screen.getByRole("button", { name: "Зберегти результат" }));
  expect(await screen.findByText("Калорії для цього тренування не розраховуються")).toBeInTheDocument();
  const call = calls.find((item) => item.method === "POST")!;
  expect(call.headers.get("Idempotency-Key")).toMatch(/^[0-9a-f-]{36}$/);
  expect(call.body).toEqual({
    scheduled_session_id: null,
    source_workout_id: 8,
    duration_min: "45.00",
    results: [{ position: 1, exercise_id: 17, actual_sets: 3, actual_reps: 10, actual_load_kg: "20.0", actual_duration_min: null, actual_distance_km: null }],
  });
});

test("planned completion uses the current personal composition and refreshes S03, G04 and G08", async () => {
  window.history.replaceState(null, "", "/schedule/92/complete");
  const session = { id: 92, scheduled_at: "2026-11-15T09:00:00Z", status: "planned", is_missed: false, user_program_id: 41, user_program_workout_id: 501, source_workout_id: 8, reschedule_history: [], completed_session_id: null, reminder: { id: 4, visible_at: "2026-11-15T08:00:00Z", status: "pending", is_current: true } };
  const program = { id: 41, name: "Моя програма", description: "", fitness_goal: "maintenance", status: "active", is_archived: false, source_program_template_id: 2, source_program_template_name_snapshot: "Шаблон", bonus_target_sessions: 3, progress: { total_planned: 1, completed_planned: 0, percent: "0.0" }, completion_snapshot: null, bonus_earned: false, workouts: [{ entry_id: 501, position: 1, source_workout_id: 8, name: "Особистий блок", category: "strength", exercises: [{ position: 1, exercise_id: 17, recommended_sets: 4, recommended_reps: 6, recommended_load_kg: "25.0", recommended_duration_min: null, recommended_distance_km: null }] }] };
  const exercisePage = { count: 1, next: null, previous: null, results: [{ id: 17, name: "Присідання", description: "", category: "strength", tracks_distance: false, met_value: null, met_activity_code: null, met_reference_version: null, met_activity_description: null }] };
  let sessionLoads = 0;
  let programLoads = 0;
  const { calls } = mockApi({
    "GET /api/v1/scheduled-sessions/92/": () => { sessionLoads += 1; return json(session); },
    "GET /api/v1/user-programs/41/": () => { programLoads += 1; return json({ ...program, name: programLoads === 1 ? "Моя програма" : "Оновлена програма" }); },
    "GET /api/v1/user-programs/41/progress/": () => json({ user_program_id: 41, status: "completed", is_archived: false, total_planned: 1, completed_planned: 1, percent: "100.0", bonus_target_sessions: 3, bonus_earned: false, completion_snapshot: null }),
    "GET /api/v1/exercises/?page=1&page_size=100": () => json(exercisePage),
    "POST /api/v1/completed-sessions/": () => json({ ...completion, scheduled_session_id: 92, program: { id: 41, status: "completed", progress_percent: "100.0", bonus_earned: false } }, 201),
  });
  render(<App />);
  await screen.findByRole("heading", { name: "Завершити тренування" });
  fireEvent.change(screen.getByLabelText("Загальна тривалість, хв"), { target: { value: "30" } });
  fireEvent.click(screen.getByRole("button", { name: "Зберегти результат" }));
  expect(await screen.findByText("Програму завершено")).toBeInTheDocument();
  expect(calls.find((item) => item.method === "POST")?.body).toMatchObject({ scheduled_session_id: 92, source_workout_id: null, results: [{ actual_sets: 4, actual_reps: 6, actual_load_kg: "25.0" }] });
  expect(sessionLoads).toBe(2);
  expect(programLoads).toBe(2);
  expect(calls.some((item) => item.path.endsWith("/progress/"))).toBe(true);
  fireEvent.click(screen.getByRole("link", { name: "До програми" }));
  expect(await screen.findByRole("heading", { name: "Оновлена програма" })).toBeInTheDocument();
  expect(programLoads).toBe(3);
});

test("a network retry of the identical body reuses the same key", async () => {
  window.history.replaceState(null, "", "/catalog/workouts/8/complete");
  let attempt = 0;
  const first = mockApi({
    "GET /api/v1/workouts/8/": () => json(workout),
    "POST /api/v1/completed-sessions/": () => {
      attempt += 1;
      if (attempt === 1) throw new TypeError("network");
      return json(completion, 201);
    },
  });
  render(<App />);
  await screen.findByRole("heading", { name: "Завершити тренування" });
  fillStandaloneForm();
  fireEvent.click(screen.getByRole("button", { name: "Зберегти результат" }));
  expect(await screen.findByText("Немає зв’язку із сервером.")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Зберегти результат" }));
  await screen.findByText("Калорії для цього тренування не розраховуються");
  const networkKeys = first.calls.filter((item) => item.method === "POST").map((item) => item.headers.get("Idempotency-Key"));
  expect(networkKeys[0]).toBe(networkKeys[1]);
});

test("idempotency conflict blocks the form, clears storage, and a new visit gets a new key", async () => {
  window.history.replaceState(null, "", "/catalog/workouts/8/complete");
  const first = mockApi({
    "GET /api/v1/workouts/8/": () => json(workout),
    "POST /api/v1/completed-sessions/": () => apiError("idempotency_conflict", 409),
  });
  const view = render(<App />);
  await screen.findByRole("heading", { name: "Завершити тренування" });
  fillStandaloneForm();
  fireEvent.click(screen.getByRole("button", { name: "Зберегти результат" }));
  expect(await screen.findByText(/Це тренування вже збережено раніше/)).toBeInTheDocument();
  const submit = screen.getByRole("button", { name: "Зберегти результат" });
  expect(submit).toBeDisabled();
  expect(sessionStorage.getItem("completion-attempt:workout:8")).toBeNull();
  expect(screen.getByRole("link", { name: "тренування" })).toHaveAttribute("href", "/catalog/workouts/8");
  expect(screen.getByRole("link", { name: "розкладу" })).toHaveAttribute("href", "/schedule");
  fireEvent.change(screen.getByLabelText("Загальна тривалість, хв"), { target: { value: "46" } });
  fireEvent.click(submit);
  expect(first.calls.filter((item) => item.method === "POST")).toHaveLength(1);
  const firstKey = first.calls.find((item) => item.method === "POST")!.headers.get("Idempotency-Key");
  view.unmount();

  const second = mockApi({
    "GET /api/v1/workouts/8/": () => json(workout),
    "POST /api/v1/completed-sessions/": () => json({ ...completion, duration_min: "46.00" }, 201),
  });
  render(<App />);
  await screen.findByRole("heading", { name: "Завершити тренування" });
  fillStandaloneForm();
  fireEvent.change(screen.getByLabelText("Загальна тривалість, хв"), { target: { value: "46" } });
  fireEvent.click(screen.getByRole("button", { name: "Зберегти результат" }));
  await screen.findByText("Калорії для цього тренування не розраховуються");
  const newKey = second.calls.find((item) => item.method === "POST")!.headers.get("Idempotency-Key");
  expect(newKey).not.toBe(firstKey);
});

test("duplicate completion blocks a slot attempt, clears its key, and links to fresh S03", async () => {
  window.history.replaceState(null, "", "/schedule/92/complete");
  const session = { id: 92, scheduled_at: "2026-11-15T09:00:00Z", status: "planned", is_missed: false, user_program_id: null, user_program_workout_id: null, source_workout_id: 8, reschedule_history: [], completed_session_id: null, reminder: { id: 4, visible_at: "2026-11-15T08:00:00Z", status: "pending", is_current: true } };
  const { calls } = mockApi({
    "GET /api/v1/scheduled-sessions/92/": () => json(session),
    "GET /api/v1/workouts/8/": () => json(workout),
    "POST /api/v1/completed-sessions/": () => apiError("duplicate_completion", 409),
  });
  render(<App />);
  await screen.findByRole("heading", { name: "Завершити тренування" });
  fillStandaloneForm();
  fireEvent.click(screen.getByRole("button", { name: "Зберегти результат" }));
  expect(await screen.findByText(/Це тренування вже збережено раніше/)).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Зберегти результат" })).toBeDisabled();
  expect(screen.getByRole("link", { name: "Переглянути заняття" })).toHaveAttribute("href", "/schedule/92");
  expect(sessionStorage.getItem("completion-attempt:session:92")).toBeNull();
  expect(calls.filter((item) => item.method === "POST")).toHaveLength(1);
});

test("E01 maps results[index] errors to the performed exercise field", async () => {
  window.history.replaceState(null, "", "/catalog/workouts/8/complete");
  mockApi({
    "GET /api/v1/workouts/8/": () => json(workout),
    "POST /api/v1/completed-sessions/": () => apiError("validation_error", 400, { "results[0].actual_reps": ["Повторення не відповідають вправі."] }),
  });
  render(<App />);
  await screen.findByRole("heading", { name: "Завершити тренування" });
  fillStandaloneForm();
  fireEvent.click(screen.getByRole("button", { name: "Зберегти результат" }));
  expect(await screen.findByText("Повторення не відповідають вправі.")).toBeInTheDocument();
  expect(screen.getByLabelText("Повторення")).toHaveAttribute("aria-invalid", "true");
});

test("profile_missing shows the required copy and profile link", async () => {
  window.history.replaceState(null, "", "/catalog/workouts/8/complete");
  mockApi({
    "GET /api/v1/workouts/8/": () => json(workout),
    "POST /api/v1/completed-sessions/": () => apiError("profile_missing", 404),
  });
  render(<App />);
  await screen.findByRole("heading", { name: "Завершити тренування" });
  fillStandaloneForm();
  fireEvent.click(screen.getByRole("button", { name: "Зберегти результат" }));
  expect(await screen.findByText(/Вкажіть вагу в профілі/)).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "Перейти до профілю" })).toHaveAttribute("href", "/profile");
});

test("result hides reason codes and shows the program bonus only when returned", async () => {
  const withProgram = { ...completion, program: { id: 41, status: "completed", progress_percent: "100.0", bonus_earned: true } };
  window.history.replaceState({ usr: { completion: withProgram } }, "", "/completed/600");
  mockApi({});
  const view = render(<App />);
  expect(await screen.findByText("Калорії для цього тренування не розраховуються")).toBeInTheDocument();
  expect(screen.queryByText("missing_met")).not.toBeInTheDocument();
  expect(screen.getByText("+50 бонусних балів")).toBeInTheDocument();
  view.unmount();

  window.history.replaceState({ usr: { completion } }, "", "/completed/600");
  render(<App />);
  await screen.findByText("Калорії для цього тренування не розраховуються");
  expect(screen.queryByText("+50 бонусних балів")).not.toBeInTheDocument();
});

test("result deep link without router state explains the phase boundary", async () => {
  window.history.replaceState(null, "", "/completed/600");
  mockApi({});
  render(<App />);
  expect(await screen.findByText(/Результат недоступний після оновлення/)).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "До розкладу" })).toHaveAttribute("href", "/schedule");
});
