import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, test, vi } from "vitest";

import App from "@/App";
import { apiError, json, mockApi } from "@/test/mockApi";

const profile = {
  first_name: "Олена",
  last_name: "",
  date_of_birth: "1995-04-12",
  age: 31,
  weight_kg: "68.0",
  height_cm: "170.0",
  gender: "female",
  fitness_goal: "maintenance",
  experience_level: "beginner",
  workouts_per_week: 3,
};
const emptyHistory = { count: 0, next: null, previous: null, results: [] };

beforeEach(() => {
  window.history.replaceState(null, "", "/profile");
  document.cookie = "csrftoken=; Max-Age=0; path=/";
});
afterEach(() => vi.unstubAllGlobals());

test("missing profile shows the create form and posts all fitness fields", async () => {
  const { calls } = mockApi({
    "GET /api/v1/profile/": () => apiError("profile_missing", 404),
    "POST /api/v1/profile/": () => json(profile, 201),
    "GET /api/v1/weight-entries/?page=1&page_size=20": () => json({ count: 1, next: null, previous: null, results: [{ id: 1, measured_at: "2026-11-14T10:00:00Z", weight_kg: "68.0" }] }),
  });
  render(<App />);
  await screen.findByRole("heading", { name: "Створіть профіль" });

  fireEvent.click(screen.getByRole("button", { name: "Створити профіль" }));
  expect(screen.getByText("Вкажіть дату народження.")).toBeInTheDocument();
  expect(calls.some((call) => call.method === "POST")).toBe(false);

  fireEvent.change(screen.getByLabelText("Ім’я (необов’язково)"), { target: { value: "Олена" } });
  fireEvent.change(screen.getByLabelText("Дата народження"), { target: { value: "1995-04-12" } });
  fireEvent.change(screen.getByLabelText("Стать"), { target: { value: "female" } });
  fireEvent.change(screen.getByLabelText("Вага, кг"), { target: { value: "68" } });
  fireEvent.change(screen.getByLabelText("Зріст, см"), { target: { value: "170" } });
  fireEvent.change(screen.getByLabelText("Ціль"), { target: { value: "maintenance" } });
  fireEvent.change(screen.getByLabelText("Рівень підготовки"), { target: { value: "beginner" } });
  fireEvent.click(screen.getByRole("button", { name: "Створити профіль" }));

  await screen.findByText("Профіль створено.");
  expect(calls.find((call) => call.method === "POST")?.body).toEqual({
    first_name: "Олена",
    last_name: "",
    date_of_birth: "1995-04-12",
    weight_kg: "68",
    height_cm: "170",
    gender: "female",
    fitness_goal: "maintenance",
    experience_level: "beginner",
    workouts_per_week: 3,
  });
  expect(screen.getByRole("heading", { name: "Мій профіль" })).toBeInTheDocument();
  expect(await screen.findByText("68 кг", { selector: "td" })).toBeInTheDocument();
});

test("editing sends only changed fields and shows server field errors", async () => {
  let attempt = 0;
  const { calls } = mockApi({
    "GET /api/v1/profile/": () => json(profile),
    "GET /api/v1/weight-entries/?page=1&page_size=20": () => json(emptyHistory),
    "PATCH /api/v1/profile/": () => {
      attempt += 1;
      return attempt === 1
        ? apiError("validation_error", 400, { height_cm: ["Зріст має бути від 100 до 250 см."] }, "Перевірте дані.")
        : json({ ...profile, height_cm: "172.0" });
    },
  });
  render(<App />);
  fireEvent.click(await screen.findByRole("button", { name: "Редагувати" }));
  fireEvent.change(screen.getByLabelText("Вага, кг"), { target: { value: "68.00" } });
  fireEvent.change(screen.getByLabelText("Зріст, см"), { target: { value: "172" } });
  fireEvent.click(screen.getByRole("button", { name: "Зберегти зміни" }));

  expect(await screen.findByText("Зріст має бути від 100 до 250 см.")).toBeInTheDocument();
  // 68.00 equals the stored 68.0, so weight is not sent and no WeightEntry is created.
  expect(calls.find((call) => call.method === "PATCH")?.body).toEqual({ height_cm: "172" });

  fireEvent.click(screen.getByRole("button", { name: "Зберегти зміни" }));
  await screen.findByText("Зміни збережено.");
  await waitFor(() => expect(screen.getByText("172 см")).toBeInTheDocument());
});
