import { request, withQuery, type Paginated } from "@/app/api";

export type Category = { code: string; label: string };

export type Exercise = {
  id: number;
  name: string;
  description: string;
  category: string;
  met_value: string | null;
  met_activity_code: string | null;
  met_reference_version: string | null;
  met_activity_description: string | null;
  tracks_distance: boolean;
};

export type WorkoutSummary = {
  id: number;
  name: string;
  description: string;
  category: string;
  exercise_count: number;
};

/** Recommended parameters shared by catalog and personal compositions. */
export type RecommendedParameters = {
  recommended_sets: number | null;
  recommended_reps: number | null;
  recommended_load_kg: string | null;
  recommended_duration_min: string | null;
  recommended_distance_km: string | null;
};

export type WorkoutExerciseItem = RecommendedParameters & {
  entry_id: number;
  position: number;
  exercise: { id: number; name: string; category: string; tracks_distance: boolean };
};

export type WorkoutDetail = {
  id: number;
  name: string;
  description: string;
  category: string;
  exercises: WorkoutExerciseItem[];
};

export type CatalogQuery = { category?: string; search?: string; page?: number; pageSize?: number };

function catalogQuery({ category, search, page = 1, pageSize = 20 }: CatalogQuery) {
  return { category, search: search?.trim(), page, page_size: pageSize };
}

export function listCategories() {
  return request<{ results: Category[] }>("/api/v1/categories/", "GET");
}

export function listExercises(query: CatalogQuery = {}) {
  return request<Paginated<Exercise>>(withQuery("/api/v1/exercises/", catalogQuery(query)), "GET");
}

export function listWorkouts(query: CatalogQuery = {}) {
  return request<Paginated<WorkoutSummary>>(withQuery("/api/v1/workouts/", catalogQuery(query)), "GET");
}

export function getWorkout(id: number) {
  return request<WorkoutDetail>(`/api/v1/workouts/${id}/`, "GET");
}
