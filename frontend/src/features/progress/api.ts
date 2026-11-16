import { request, withQuery, type Paginated } from "@/app/api";

export type ApiPeriod = { start_date: string; end_date: string; timezone: string };
export type WeeklyActivity = { week_start: string; completed_workouts: number; total_duration_min: string };
export type Overview = {
  period: ApiPeriod;
  completed_workouts: number;
  performed_exercises: number;
  total_duration_min: string;
  estimated_calories_total: string;
  workouts_without_calorie_estimate: number;
  weekly_activity: WeeklyActivity[];
};
type OverviewResponse = Omit<Overview, "weekly_activity"> & { weekly_activity?: WeeklyActivity[] };
export type WeightPoint = { measured_at: string; weight_kg: string };
export type WeightChartResponse = { period: ApiPeriod; points: WeightPoint[] };
export type CompletedSessionSummary = {
  id: number;
  completed_at: string;
  source_workout_id: number;
  source_workout_name_snapshot: string;
  performed_workout_name_snapshot: string;
  duration_min: string;
  estimated_calories: string | null;
  workout_points: number;
};
export type ExerciseResult = {
  id: number;
  position: number;
  source_exercise_id: number;
  exercise_name_snapshot: string;
  exercise_category_snapshot: string;
  actual_sets: number | null;
  actual_reps: number | null;
  actual_load_kg: string | null;
  actual_duration_min: string | null;
  actual_distance_km: string | null;
};
export type CompletedSessionDetail = CompletedSessionSummary & {
  scheduled_session_id: number | null;
  source_workout_id_snapshot: number;
  performed_workout_category_snapshot: string;
  program_context: {
    source_program_template_id_snapshot: number;
    source_program_template_name_snapshot: string;
    user_program_id_snapshot: number;
    user_program_name_snapshot: string;
  } | null;
  weight_kg_snapshot: string;
  estimated_calories: string | null;
  missing_calorie_reason: string | null;
  results: ExerciseResult[];
};
export type PointsSummary = {
  period: ApiPeriod | null;
  total_points: number;
  workout_points: number;
  program_bonus_points: number;
};
export type PointTransaction = {
  id: number;
  point_kind: "workout_completion" | "program_completion";
  points: number;
  awarded_at: string;
  source: { kind: "completed_session" | "user_program"; id: number };
};
export type Achievement = { id: number; code: string; name: string; description: string; earned: boolean };
export type UserAchievement = {
  id: number;
  achievement_id: number;
  rule_code_snapshot: string;
  name_snapshot: string;
  unlocked_at: string;
};
export type Challenge = {
  id: number;
  name: string;
  start_at: string;
  end_at: string;
  goal_kind: string;
  goal_value: number;
  joined: boolean;
};
export type ChallengeParticipation = {
  id: number;
  challenge_id: number;
  challenge_name: string;
  joined_at: string;
  status: "joined" | "completed" | "expired";
  goal_kind: string;
  goal_value: number;
  progress_value: number;
  completed_at: string | null;
};
export type JoinResponse = {
  id: number;
  challenge_id: number;
  joined_at: string;
  status: string;
  progress_value: number;
  goal_value: number;
};
export type Leaderboard = {
  period: { kind: string; start_at: string | null; end_at: string | null };
  count: number;
  next: string | null;
  previous: string | null;
  results: { rank: number; public_alias: string; points: number }[];
  self: { opted_in: boolean; points: number; rank: number | null };
};

const dates = (startDate?: string, endDate?: string) => ({ start_date: startDate, end_date: endDate });
export const getOverview = async (startDate: string, endDate: string): Promise<Overview> => {
  const response = await request<OverviewResponse>(
    withQuery("/api/v1/statistics/overview/", dates(startDate, endDate)),
    "GET",
  );
  return { ...response, weekly_activity: response.weekly_activity ?? [] };
};
export const getWeightChart = (startDate: string, endDate: string) =>
  request<WeightChartResponse>(withQuery("/api/v1/statistics/weight-chart/", dates(startDate, endDate)), "GET");
export const listCompletedSessions = (startDate: string, endDate: string, page = 1, pageSize = 20) =>
  request<Paginated<CompletedSessionSummary>>(
    withQuery("/api/v1/completed-sessions/", { ...dates(startDate, endDate), page, page_size: pageSize }),
    "GET",
  );
export const getCompletedSession = (id: number) =>
  request<CompletedSessionDetail>(`/api/v1/completed-sessions/${id}/`, "GET");
export const getPointsSummary = (startDate: string, endDate: string) =>
  request<PointsSummary>(withQuery("/api/v1/points/summary/", dates(startDate, endDate)), "GET");
export const getAllTimePointsSummary = () => request<PointsSummary>("/api/v1/points/summary/", "GET");
export const listPointTransactions = (startDate: string, endDate: string, page = 1, pageSize = 20) =>
  request<Paginated<PointTransaction>>(
    withQuery("/api/v1/point-transactions/", { ...dates(startDate, endDate), page, page_size: pageSize }),
    "GET",
  );
export const listAchievements = () =>
  request<Paginated<Achievement>>(withQuery("/api/v1/achievements/", { page: 1, page_size: 100 }), "GET");
export const listUserAchievements = () =>
  request<Paginated<UserAchievement>>(withQuery("/api/v1/user-achievements/", { page: 1, page_size: 100 }), "GET");
export const listChallenges = (state: string, page = 1, pageSize = 20) =>
  request<Paginated<Challenge>>(withQuery("/api/v1/challenges/", { state, page, page_size: pageSize }), "GET");
export const getChallenge = (id: number) => request<Challenge>(`/api/v1/challenges/${id}/`, "GET");
export const joinChallenge = (id: number) => request<JoinResponse>(`/api/v1/challenges/${id}/join/`, "POST", {});
export const listParticipations = (status: string, page = 1, pageSize = 20) =>
  request<Paginated<ChallengeParticipation>>(
    withQuery("/api/v1/challenge-participations/", { status, page, page_size: pageSize }),
    "GET",
  );
export const getLeaderboard = (period: string, page = 1, pageSize = 20) =>
  request<Leaderboard>(withQuery("/api/v1/leaderboard/", { period, page, page_size: pageSize }), "GET");
