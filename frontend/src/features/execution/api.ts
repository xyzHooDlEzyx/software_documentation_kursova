import { request } from "@/app/api";

export type CompletionResultInput = {
  position: number;
  exercise_id: number;
  actual_sets: number | null;
  actual_reps: number | null;
  actual_load_kg: string | null;
  actual_duration_min: string | null;
  actual_distance_km: string | null;
};

export type CompletionInput = {
  scheduled_session_id: number | null;
  source_workout_id: number | null;
  duration_min: string;
  results: CompletionResultInput[];
};

export type UnlockedAchievement = {
  id?: number;
  name?: string;
  name_snapshot?: string;
};

export type CompletionResponse = {
  id: number;
  scheduled_session_id: number | null;
  source_workout_id: number;
  completed_at: string;
  duration_min: string;
  estimated_calories: string | null;
  missing_calorie_reason: string | null;
  workout_points: number;
  planned_day_bonus?: number;
  program: {
    id: number;
    status: string;
    progress_percent: string;
    bonus_earned: boolean;
  } | null;
  unlocked_achievements?: UnlockedAchievement[];
  newly_unlocked_achievements?: UnlockedAchievement[];
};

export function completeWorkout(body: CompletionInput, idempotencyKey: string) {
  return request<CompletionResponse>("/api/v1/completed-sessions/", "POST", body, {
    headers: { "Idempotency-Key": idempotencyKey },
  });
}
