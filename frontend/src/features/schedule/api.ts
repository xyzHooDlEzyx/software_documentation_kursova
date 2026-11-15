import { request, withQuery, type Paginated } from "@/app/api";

export type SessionStatus = "planned" | "completed" | "cancelled";
export type Reminder = { id: number; visible_at: string; status: "pending" | "read" | "cancelled"; read_at?: string | null; is_current: boolean };
export type ScheduledSession = {
  id: number;
  scheduled_at: string;
  status: SessionStatus;
  is_missed: boolean;
  user_program_id: number | null;
  user_program_workout_id: number | null;
  source_workout_id: number;
};
export type ScheduledSessionDetail = ScheduledSession & {
  reschedule_history: string[];
  completed_session_id: number | null;
  reminder: Reminder;
};

export async function listAllSessions(startDate: string, endDate: string) {
  const results: ScheduledSession[] = [];
  let page = 1;
  let count = 0;
  do {
    const response = await request<Paginated<ScheduledSession>>(withQuery("/api/v1/scheduled-sessions/", {
      start_date: startDate, end_date: endDate, page, page_size: 100,
    }), "GET");
    results.push(...response.results);
    count = response.count;
    page += 1;
  } while (results.length < count);
  return results;
}

export function createSession(body: { scheduled_at: string; user_program_workout_id: number | null; source_workout_id: number | null }) {
  return request<ScheduledSessionDetail>("/api/v1/scheduled-sessions/", "POST", body);
}

export function getSession(id: number) {
  return request<ScheduledSessionDetail>(`/api/v1/scheduled-sessions/${id}/`, "GET");
}

export function rescheduleSession(id: number, scheduled_at: string) {
  return request<ScheduledSessionDetail>(`/api/v1/scheduled-sessions/${id}/`, "PATCH", { scheduled_at });
}

export function cancelSession(id: number) {
  return request<Pick<ScheduledSessionDetail, "id" | "status" | "reminder">>(`/api/v1/scheduled-sessions/${id}/cancel/`, "POST", {});
}
