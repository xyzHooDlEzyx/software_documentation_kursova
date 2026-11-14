import type { Notification } from "./api";
import { getSession, type ScheduledSessionDetail } from "@/features/schedule/api";
import { resolveSessionNames } from "@/features/schedule/names";

export type NotificationSessionContext = {
  workout: string;
  scheduledAt: string | null;
};

/** Creates a successful-result cache scoped to one notification page instance. */
export function createNotificationSessionResolver() {
  const sessions = new Map<number, Promise<ScheduledSessionDetail | null>>();

  function session(id: number) {
    let pending = sessions.get(id);
    if (!pending) {
      pending = getSession(id).catch(() => {
        sessions.delete(id);
        return null;
      });
      sessions.set(id, pending);
    }
    return pending;
  }

  return async (notifications: Notification[]) => {
    const uniqueIds = [...new Set(notifications.map((item) => item.scheduled_session_id))];
    const loaded = await Promise.all(uniqueIds.map(async (id) => [id, await session(id)] as const));
    const byId = new Map(loaded);
    const available = loaded.flatMap(([, item]) => item ? [item] : []);
    const names = await resolveSessionNames(available);
    const result = new Map<number, NotificationSessionContext>();
    for (const item of notifications) {
      const slot = byId.get(item.scheduled_session_id);
      result.set(item.id, {
        workout: slot ? names.get(slot.id)?.workout ?? `Тренування #${slot.source_workout_id}` : `Тренування #${item.scheduled_session_id}`,
        scheduledAt: slot?.scheduled_at ?? null,
      });
    }
    return result;
  };
}
