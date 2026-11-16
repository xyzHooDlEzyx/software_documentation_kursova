import { useEffect, useRef, useState, type FormEvent } from "react";
import { Link, useParams } from "react-router";

import { PageHeader } from "@/components/layout";
import { Alert, Badge, Button, Card, LoadingState, TextInput, buttonVariants } from "@/components/ui";
import { errorMessage, fieldErrors, isApiError } from "@/lib/errors";
import { formatDateTime } from "@/lib/format";
import { kyivDateTimeInput, kyivLocalToUtcIso, kyivToday } from "@/lib/kyivDateTime";
import { label, notificationStatusLabels, scheduledSessionStatusLabels } from "@/lib/labels";
import { useResource } from "@/lib/useResource";
import { getProgram, getProgramProgress } from "@/features/programs/api";
import { cancelSession, getSession, rescheduleSession } from "./api";
import { clearSessionNameCache, resolveSessionNames, type SessionNames } from "./names";

export function reminderDescription(
  reminder: { visible_at: string; status: string; is_current: boolean },
  now = new Date(),
) {
  if (new Date(reminder.visible_at).getTime() > now.getTime())
    return `Нагадування з’явиться о ${formatDateTime(reminder.visible_at)}`;
  const state = label(notificationStatusLabels, reminder.status).toLocaleLowerCase("uk-UA");
  return `Нагадування: ${state}${reminder.is_current ? "" : ", неактуальне"}`;
}

export function SessionDetailPage() {
  const id = Number(useParams().id);
  const session = useResource(() => getSession(id), [id]);
  const [names, setNames] = useState<SessionNames | null>(null);
  const [date, setDate] = useState("");
  const [time, setTime] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [message, setMessage] = useState("");
  const [confirmCancel, setConfirmCancel] = useState(false);
  const [cancelBusy, setCancelBusy] = useState(false);
  const confirmContainerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    clearSessionNameCache();
  }, []);

  useEffect(() => {
    if (!session.data) return;
    const input = kyivDateTimeInput(session.data.scheduled_at);
    setDate(input.date);
    setTime(input.time);
    void resolveSessionNames([session.data]).then((resolved) => setNames(resolved.get(session.data!.id) ?? null));
  }, [session.data]);

  useEffect(() => {
    if (confirmCancel) confirmContainerRef.current?.querySelector("button")?.focus();
  }, [confirmCancel]);

  async function cancel() {
    setError("");
    setMessage("");
    setCancelBusy(true);
    try {
      await cancelSession(id);
      clearSessionNameCache();
      const current = await getSession(id);
      session.setData(current);
      if (current.user_program_id)
        await Promise.allSettled([getProgram(current.user_program_id), getProgramProgress(current.user_program_id)]);
      setConfirmCancel(false);
      setMessage("Заняття скасовано.");
    } catch (reason) {
      setError(
        isApiError(reason, 409) ? "Заняття вже завершено або програму закрито. Дані оновлено." : errorMessage(reason),
      );
      if (isApiError(reason, 409)) session.reload();
    } finally {
      setCancelBusy(false);
    }
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setMessage("");
    setErrors({});
    let value: string;
    try {
      value = kyivLocalToUtcIso(date, time);
    } catch {
      setErrors({ scheduled_at: "Оберіть коректний місцевий час." });
      return;
    }
    if (new Date(value).getTime() <= Date.now()) {
      setErrors({ scheduled_at: "Оберіть час у майбутньому." });
      return;
    }
    setBusy(true);
    try {
      await rescheduleSession(id, value);
      setMessage("Час тренування й нагадування оновлено.");
      session.reload();
    } catch (reason) {
      setErrors(fieldErrors(reason));
      setError(
        isApiError(reason, 409) ? "Стан тренування або програми змінився. Дані оновлено." : errorMessage(reason),
      );
      if (isApiError(reason, 409)) session.reload();
    } finally {
      setBusy(false);
    }
  }

  if (session.status === "loading" && !session.data) return <LoadingState text="Завантажуємо тренування…" />;
  if (session.status === "error" && !session.data)
    return (
      <Alert tone="error">
        {isApiError(session.error, 404) ? "Заплановане тренування не знайдено." : errorMessage(session.error)}
      </Alert>
    );
  const data = session.data!;
  const displayStatus = data.is_missed ? "missed" : data.status;
  return (
    <>
      <PageHeader
        title={names?.workout ?? `Тренування #${data.source_workout_id}`}
        eyebrow={
          data.status === "completed"
            ? "Завершене тренування"
            : data.status === "cancelled"
              ? "Скасоване тренування"
              : "Заплановане тренування"
        }
        description={formatDateTime(data.scheduled_at)}
      >
        <Link className={buttonVariants({ variant: "outlined", size: "sm" })} to="/schedule">
          До розкладу
        </Link>
      </PageHeader>
      <div className="grid gap-space-4 lg:grid-cols-[minmax(0,1fr)_minmax(18rem,0.7fr)]">
        <div className="grid content-start gap-space-4">
          {message && (
            <Alert tone="success" aria-live="polite">
              {message}
            </Alert>
          )}
          {error && <Alert tone="error">{error}</Alert>}
          <Card className="grid gap-space-3 p-space-4 sm:p-space-6">
            <div className="flex flex-wrap gap-space-2">
              <Badge tone="brand">{label(scheduledSessionStatusLabels, displayStatus)}</Badge>
              {!data.reminder.is_current && <Badge tone="outline">Нагадування неактуальне</Badge>}
            </div>
            {names?.program && data.user_program_id && (
              <p className="m-0">
                Програма: <Link to={`/programs/${data.user_program_id}`}>{names.program}</Link>
              </p>
            )}
            <p className="m-0">
              Джерело:{" "}
              <Link to={`/catalog/workouts/${data.source_workout_id}`}>
                {names?.workout ?? `Тренування #${data.source_workout_id}`}
              </Link>
            </p>
            <p className="m-0 text-small text-muted-foreground">{reminderDescription(data.reminder)}</p>
          </Card>
          <Card className="p-space-4 sm:p-space-6">
            <h2 className="mt-0 text-title-small">Історія перенесень</h2>
            {data.reschedule_history.length ? (
              <ul className="mb-0 grid gap-space-1">
                {data.reschedule_history.map((item) => (
                  <li key={item}>{formatDateTime(item)}</li>
                ))}
              </ul>
            ) : (
              <p className="mb-0 text-muted-foreground">Час ще не переносили.</p>
            )}
          </Card>
        </div>
        {data.status === "planned" && (
          <div className="grid h-fit gap-space-4">
            <Card className="grid gap-space-3 p-space-4 sm:p-space-6">
              <h2 className="m-0 text-title-small">Дії із заняттям</h2>
              <div className="flex flex-wrap gap-space-2">
                <Link
                  className={buttonVariants({ variant: "primary", size: "md" })}
                  to={`/schedule/${data.id}/complete`}
                >
                  Завершити тренування
                </Link>
                <Button variant="outlined" onClick={() => setConfirmCancel(true)}>
                  Скасувати заняття
                </Button>
              </div>
              {confirmCancel && (
                <div
                  ref={confirmContainerRef}
                  className="grid gap-space-3 rounded-field border border-status-warning/30 bg-status-warning/10 p-space-3"
                  role="group"
                  aria-labelledby="cancel-title"
                >
                  <div>
                    <h3 id="cancel-title" className="m-0 text-base font-bold">
                      Скасувати це заняття?
                    </h3>
                    <p className="mb-0 mt-space-1 text-small">Запис залишиться в розкладі зі станом «Скасовано».</p>
                  </div>
                  <div className="flex flex-wrap gap-space-2">
                    <Button loading={cancelBusy} onClick={() => void cancel()}>
                      Так, скасувати
                    </Button>
                    <Button variant="outlined" disabled={cancelBusy} onClick={() => setConfirmCancel(false)}>
                      Не скасовувати
                    </Button>
                  </div>
                </div>
              )}
            </Card>
            <Card className="p-space-4 sm:p-space-6">
              <h2 className="mt-0 text-title-small">Перенести тренування</h2>
              <form className="grid gap-space-3" onSubmit={(event) => void submit(event)} noValidate>
                <TextInput
                  id="reschedule-date"
                  label="Нова дата"
                  type="date"
                  min={kyivToday()}
                  value={date}
                  onChange={(event) => setDate(event.target.value)}
                />
                <TextInput
                  id="reschedule-time"
                  label="Новий час (Київ)"
                  type="time"
                  value={time}
                  onChange={(event) => setTime(event.target.value)}
                  error={errors.scheduled_at}
                />
                <div>
                  <Button type="submit" loading={busy}>
                    Перенести
                  </Button>
                </div>
              </form>
            </Card>
          </div>
        )}
      </div>
    </>
  );
}
