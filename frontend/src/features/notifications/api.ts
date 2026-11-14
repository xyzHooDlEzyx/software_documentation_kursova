import { request, withQuery, type Paginated } from "@/app/api";

export type Notification = {
  id: number;
  scheduled_session_id: number;
  type: string;
  visible_at: string;
  status: "pending" | "read" | "cancelled";
  read_at: string | null;
  is_current: boolean;
};

export function listNotifications(query: { status?: string; isCurrent?: string; page?: number; pageSize?: number } = {}) {
  return request<Paginated<Notification>>(withQuery("/api/v1/notifications/", {
    status: query.status,
    is_current: query.isCurrent,
    page: query.page ?? 1,
    page_size: query.pageSize,
  }), "GET");
}

export function getNotification(id: number) {
  return request<Notification>(`/api/v1/notifications/${id}/`, "GET");
}

export function markNotificationRead(id: number) {
  return request<Notification>(`/api/v1/notifications/${id}/read/`, "POST", {});
}
