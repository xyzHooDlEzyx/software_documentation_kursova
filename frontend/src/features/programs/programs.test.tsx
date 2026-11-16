import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, expect, test, vi } from "vitest";

import App from "@/App";
import { apiError, json, mockApi } from "@/test/mockApi";

const recommendation = {
  program_template: {
    id: 12,
    name: "Баланс 3",
    description: "Рівномірний склад",
    fitness_goal: "maintenance",
    experience_level: "beginner",
    workouts_per_week: 3,
    workouts: [{ position: 1, workout_id: 8, name: "Силове А" }],
  },
  reason: {
    exact_goal: true,
    exact_level: true,
    frequency_difference: 0,
    strategy: "MaintenanceSelectionStrategy",
    composition_criterion: "Найменший розмах часток",
  },
};

const program = {
  id: 41,
  name: "Баланс 3",
  description: "",
  fitness_goal: "maintenance",
  status: "draft",
  is_archived: false,
  source_program_template_id: 12,
  source_program_template_name_snapshot: "Баланс 3",
  bonus_target_sessions: null,
  progress: { total_planned: 0, completed_planned: 0, percent: "0.0" },
  completion_snapshot: null,
  bonus_earned: false,
  workouts: [
    {
      entry_id: 501,
      position: 1,
      source_workout_id: 8,
      name: "Силове А",
      category: "strength",
      exercises: [
        {
          position: 1,
          exercise_id: 17,
          recommended_sets: 3,
          recommended_reps: 10,
          recommended_load_kg: "20.0",
          recommended_duration_min: null,
          recommended_distance_km: null,
        },
        {
          position: 2,
          exercise_id: 18,
          recommended_sets: 3,
          recommended_reps: 12,
          recommended_load_kg: null,
          recommended_duration_min: null,
          recommended_distance_km: null,
        },
      ],
    },
  ],
};

const strengthExercises = {
  count: 2,
  next: null,
  previous: null,
  results: [
    {
      id: 17,
      name: "Присідання",
      description: "",
      category: "strength",
      met_value: null,
      met_activity_code: null,
      met_reference_version: null,
      met_activity_description: null,
      tracks_distance: false,
    },
    {
      id: 18,
      name: "Віджимання",
      description: "",
      category: "strength",
      met_value: null,
      met_activity_code: null,
      met_reference_version: null,
      met_activity_description: null,
      tracks_distance: false,
    },
  ],
};

const cardioProgram = {
  ...program,
  name: "Кардіо план",
  workouts: [
    {
      entry_id: 601,
      position: 1,
      source_workout_id: 9,
      name: "Кардіо блок",
      category: "cardio",
      exercises: [
        {
          position: 1,
          exercise_id: 21,
          recommended_sets: null,
          recommended_reps: null,
          recommended_load_kg: null,
          recommended_duration_min: null,
          recommended_distance_km: "4.500",
        },
        {
          position: 2,
          exercise_id: 22,
          recommended_sets: null,
          recommended_reps: null,
          recommended_load_kg: null,
          recommended_duration_min: "12.00",
          recommended_distance_km: null,
        },
      ],
    },
  ],
};

const cardioExercises = {
  count: 2,
  next: null,
  previous: null,
  results: [
    {
      id: 21,
      name: "Біг на біговій доріжці",
      description: "",
      category: "cardio",
      met_value: null,
      met_activity_code: null,
      met_reference_version: null,
      met_activity_description: null,
      tracks_distance: true,
    },
    {
      id: 22,
      name: "Стрибки на скакалці",
      description: "",
      category: "cardio",
      met_value: null,
      met_activity_code: null,
      met_reference_version: null,
      met_activity_description: null,
      tracks_distance: false,
    },
  ],
};

beforeEach(() => {
  document.cookie = "csrftoken=; Max-Age=0; path=/";
});
afterEach(() => vi.unstubAllGlobals());

test("accepting a recommendation copies the template and opens the new program", async () => {
  window.history.replaceState(null, "", "/programs/recommendation");
  const { calls } = mockApi({
    "GET /api/v1/program-recommendation/": () => json(recommendation),
    "POST /api/v1/user-programs/": () => json(program, 201),
    "GET /api/v1/user-programs/41/": () => json(program),
    "GET /api/v1/exercises/?page=1&page_size=100": () => json(strengthExercises),
  });
  render(<App />);
  expect(await screen.findByText("Підтримка: збалансований склад")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Прийняти й створити мою програму" }));

  await screen.findByText("Програму створено. Це ваша особиста копія — її можна змінювати.");
  expect(calls.find((call) => call.method === "POST")?.body).toEqual({ program_template_id: 12 });
  expect(await screen.findByText("1. Присідання")).toBeInTheDocument();
});

test("a stale recommendation (409) reloads the proposal instead of failing silently", async () => {
  window.history.replaceState(null, "", "/programs/recommendation");
  let loads = 0;
  mockApi({
    "GET /api/v1/program-recommendation/": () => {
      loads += 1;
      return json(recommendation);
    },
    "POST /api/v1/user-programs/": () => apiError("recommendation_mismatch", 409),
  });
  render(<App />);
  fireEvent.click(await screen.findByRole("button", { name: "Прийняти й створити мою програму" }));
  expect(await screen.findByText(/Рекомендація змінилась/)).toBeInTheDocument();
  expect(loads).toBe(2);
});

test("missing profile on recommendation links to the profile form", async () => {
  window.history.replaceState(null, "", "/programs/recommendation");
  mockApi({ "GET /api/v1/program-recommendation/": () => apiError("profile_missing", 404) });
  render(<App />);
  expect(await screen.findByRole("link", { name: "Заповнити профіль" })).toHaveAttribute("href", "/profile");
});

test("composition editor reorders, removes and sends only strength parameters", async () => {
  window.history.replaceState(null, "", "/programs/41/workouts/501");
  const { calls } = mockApi({
    "GET /api/v1/user-programs/41/": () => json(program),
    "GET /api/v1/exercises/?category=strength&page=1&page_size=100": () => json(strengthExercises),
    "GET /api/v1/exercises/?page=1&page_size=100": () => json(strengthExercises),
    "PUT /api/v1/user-programs/41/workouts/501/": () => json(program.workouts[0]),
  });
  render(<App />);
  fireEvent.click(await screen.findByRole("button", { name: "Опустити вправу 1" }));
  expect(screen.queryByLabelText(/Тривалість/)).not.toBeInTheDocument();
  fireEvent.change(screen.getAllByLabelText("Підходи")[0], { target: { value: "4" } });
  fireEvent.click(screen.getByRole("button", { name: "Зберегти склад" }));

  await screen.findByText("Склад тренування «Силове А» збережено.");
  expect(calls.find((call) => call.method === "PUT")?.body).toEqual({
    name: "Силове А",
    exercises: [
      {
        position: 1,
        exercise_id: 18,
        recommended_sets: 4,
        recommended_reps: 12,
        recommended_load_kg: null,
        recommended_duration_min: null,
        recommended_distance_km: null,
      },
      {
        position: 2,
        exercise_id: 17,
        recommended_sets: 3,
        recommended_reps: 10,
        recommended_load_kg: "20",
        recommended_duration_min: null,
        recommended_distance_km: null,
      },
    ],
  });
});

test("cardio composition allows distance only for exercises that track it", async () => {
  window.history.replaceState(null, "", "/programs/41/workouts/601");
  const { calls } = mockApi({
    "GET /api/v1/user-programs/41/": () => json(cardioProgram),
    "GET /api/v1/exercises/?category=cardio&page=1&page_size=100": () => json(cardioExercises),
    "GET /api/v1/exercises/?page=1&page_size=100": () => json(cardioExercises),
    "PUT /api/v1/user-programs/41/workouts/601/": () => json(cardioProgram.workouts[0]),
  });

  const firstRender = render(<App />);
  const rows = await screen.findAllByRole("listitem");
  expect(within(rows[0]).getByLabelText("Дистанція, км")).toHaveValue(4.5);
  expect(within(rows[1]).queryByLabelText("Дистанція, км")).not.toBeInTheDocument();
  expect(within(rows[1]).getByLabelText("Тривалість, хв (обов’язково)")).toHaveValue(12);
  expect(within(rows[1]).queryByText("Потрібна тривалість або дистанція.")).not.toBeInTheDocument();

  fireEvent.click(screen.getByRole("button", { name: "Зберегти склад" }));
  await screen.findByText("Склад тренування «Кардіо блок» збережено.");
  expect(calls.filter((call) => call.method === "PUT")[0]?.body).toEqual({
    name: "Кардіо блок",
    exercises: [
      {
        position: 1,
        exercise_id: 21,
        recommended_sets: null,
        recommended_reps: null,
        recommended_load_kg: null,
        recommended_duration_min: null,
        recommended_distance_km: "4.5",
      },
      {
        position: 2,
        exercise_id: 22,
        recommended_sets: null,
        recommended_reps: null,
        recommended_load_kg: null,
        recommended_duration_min: "12",
        recommended_distance_km: null,
      },
    ],
  });
  firstRender.unmount();

  window.history.replaceState(null, "", "/programs/41/workouts/601");
  render(<App />);
  const exerciseSelects = await screen.findAllByLabelText("Вправа");
  fireEvent.change(exerciseSelects[0], { target: { value: "22" } });
  expect(screen.queryByLabelText("Дистанція, км")).not.toBeInTheDocument();
  const requiredDurations = screen.getAllByLabelText("Тривалість, хв (обов’язково)");
  fireEvent.change(requiredDurations[0], { target: { value: "15" } });
  fireEvent.click(screen.getByRole("button", { name: "Зберегти склад" }));
  await screen.findByText("Склад тренування «Кардіо блок» збережено.");
  expect(calls.filter((call) => call.method === "PUT")[1]?.body).toEqual({
    name: "Кардіо блок",
    exercises: [
      {
        position: 1,
        exercise_id: 22,
        recommended_sets: null,
        recommended_reps: null,
        recommended_load_kg: null,
        recommended_duration_min: "15",
        recommended_distance_km: null,
      },
      {
        position: 2,
        exercise_id: 22,
        recommended_sets: null,
        recommended_reps: null,
        recommended_load_kg: null,
        recommended_duration_min: "12",
        recommended_distance_km: null,
      },
    ],
  });
});

test("composition editor maps per-exercise server errors to readable lines", async () => {
  window.history.replaceState(null, "", "/programs/41/workouts/501");
  mockApi({
    "GET /api/v1/user-programs/41/": () => json(program),
    "GET /api/v1/exercises/?category=strength&page=1&page_size=100": () => json(strengthExercises),
    "PUT /api/v1/user-programs/41/workouts/501/": () =>
      apiError(
        "validation_error",
        400,
        { "exercises[1].recommended_reps": ["Для силових вправ обов'язкова кількість повторень (> 0)."] },
        "Перевірте склад.",
      ),
  });
  render(<App />);
  fireEvent.click(await screen.findByRole("button", { name: "Зберегти склад" }));
  const alert = await screen.findByRole("alert");
  expect(
    within(alert).getByText("Вправа 2: Для силових вправ обов'язкова кількість повторень (> 0)."),
  ).toBeInTheDocument();
});

test("a 401 from a protected page returns the user to login", async () => {
  window.history.replaceState(null, "", "/programs");
  mockApi({ "GET /api/v1/user-programs/?archived=false&page=1": () => apiError("authentication_required", 401) });
  render(<App />);
  expect(await screen.findByRole("button", { name: "Увійти" })).toBeInTheDocument();
});

test("G09 planned_sessions_exist explains that slots must be cancelled and links to schedule", async () => {
  window.history.replaceState(null, "", "/programs/41");
  mockApi({
    "GET /api/v1/user-programs/41/": () => json(program),
    "GET /api/v1/exercises/?page=1&page_size=100": () => json(strengthExercises),
    "POST /api/v1/user-programs/41/archive/": () => apiError("planned_sessions_exist", 409),
  });
  render(<App />);
  fireEvent.click(await screen.findByRole("button", { name: "Архівувати програму" }));
  expect(screen.getByRole("button", { name: "Так, архівувати" })).toHaveFocus();
  fireEvent.click(screen.getByRole("button", { name: "Так, архівувати" }));
  expect(await screen.findByText(/Спочатку скасуйте заплановані заняття/)).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "Перейти до розкладу" })).toHaveAttribute(
    "href",
    "/schedule?user_program_id=41",
  );
});

test("an archived program is read-only and hides edit, schedule, activation and archive actions", async () => {
  window.history.replaceState(null, "", "/programs/41");
  mockApi({
    "GET /api/v1/user-programs/41/": () => json({ ...program, is_archived: true }),
    "GET /api/v1/exercises/?page=1&page_size=100": () => json(strengthExercises),
  });
  render(<App />);
  expect(await screen.findByText(/Програма в архіві/)).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Перейменувати" })).not.toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Запланувати" })).not.toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Активувати програму" })).not.toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Архівувати програму" })).not.toBeInTheDocument();
  expect(screen.queryByRole("link", { name: "Змінити склад" })).not.toBeInTheDocument();
});

test("the archive filter requests the real archived field", async () => {
  window.history.replaceState(null, "", "/programs");
  const empty = { count: 0, next: null, previous: null, results: [] };
  const { calls } = mockApi({
    "GET /api/v1/user-programs/?archived=false&page=1": () => json(empty),
    "GET /api/v1/user-programs/?archived=true&page=1": () => json(empty),
  });
  render(<App />);
  const archive = await screen.findByRole("button", { name: "Архів" });
  fireEvent.click(archive);
  await waitFor(() =>
    expect(calls.some((call) => call.path === "/api/v1/user-programs/?archived=true&page=1")).toBe(true),
  );
  expect(archive).toHaveAttribute("aria-pressed", "true");
});
