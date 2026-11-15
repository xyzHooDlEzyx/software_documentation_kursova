import { request, withQuery, type Paginated } from "@/app/api";
import type { RecommendedParameters } from "@/features/catalog/api";

export type Recommendation = {
  program_template: {
    id: number;
    name: string;
    description: string;
    fitness_goal: string;
    experience_level: string;
    workouts_per_week: number;
    workouts: { position: number; workout_id: number; name: string }[];
  };
  reason: {
    exact_goal: boolean;
    exact_level: boolean;
    frequency_difference: number;
    strategy: string;
    composition_criterion: string;
  };
};

export type UserProgramSummary = {
  id: number;
  name: string;
  status: string;
  is_archived: boolean;
  source_program_template_id: number;
  progress_percent: string;
  bonus_earned: boolean;
};

export type ProgramExercise = RecommendedParameters & {
  position: number;
  exercise_id: number;
};

export type ProgramWorkout = {
  entry_id: number;
  position: number;
  source_workout_id: number;
  name: string;
  category: string;
  exercises: ProgramExercise[];
};

export type UserProgramDetail = {
  id: number;
  name: string;
  description: string;
  fitness_goal: string;
  status: string;
  is_archived: boolean;
  source_program_template_id: number;
  source_program_template_name_snapshot: string;
  bonus_target_sessions: number | null;
  progress: { total_planned: number; completed_planned: number; percent: string };
  completion_snapshot: CompletionSnapshot | null;
  bonus_earned: boolean;
  workouts: ProgramWorkout[];
};

export type CompletionSnapshot = {
  completed_at: string;
  total_planned_at_completion: number;
  completed_planned_at_completion: number;
  progress_percent_at_completion: string;
};

export type ProgramProgress = {
  user_program_id: number;
  status: string;
  is_archived: boolean;
  total_planned: number;
  completed_planned: number;
  percent: string;
  bonus_target_sessions: number | null;
  bonus_earned: boolean;
  completion_snapshot: CompletionSnapshot | null;
};

export type CompositionItem = RecommendedParameters & { position: number; exercise_id: number };

export function getRecommendation() {
  return request<Recommendation>("/api/v1/program-recommendation/", "GET");
}

export function listPrograms({ status, archived = false, page = 1 }: { status?: string; archived?: boolean; page?: number } = {}) {
  return request<Paginated<UserProgramSummary>>(withQuery("/api/v1/user-programs/", { status, archived, page }), "GET");
}

/** G03: copies the template that the server currently recommends. */
export function createProgram(programTemplateId: number) {
  return request<UserProgramDetail>("/api/v1/user-programs/", "POST", { program_template_id: programTemplateId });
}

export function getProgram(id: number) {
  return request<UserProgramDetail>(`/api/v1/user-programs/${id}/`, "GET");
}

export function updateProgram(id: number, changes: { name?: string; description?: string }) {
  return request<Pick<UserProgramDetail, "id" | "name" | "description" | "status" | "is_archived">>(`/api/v1/user-programs/${id}/`, "PATCH", changes);
}

export function activateProgram(id: number) {
  return request<Pick<UserProgramDetail, "id" | "status" | "is_archived" | "bonus_target_sessions" | "progress"> & { activated_at: string }>(`/api/v1/user-programs/${id}/activate/`, "POST", {});
}

export function getProgramProgress(id: number) {
  return request<ProgramProgress>(`/api/v1/user-programs/${id}/progress/`, "GET");
}

export function archiveProgram(id: number) {
  return request<Pick<UserProgramDetail, "id" | "status" | "is_archived" | "bonus_earned">>(`/api/v1/user-programs/${id}/archive/`, "POST", {});
}

/** G06: replaces the whole personal composition of one workout occurrence. */
export function replaceComposition(programId: number, entryId: number, name: string, exercises: CompositionItem[]) {
  return request<ProgramWorkout>(`/api/v1/user-programs/${programId}/workouts/${entryId}/`, "PUT", { name, exercises });
}
