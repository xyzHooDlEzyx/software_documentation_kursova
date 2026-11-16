import { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router";

import { PageHeader } from "@/components/layout";
import {
  Alert,
  Badge,
  Button,
  Card,
  EmptyState,
  LoadingState,
  Pagination,
  Select,
  buttonVariants,
} from "@/components/ui";
import { errorMessage, isApiError } from "@/lib/errors";
import { formatDateTime } from "@/lib/format";
import { label, notificationStatusLabels } from "@/lib/labels";
import { useResource } from "@/lib/useResource";
import { listNotifications, markNotificationRead } from "./api";
import { useVisiblePolling } from "./useVisiblePolling";
import { clearSessionNameCache } from "@/features/schedule/names";
import { createNotificationSessionResolver, type NotificationSessionContext } from "./sessionContext";

const PAGE_SIZE = 10;

export function NotificationsPage() {
  const [params, setParams] = useSearchParams();
  const status = params.get("status") ?? "";
  const isCurrent = params.get("is_current") ?? "";
  const page = Math.max(1, Number(params.get("page")) || 1);
  const notifications = useResource(
    () => listNotifications({ status, isCurrent, page, pageSize: PAGE_SIZE }),
    [status, isCurrent, page],
  );
  const [message, setMessage] = useState("");
  const [busyId, setBusyId] = useState<number | null>(null);
  const [sessionContexts, setSessionContexts] = useState(new Map<number, NotificationSessionContext>());
  const resolveSessions = useMemo(() => createNotificationSessionResolver(), []);
  useVisiblePolling(notifications.reload);

  useEffect(() => {
    clearSessionNameCache();
  }, []);

  useEffect(() => {
    let active = true;
    if (notifications.data)
      void resolveSessions(notifications.data.results).then((contexts) => {
        if (active) setSessionContexts(contexts);
      });
    return () => {
      active = false;
    };
  }, [notifications.data, resolveSessions]);

  function update(key: string, value: string) {
    const next = new URLSearchParams(params);
    if (value) next.set(key, value);
    else next.delete(key);
    if (key !== "page") next.delete("page");
    setParams(next);
  }

  async function markRead(id: number) {
    setBusyId(id);
    setMessage("");
    try {
      const saved = await markNotificationRead(id);
      if (notifications.data) {
        const keep =
          status === "pending"
            ? notifications.data.results.filter((item) => item.id !== id)
            : notifications.data.results.map((item) => (item.id === id ? saved : item));
        notifications.setData({
          ...notifications.data,
          count: status === "pending" ? Math.max(0, notifications.data.count - 1) : notifications.data.count,
          results: keep,
        });
      }
      setMessage("Сповіщення позначено прочитаним.");
      window.dispatchEvent(new Event("notification-read"));
    } catch (reason) {
      setMessage(isApiError(reason, 404) ? "Сповіщення більше недоступне. Список оновлено." : errorMessage(reason));
      notifications.reload();
    } finally {
      setBusyId(null);
    }
  }

  return (
    <>
      <PageHeader
        title="Мої сповіщення"
        eyebrow="Нагадування"
        description="Час відображено за Києвом. Відкриття не позначає сповіщення прочитаним."
      />
      <div className="mb-space-4 grid gap-space-3 sm:grid-cols-2">
        <Select
          id="notification-status"
          label="Статус"
          value={status}
          onChange={(event) => update("status", event.target.value)}
          placeholder="Усі"
          options={[
            { value: "pending", label: "Непрочитані" },
            { value: "read", label: "Прочитані" },
          ]}
        />
        <Select
          id="notification-current"
          label="Актуальність"
          value={isCurrent}
          onChange={(event) => update("is_current", event.target.value)}
          placeholder="Усі"
          options={[
            { value: "true", label: "Актуальні" },
            { value: "false", label: "Неактуальні" },
          ]}
        />
      </div>
      {message && (
        <Alert tone={message.includes("позначено") ? "success" : "warning"} className="mb-space-4" aria-live="polite">
          {message}
        </Alert>
      )}
      {notifications.status === "loading" && !notifications.data && <LoadingState text="Завантажуємо сповіщення…" />}
      {notifications.status === "error" && !notifications.data && (
        <Alert tone="error">{errorMessage(notifications.error)}</Alert>
      )}
      {notifications.data?.count === 0 && (
        <EmptyState title="Сповіщень немає">Нагадування з’являться тут, коли настане час їх показу.</EmptyState>
      )}
      {!!notifications.data?.results.length && (
        <div className="grid gap-space-3">
          {notifications.data.results.map((item) => {
            const context = sessionContexts.get(item.id);
            return (
              <Card
                key={item.id}
                className={`grid gap-space-3 p-space-4 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-center ${!item.is_current ? "opacity-70" : ""}`}
              >
                <div className="min-w-0">
                  <div className="mb-space-2 flex flex-wrap gap-space-2">
                    <Badge tone={item.status === "pending" ? "brand" : "neutral"}>
                      {label(notificationStatusLabels, item.status)}
                    </Badge>
                    {!item.is_current && <Badge tone="outline">Неактуальне</Badge>}
                  </div>
                  <h2 className="m-0 text-title-small">
                    <Link to={`/notifications/${item.id}`}>
                      {context?.workout ?? `Тренування #${item.scheduled_session_id}`}
                    </Link>
                  </h2>
                  <p className="mb-0 mt-space-1 text-small text-muted-foreground">
                    {context?.scheduledAt
                      ? `Тренування о ${formatDateTime(context.scheduledAt)} · нагадування з ${formatDateTime(item.visible_at)}`
                      : `Нагадування з ${formatDateTime(item.visible_at)}`}
                  </p>
                </div>
                <div className="flex flex-wrap gap-space-2">
                  <Link
                    className={buttonVariants({ variant: "outlined", size: "sm" })}
                    to={`/schedule/${item.scheduled_session_id}`}
                  >
                    Відкрити тренування
                  </Link>
                  {item.status === "pending" && (
                    <Button size="sm" loading={busyId === item.id} onClick={() => void markRead(item.id)}>
                      Позначити прочитаним
                    </Button>
                  )}
                </div>
              </Card>
            );
          })}
          <Pagination
            page={page}
            pageSize={PAGE_SIZE}
            count={notifications.data.count}
            onPage={(value) => update("page", String(value))}
          />
        </div>
      )}
    </>
  );
}
