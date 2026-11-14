import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router";

import { PageHeader } from "@/components/layout";
import { Alert, Badge, Button, Card, LoadingState, buttonVariants } from "@/components/ui";
import { errorMessage, isApiError } from "@/lib/errors";
import { formatDateTime } from "@/lib/format";
import { label, notificationStatusLabels } from "@/lib/labels";
import { useResource } from "@/lib/useResource";
import { getNotification, markNotificationRead } from "./api";
import { clearSessionNameCache } from "@/features/schedule/names";
import { createNotificationSessionResolver, type NotificationSessionContext } from "./sessionContext";

export function NotificationDetailPage() {
  const id = Number(useParams().id);
  const notification = useResource(() => getNotification(id), [id]);
  const [sessionContext, setSessionContext] = useState<NotificationSessionContext | null>(null);
  const resolveSessions = useMemo(() => createNotificationSessionResolver(), []);

  useEffect(() => {
    clearSessionNameCache();
  }, []);

  useEffect(() => {
    let active = true;
    if (notification.data) void resolveSessions([notification.data]).then((contexts) => { if (active) setSessionContext(contexts.get(notification.data!.id) ?? null); });
    return () => { active = false; };
  }, [notification.data, resolveSessions]);

  async function markRead() {
    try {
      const saved = await markNotificationRead(id);
      notification.setData(saved);
      window.dispatchEvent(new Event("notification-read"));
    } catch (reason) {
      if (isApiError(reason, 404)) notification.reload();
      else throw reason;
    }
  }

  if (notification.status === "loading" && !notification.data) return <LoadingState text="Завантажуємо сповіщення…" />;
  if (notification.status === "error" && !notification.data) return <div className="grid gap-space-3"><Alert tone="error">{isApiError(notification.error, 404) ? "Сповіщення більше недоступне." : errorMessage(notification.error)}</Alert><div><Link className={buttonVariants({ variant: "outlined" })} to="/notifications">До сповіщень</Link></div></div>;
  const data = notification.data!;
  return <>
    <PageHeader title={sessionContext?.workout ?? `Тренування #${data.scheduled_session_id}`} eyebrow="Сповіщення" description={sessionContext?.scheduledAt ? `Тренування о ${formatDateTime(sessionContext.scheduledAt)} · нагадування з ${formatDateTime(data.visible_at)}` : `Нагадування з ${formatDateTime(data.visible_at)}`}>
      <Link className={buttonVariants({ variant: "outlined", size: "sm" })} to="/notifications">До списку</Link>
    </PageHeader>
    <Card className="grid gap-space-4 p-space-4 sm:p-space-6">
      <div className="flex flex-wrap gap-space-2"><Badge tone={data.status === "pending" ? "brand" : "neutral"}>{label(notificationStatusLabels, data.status)}</Badge>{!data.is_current && <Badge tone="outline">Неактуальне</Badge>}</div>
      <p className="m-0 text-muted-foreground">Нагадування про заплановане тренування. Перегляд цієї сторінки не змінює його статус.</p>
      <div className="flex flex-wrap gap-space-2">
        <Link className={buttonVariants({ size: "sm" })} to={`/schedule/${data.scheduled_session_id}`}>Відкрити тренування</Link>
        {data.status === "pending" && <Button variant="outlined" size="sm" onClick={() => void markRead()}>Позначити прочитаним</Button>}
      </div>
    </Card>
  </>;
}
