import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, expect, test, vi } from "vitest";

import App from "@/App";
import { json, mockApi } from "@/test/mockApi";

const categories = { results: [{ code: "cardio", label: "Кардіо" }, { code: "strength", label: "Силові" }, { code: "yoga", label: "Йога" }] };
const page = <T,>(results: T[]) => ({ count: results.length, next: null, previous: null, results });

beforeEach(() => {
  window.history.replaceState(null, "", "/catalog");
  document.cookie = "csrftoken=; Max-Age=0; path=/";
});
afterEach(() => vi.unstubAllGlobals());

test("category filter queries the API and a workout opens its ordered exercises", async () => {
  const { calls } = mockApi({
    "GET /api/v1/categories/": () => json(categories),
    "GET /api/v1/workouts/?page=1&page_size=12": () => json(page([
      { id: 8, name: "Силове А", description: "Все тіло", category: "strength", exercise_count: 2 },
      { id: 9, name: "Ранкова йога", description: "", category: "yoga", exercise_count: 1 },
    ])),
    "GET /api/v1/workouts/?category=strength&page=1&page_size=12": () => json(page([
      { id: 8, name: "Силове А", description: "Все тіло", category: "strength", exercise_count: 2 },
    ])),
    "GET /api/v1/workouts/8/": () => json({
      id: 8, name: "Силове А", description: "Все тіло", category: "strength",
      exercises: [
        { entry_id: 51, position: 1, exercise: { id: 17, name: "Присідання", category: "strength", tracks_distance: false }, recommended_sets: 3, recommended_reps: 10, recommended_load_kg: "20.0", recommended_duration_min: null, recommended_distance_km: null },
        { entry_id: 52, position: 2, exercise: { id: 18, name: "Віджимання", category: "strength", tracks_distance: false }, recommended_sets: 3, recommended_reps: 12, recommended_load_kg: null, recommended_duration_min: null, recommended_distance_km: null },
      ],
    }),
  });
  render(<App />);
  await screen.findByText("Ранкова йога");

  fireEvent.click(await screen.findByRole("button", { name: "Силові" }));
  await screen.findByRole("button", { name: "Силові", pressed: true });
  expect(await screen.findByText("Силове А")).toBeInTheDocument();
  expect(screen.queryByText("Ранкова йога")).not.toBeInTheDocument();
  expect(calls.some((call) => call.path === "/api/v1/workouts/?category=strength&page=1&page_size=12")).toBe(true);

  fireEvent.click(screen.getByRole("link", { name: /Силове А/ }));
  await screen.findByRole("heading", { name: "Силове А" });
  expect(screen.getByText("3 × 10 · 20 кг")).toBeInTheDocument();
  expect(screen.getByText("3 × 12")).toBeInTheDocument();
});
