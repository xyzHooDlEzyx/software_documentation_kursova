import { request, withQuery, type Paginated } from "@/app/api";

/** P01–P03 response: decimals are strings, `age` is computed by the server. */
export type Profile = {
  first_name: string;
  last_name: string;
  date_of_birth: string;
  age: number;
  weight_kg: string;
  height_cm: string;
  gender: string;
  fitness_goal: string;
  experience_level: string;
  workouts_per_week: number;
};

export type ProfileInput = Omit<Profile, "age">;

export type WeightEntry = {
  id: number;
  measured_at: string;
  weight_kg: string;
};

export function getProfile() {
  return request<Profile>("/api/v1/profile/", "GET");
}

export function createProfile(input: ProfileInput) {
  return request<Profile>("/api/v1/profile/", "POST", input);
}

/** P03 accepts any subset; a changed weight also records a WeightEntry. */
export function updateProfile(changes: Partial<ProfileInput>) {
  return request<Profile>("/api/v1/profile/", "PATCH", changes);
}

export function listWeightEntries(page = 1, pageSize = 20) {
  return request<Paginated<WeightEntry>>(withQuery("/api/v1/weight-entries/", { page, page_size: pageSize }), "GET");
}
