import { fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import App from "@/App";
import { apiError, json, mockApi } from "@/test/mockApi";

const page = (results: unknown[]) => ({ count: results.length, next: null, previous: null, results });
beforeEach(() => {
  document.cookie = "csrftoken=token; path=/";
  window.history.replaceState(null, "", "/");
});
afterEach(() => vi.unstubAllGlobals());

test("statistics sends Kyiv dates, reports missing kcal estimates, and has an honest empty weight state", async () => {
  window.history.replaceState(null, "", "/stats?period=custom&start_date=2026-10-19&end_date=2026-10-26");
  const { calls } = mockApi({
    "GET /api/v1/statistics/overview/?start_date=2026-10-19&end_date=2026-10-26": () =>
      json({
        period: { start_date: "2026-10-19", end_date: "2026-10-26", timezone: "Europe/Kyiv" },
        completed_workouts: 2,
        performed_exercises: 4,
        total_duration_min: "85.00",
        estimated_calories_total: "420.50",
        workouts_without_calorie_estimate: 1,
      }),
    "GET /api/v1/statistics/weight-chart/?start_date=2026-10-19&end_date=2026-10-26": () =>
      json({ period: { start_date: "2026-10-19", end_date: "2026-10-26", timezone: "Europe/Kyiv" }, points: [] }),
  });
  render(<App />);
  expect(await screen.findByText("1 занять без оцінки калорій")).toBeInTheDocument();
  expect(screen.getByText("Немає вимірів ваги за цей період")).toBeInTheDocument();
  expect(screen.getByText("Немає активності за цей період")).toBeInTheDocument();
  expect(calls.some((call) => call.path.includes("start_date=2026-10-19&end_date=2026-10-26"))).toBe(true);
});

test("statistics renders weekly activity bars with Kyiv labels and an accessible minutes table", async () => {
  window.history.replaceState(null, "", "/stats?period=custom&start_date=2026-10-26&end_date=2026-11-09");
  mockApi({
    "GET /api/v1/statistics/overview/?start_date=2026-10-26&end_date=2026-11-09": () =>
      json({
        period: { start_date: "2026-10-26", end_date: "2026-11-09", timezone: "Europe/Kyiv" },
        completed_workouts: 3,
        performed_exercises: 6,
        total_duration_min: "115.00",
        estimated_calories_total: "500.00",
        workouts_without_calorie_estimate: 0,
        weekly_activity: [
          { week_start: "2026-10-26", completed_workouts: 2, total_duration_min: "85.00" },
          { week_start: "2026-11-02", completed_workouts: 1, total_duration_min: "30.00" },
        ],
      }),
    "GET /api/v1/statistics/weight-chart/?start_date=2026-10-26&end_date=2026-11-09": () =>
      json({ period: { start_date: "2026-10-26", end_date: "2026-11-09", timezone: "Europe/Kyiv" }, points: [] }),
  });
  render(<App />);
  expect(await screen.findByText("Активність по тижнях")).toBeInTheDocument();
  expect(screen.getByTestId("weekly-activity-bars")).toBeInTheDocument();
  const table = screen.getByRole("table", { name: "Дані активності по тижнях" });
  expect(within(table).getByText("26.10–01.11")).toBeInTheDocument();
  expect(within(table).getByText("85 хв")).toBeInTheDocument();
  expect(within(table).getByText("2")).toBeInTheDocument();
});

test("statistics shows an activity empty state when every weekly bucket is zero", async () => {
  window.history.replaceState(null, "", "/stats?period=custom&start_date=2026-10-26&end_date=2026-11-09");
  mockApi({
    "GET /api/v1/statistics/overview/?start_date=2026-10-26&end_date=2026-11-09": () =>
      json({
        period: { start_date: "2026-10-26", end_date: "2026-11-09", timezone: "Europe/Kyiv" },
        completed_workouts: 0,
        performed_exercises: 0,
        total_duration_min: "0.00",
        estimated_calories_total: "0.00",
        workouts_without_calorie_estimate: 0,
        weekly_activity: [
          { week_start: "2026-10-26", completed_workouts: 0, total_duration_min: "0.00" },
          { week_start: "2026-11-02", completed_workouts: 0, total_duration_min: "0.00" },
        ],
      }),
    "GET /api/v1/statistics/weight-chart/?start_date=2026-10-26&end_date=2026-11-09": () =>
      json({ period: { start_date: "2026-10-26", end_date: "2026-11-09", timezone: "Europe/Kyiv" }, points: [] }),
  });
  render(<App />);
  expect(await screen.findByText("Немає активності за цей період")).toBeInTheDocument();
  expect(screen.queryByText("Активність по тижнях")).not.toBeInTheDocument();
});

test("history shows the required null-kcal text", async () => {
  window.history.replaceState(null, "", "/history?period=custom&start_date=2026-11-01&end_date=2026-12-01");
  mockApi({
    "GET /api/v1/completed-sessions/?start_date=2026-11-01&end_date=2026-12-01&page=1&page_size=20": () =>
      json(
        page([
          {
            id: 1,
            completed_at: "2026-11-02T10:00:00Z",
            source_workout_id: 2,
            source_workout_name_snapshot: "A",
            performed_workout_name_snapshot: "B",
            duration_min: "20.00",
            estimated_calories: null,
            workout_points: 14,
          },
        ]),
      ),
  });
  render(<App />);
  expect(await screen.findByText("Калорії не розраховано")).toBeInTheDocument();
  expect(screen.queryByText("null")).not.toBeInTheDocument();
});

test("leaderboard highlights self without rendering PII", async () => {
  window.history.replaceState(null, "", "/leaderboard?period=week");
  mockApi({
    "GET /api/v1/leaderboard/?period=week&page=1&page_size=20": () =>
      json({
        period: { kind: "week", start_at: null, end_at: null },
        count: 1,
        next: null,
        previous: null,
        results: [{ rank: 2, public_alias: "FitFox", points: 42, email: "secret@example.test", name: "Private Name" }],
        self: { opted_in: true, points: 42, rank: 2 },
      }),
  });
  render(<App />);
  expect(await screen.findByTestId("leaderboard-self")).toHaveTextContent("42");
  expect(screen.getByText("FitFox").closest("div")).toHaveClass("bg-selected-state");
  expect(screen.queryByText("secret@example.test")).not.toBeInTheDocument();
  expect(screen.queryByText("Private Name")).not.toBeInTheDocument();
});

test("leaderboard gives non-opted users a settings link", async () => {
  window.history.replaceState(null, "", "/leaderboard?period=all");
  mockApi({
    "GET /api/v1/leaderboard/?period=all&page=1&page_size=20": () =>
      json({
        period: { kind: "all", start_at: null, end_at: null },
        count: 0,
        next: null,
        previous: null,
        results: [],
        self: { opted_in: false, points: 9, rank: null },
      }),
  });
  render(<App />);
  expect(await screen.findByText(/не берете участі/)).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "Налаштувати участь" })).toHaveAttribute("href", "/settings");
});

test("challenge join confirms, posts H03, and reloads H02", async () => {
  window.history.replaceState(null, "", "/challenges/9");
  vi.spyOn(window, "confirm").mockReturnValue(true);
  let joined = false;
  const { calls } = mockApi({
    "GET /api/v1/challenges/9/": () =>
      json({
        id: 9,
        name: "Рух",
        start_at: "2026-10-01T00:00:00Z",
        end_at: "2026-12-01T00:00:00Z",
        goal_kind: "workouts",
        goal_value: 5,
        joined,
      }),
    "POST /api/v1/challenges/9/join/": () => {
      joined = true;
      return json(
        {
          id: 1,
          challenge_id: 9,
          joined_at: "2026-11-01T00:00:00Z",
          status: "joined",
          progress_value: 0,
          goal_value: 5,
        },
        201,
      );
    },
  });
  render(<App />);
  fireEvent.click(await screen.findByRole("button", { name: "Приєднатися" }));
  expect(await screen.findByText("Ви приєдналися до челенджу.")).toBeInTheDocument();
  expect(calls.some((call) => call.method === "POST")).toBe(true);
});

test("challenge join maps 409 to an expired message", async () => {
  window.history.replaceState(null, "", "/challenges/9");
  vi.spyOn(window, "confirm").mockReturnValue(true);
  mockApi({
    "GET /api/v1/challenges/9/": () =>
      json({
        id: 9,
        name: "Рух",
        start_at: "2026-10-01T00:00:00Z",
        end_at: "2026-11-01T00:00:00Z",
        goal_kind: "workouts",
        goal_value: 5,
        joined: false,
      }),
    "POST /api/v1/challenges/9/join/": () => apiError("invalid_state", 409),
  });
  render(<App />);
  fireEvent.click(await screen.findByRole("button", { name: "Приєднатися" }));
  expect(await screen.findByText("Термін вступу до челенджу вже минув.")).toBeInTheDocument();
});

test("achievements merge M03 definitions with M04 unlocks", async () => {
  window.history.replaceState(null, "", "/achievements");
  mockApi({
    "GET /api/v1/achievements/?page=1&page_size=100": () =>
      json(
        page([
          { id: 4, code: "first_workout", name: "Перше", description: "Завершіть тренування", earned: true },
          { id: 5, code: "five_workouts", name: "П’ять", description: "Завершіть п’ять", earned: false },
        ]),
      ),
    "GET /api/v1/user-achievements/?page=1&page_size=100": () =>
      json(
        page([
          {
            id: 71,
            achievement_id: 4,
            rule_code_snapshot: "first_workout",
            name_snapshot: "Перше",
            unlocked_at: "2026-10-01T17:00:00Z",
          },
        ]),
      ),
  });
  render(<App />);
  await screen.findByText("Перше");
  expect(screen.getByText("Перше").closest("div")?.parentElement).toHaveTextContent("Відкрито");
  expect(screen.getByText("П’ять").closest("div")?.parentElement).toHaveTextContent("Заблоковано");
  expect(screen.queryByRole("progressbar")).not.toBeInTheDocument();
});

test("mobile navigation has five items and grouped nested routes stay active", async () => {
  window.history.replaceState(null, "", "/history/600");
  mockApi({
    "GET /api/v1/completed-sessions/600/": () =>
      json({
        id: 600,
        scheduled_session_id: null,
        source_workout_id: 8,
        source_workout_id_snapshot: 8,
        source_workout_name_snapshot: "A",
        performed_workout_name_snapshot: "B",
        performed_workout_category_snapshot: "strength",
        program_context: null,
        completed_at: "2026-11-01T00:00:00Z",
        duration_min: "20.00",
        weight_kg_snapshot: "70.0",
        estimated_calories: "100.00",
        missing_calorie_reason: null,
        workout_points: 12,
        results: [],
      }),
  });
  render(<App />);
  await screen.findByText("B");
  const nav = screen.getByRole("navigation", { name: "Мобільна навігація" });
  expect(within(nav).getAllByRole("link")).toHaveLength(5);
  expect(within(nav).getByRole("link", { name: "Прогрес" })).toHaveClass("bg-selected-state");
});
