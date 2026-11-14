import { useState, type FormEvent } from "react";

import { Link } from "react-router";

import { Alert, Button, TextInput, buttonVariants } from "@/components/ui";
import { errorMessage, fieldErrors } from "@/lib/errors";
import { formatTime } from "@/lib/format";
import { kyivLocalToUtcIso, kyivToday } from "@/lib/kyivDateTime";
import { createSession, type ScheduledSessionDetail } from "./api";

type Source = { user_program_workout_id: number; source_workout_id?: never } | { source_workout_id: number; user_program_workout_id?: never };

export function ScheduleForm({ source, onCreated, onClose }: { source: Source; onCreated?: (session: ScheduledSessionDetail) => void; onClose?: () => void }) {
  const [date, setDate] = useState(kyivToday());
  const [time, setTime] = useState("");
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [createdId, setCreatedId] = useState<number | null>(null);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    const nextErrors: Record<string, string> = {};
    if (!date) nextErrors.date = "Оберіть дату.";
    if (!time) nextErrors.time = "Оберіть час.";
    let scheduledAt = "";
    if (!Object.keys(nextErrors).length) {
      try { scheduledAt = kyivLocalToUtcIso(date, time); }
      catch { nextErrors.scheduled_at = "Цей місцевий час не існує або має неправильний формат."; }
      if (scheduledAt && new Date(scheduledAt).getTime() <= Date.now()) nextErrors.scheduled_at = "Оберіть час у майбутньому.";
    }
    setErrors(nextErrors);
    if (Object.keys(nextErrors).length) return;
    setMessage("");
    setCreatedId(null);
    setBusy(true);
    try {
      const created = await createSession({
        scheduled_at: scheduledAt,
        user_program_workout_id: "user_program_workout_id" in source ? source.user_program_workout_id ?? null : null,
        source_workout_id: "source_workout_id" in source ? source.source_workout_id ?? null : null,
      });
      const available = new Date(created.reminder.visible_at).getTime() <= Date.now();
      setMessage(available ? "Тренування заплановано. Нагадування вже доступне." : `Тренування заплановано. Нагадування з’явиться о ${formatTime(created.reminder.visible_at)}.`);
      setTime("");
      setCreatedId(created.id);
      onCreated?.(created);
    } catch (reason) {
      const fields = fieldErrors(reason);
      setErrors({ ...fields, scheduled_at: fields.scheduled_at });
      setError(errorMessage(reason));
    } finally { setBusy(false); }
  }

  return (
    <form className="grid gap-space-3" onSubmit={(event) => void submit(event)} noValidate>
      {message && <Alert tone="success" aria-live="polite">{message}</Alert>}
      {error && <Alert tone="error">{error}</Alert>}
      <div className="grid gap-space-3 sm:grid-cols-2">
        <TextInput id={`schedule-date-${"user_program_workout_id" in source ? `p${source.user_program_workout_id}` : `w${source.source_workout_id}`}`} label="Дата" type="date" value={date} min={kyivToday()} onChange={(event) => setDate(event.target.value)} error={errors.date} />
        <TextInput id={`schedule-time-${"user_program_workout_id" in source ? `p${source.user_program_workout_id}` : `w${source.source_workout_id}`}`} label="Час (Київ)" type="time" value={time} onChange={(event) => setTime(event.target.value)} error={errors.time ?? errors.scheduled_at} />
      </div>
      <div className="flex flex-wrap gap-space-2">
        <Button type="submit" loading={busy}>Запланувати</Button>
        {onClose && <Button type="button" variant="outlined" onClick={onClose} disabled={busy}>{createdId ? "Закрити" : "Скасувати"}</Button>}
        {createdId && <Link className={buttonVariants({ variant: "outlined" })} to={`/schedule/${createdId}`}>Відкрити в розкладі</Link>}
      </div>
    </form>
  );
}
