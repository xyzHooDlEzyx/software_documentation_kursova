import { useEffect, useRef, useState, type FormEvent } from "react";
import { Link, useLocation, useParams } from "react-router";

import { PageHeader } from "@/components/layout";
import { Alert, Badge, Button, Card, LoadingState, TextInput, buttonVariants } from "@/components/ui";
import { describeParameters } from "@/features/catalog/parameters";
import { exerciseNames, fetchAllExercises } from "@/features/catalog/exerciseIndex";
import { errorMessage, fieldErrors, isApiError } from "@/lib/errors";
import { formatDateTime, formatDecimal } from "@/lib/format";
import { categoryLabels, goalLabels, label, programStatusLabels } from "@/lib/labels";
import { useResource } from "@/lib/useResource";
import { ScheduleForm } from "@/features/schedule/ScheduleForm";
import { activateProgram, archiveProgram, getProgram, getProgramProgress, updateProgram, type UserProgramDetail } from "./api";

export function isProgramEditable(program: Pick<UserProgramDetail, "status" | "is_archived">) {
  return program.status !== "completed" && !program.is_archived;
}

function RenameForm({ program, onSaved, onCancel }: { program: UserProgramDetail; onSaved: (changes: { name: string; description: string }) => void; onCancel: () => void }) {
  const [name, setName] = useState(program.name);
  const [description, setDescription] = useState(program.description);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    if (!name.trim()) { setErrors({ name: "Назва не може бути порожньою." }); return; }
    setBusy(true);
    try {
      const saved = await updateProgram(program.id, { name: name.trim(), description });
      onSaved({ name: saved.name, description: saved.description });
    } catch (reason) {
      setErrors(fieldErrors(reason));
      setError(isApiError(reason, 409) ? "Завершену або архівну програму змінювати не можна." : errorMessage(reason));
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="grid gap-space-4" onSubmit={(event) => void submit(event)} noValidate>
      {error && <Alert tone="error">{error}</Alert>}
      <TextInput id="program-name" label="Назва програми" value={name} maxLength={160} onChange={(event) => setName(event.target.value)} error={errors.name} />
      <div className="grid gap-space-1">
        <label className="text-sm font-semibold" htmlFor="program-description">Опис</label>
        <textarea id="program-description" className="min-h-24 w-full rounded-field border border-input-border bg-card px-3 py-2 text-base focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring" value={description} onChange={(event) => setDescription(event.target.value)} />
        {errors.description && <span className="text-xs text-status-error">{errors.description}</span>}
      </div>
      <div className="flex gap-space-2">
        <Button type="submit" loading={busy}>Зберегти</Button>
        <Button variant="outlined" onClick={onCancel} disabled={busy}>Скасувати</Button>
      </div>
    </form>
  );
}

export function ProgramDetailPage() {
  const id = Number(useParams().id);
  const location = useLocation();
  const program = useResource(() => getProgram(id), [id]);
  const exercises = useResource(() => fetchAllExercises(), []);
  const [editing, setEditing] = useState(false);
  const [message, setMessage] = useState<string>((location.state as { message?: string } | null)?.message ?? "");
  const [activationError, setActivationError] = useState("");
  const [activationBusy, setActivationBusy] = useState(false);
  const [schedulingEntry, setSchedulingEntry] = useState<number | null>(null);
  const [archiveConfirm, setArchiveConfirm] = useState(false);
  const [archiveBusy, setArchiveBusy] = useState(false);
  const [archiveError, setArchiveError] = useState<"planned" | "active" | "generic" | "">("");
  const archiveConfirmRef = useRef<HTMLDivElement>(null);
  const back = <Link className={buttonVariants({ variant: "outlined", size: "sm" })} to="/programs">До програм</Link>;

  useEffect(() => { if (archiveConfirm) archiveConfirmRef.current?.querySelector("button")?.focus(); }, [archiveConfirm]);

  if (program.status === "loading" && !program.data) return <LoadingState text="Завантажуємо програму…" />;
  if (program.status === "error" && !program.data) {
    const text = isApiError(program.error, 404) ? "Програму не знайдено." : errorMessage(program.error);
    return <div className="grid gap-space-3"><Alert tone="error">{text}</Alert><div>{back}</div></div>;
  }

  const data = program.data!;
  const editable = isProgramEditable(data);
  const names = exerciseNames(exercises.data ?? []);

  async function activate() {
    setActivationError(""); setActivationBusy(true);
    try { await activateProgram(data.id); setMessage("Програму активовано."); program.reload(); }
    catch (reason) {
      setActivationError(isApiError(reason, 400) ? "Спочатку заплануйте хоча б одне тренування цієї програми." : isApiError(reason, 409) ? "Програму вже не можна активувати в її поточному стані. Дані оновлено." : errorMessage(reason));
      if (isApiError(reason, 409)) program.reload();
    } finally { setActivationBusy(false); }
  }

  async function archive() {
    setArchiveError(""); setArchiveBusy(true);
    try {
      await archiveProgram(data.id);
      const [detail, progress] = await Promise.all([getProgram(data.id), getProgramProgress(data.id)]);
      program.setData({
        ...detail,
        status: progress.status,
        is_archived: progress.is_archived,
        progress: { total_planned: progress.total_planned, completed_planned: progress.completed_planned, percent: progress.percent },
        completion_snapshot: progress.completion_snapshot,
        bonus_earned: progress.bonus_earned,
      });
      setArchiveConfirm(false);
      setMessage("Програму архівовано.");
    } catch (reason) {
      if (isApiError(reason, 409, "planned_sessions_exist")) setArchiveError("planned");
      else if (isApiError(reason, 409, "invalid_state")) setArchiveError("active");
      else setArchiveError("generic");
    } finally { setArchiveBusy(false); }
  }

  return (
    <>
      <PageHeader title={data.name} eyebrow="Програма" description={data.description || undefined}>
        {back}
        {editable && !editing && <Button variant="outlined" size="sm" onClick={() => { setMessage(""); setEditing(true); }}>Перейменувати</Button>}
      </PageHeader>
      <div className="grid gap-space-6">
        {message && <Alert tone="success">{message}</Alert>}
        {activationError && <Alert tone="error">{activationError}</Alert>}
        {archiveError === "planned" && <Alert tone="error">Спочатку скасуйте заплановані заняття цієї програми. <Link to={`/schedule?user_program_id=${data.id}`}>Перейти до розкладу</Link></Alert>}
        {archiveError === "active" && <Alert tone="error">Активну програму не можна архівувати.</Alert>}
        {archiveError === "generic" && <Alert tone="error">Не вдалося архівувати програму. Спробуйте ще раз.</Alert>}
        {!editable && <Alert tone="info">Програма {data.is_archived ? "в архіві" : "завершена"}: склад і назву змінювати не можна.</Alert>}
        {editing && (
          <Card className="p-space-4 sm:p-space-6">
            <RenameForm program={data} onCancel={() => setEditing(false)} onSaved={(changes) => { program.setData({ ...data, ...changes }); setEditing(false); setMessage("Назву й опис збережено."); }} />
          </Card>
        )}
        <Card className="flex flex-wrap gap-space-2 p-space-4">
          <Badge tone={data.status === "active" ? "brand" : "neutral"}>{label(programStatusLabels, data.status)}</Badge>
          <Badge tone="accent">{label(goalLabels, data.fitness_goal)}</Badge>
          <Badge tone="outline">Шаблон: {data.source_program_template_name_snapshot}</Badge>
          <Badge tone="outline">Прогрес: {data.progress.completed_planned}/{data.progress.total_planned} ({data.progress.percent}%)</Badge>
          {data.status === "active" && data.bonus_target_sessions !== null && <Badge tone="accent">Бонус +50 після {data.bonus_target_sessions} завершених занять</Badge>}
        </Card>
        <Card className="grid gap-space-3 p-space-4 sm:p-space-6">
          <div className="flex flex-wrap items-baseline justify-between gap-space-2"><h2 className="m-0 text-title-small">Прогрес програми</h2><strong>{data.progress.completed_planned} / {data.progress.total_planned}</strong></div>
          <div className="h-3 overflow-hidden rounded-chip bg-muted" role="progressbar" aria-label="Прогрес програми" aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.min(100, Number(data.progress.percent))}>
            <div className="h-full bg-accent" style={{ width: `${Math.min(100, Number(data.progress.percent))}%` }} />
          </div>
          <p className="m-0 text-small text-muted-foreground">{formatDecimal(data.progress.percent)}% запланованих занять завершено</p>
          {data.completion_snapshot && <div className="grid gap-space-1 border-t border-outline pt-space-3 text-small"><strong>Завершено {formatDateTime(data.completion_snapshot.completed_at)}</strong><span>Підсумок: {data.completion_snapshot.completed_planned_at_completion} / {data.completion_snapshot.total_planned_at_completion} ({formatDecimal(data.completion_snapshot.progress_percent_at_completion)}%)</span></div>}
          {data.bonus_earned && <p className="m-0 font-semibold text-status-success">Бонус +50 отримано</p>}
        </Card>
        {data.status === "draft" && !data.is_archived && <Card className="grid gap-space-3 p-space-4 sm:p-space-6">
          <div><h2 className="m-0 text-title-small">Активація програми</h2><p className="mb-0 mt-space-1 text-small text-muted-foreground">Заплановано занять: {data.progress.total_planned}. Поріг бонусу визначить сервер під час активації.</p></div>
          {data.progress.total_planned === 0 && <p className="m-0 text-small" id="activation-hint">Щоб активувати програму, спочатку заплануйте хоча б одне заняття.</p>}
          <div><Button loading={activationBusy} disabled={data.progress.total_planned === 0} aria-describedby={data.progress.total_planned === 0 ? "activation-hint" : undefined} onClick={() => void activate()}>Активувати програму</Button></div>
        </Card>}
        {!data.is_archived && data.status !== "active" && <Card className="grid gap-space-3 p-space-4 sm:p-space-6">
          <div><h2 className="m-0 text-title-small">Архівація</h2><p className="mb-0 mt-space-1 text-small text-muted-foreground">Архівна програма залишається доступною лише для перегляду.</p></div>
          {!archiveConfirm ? <div><Button variant="outlined" onClick={() => { setArchiveError(""); setArchiveConfirm(true); }}>Архівувати програму</Button></div> : <div ref={archiveConfirmRef} className="grid gap-space-3 rounded-field border border-status-warning/30 bg-status-warning/10 p-space-3" role="group" aria-labelledby="archive-title">
            <h3 id="archive-title" className="m-0 text-base font-bold">Архівувати цю програму?</h3>
            <div className="flex flex-wrap gap-space-2"><Button loading={archiveBusy} onClick={() => void archive()}>Так, архівувати</Button><Button variant="outlined" disabled={archiveBusy} onClick={() => setArchiveConfirm(false)}>Не архівувати</Button></div>
          </div>}
        </Card>}
        {exercises.status === "error" && <Alert tone="warning">Назви вправ не завантажились: {errorMessage(exercises.error)}</Alert>}
        <ol className="m-0 grid list-none gap-space-4 p-0">
          {data.workouts.map((workout) => (
            <li key={workout.entry_id}>
              <Card className="grid gap-space-3 p-space-4 sm:p-space-6">
                <div className="flex flex-wrap items-center justify-between gap-space-3">
                  <div className="flex items-center gap-space-3">
                    <span className="grid size-8 shrink-0 place-items-center rounded-full bg-muted text-small font-bold">{workout.position}</span>
                    <h2 className="m-0 text-title-small font-bold">{workout.name}</h2>
                    <Badge tone="accent">{label(categoryLabels, workout.category)}</Badge>
                  </div>
                  {editable && <div className="flex flex-wrap gap-space-2"><Button variant="outlined" size="sm" aria-expanded={schedulingEntry === workout.entry_id} onClick={() => setSchedulingEntry(schedulingEntry === workout.entry_id ? null : workout.entry_id)}>Запланувати</Button><Link className={buttonVariants({ variant: "outlined", size: "sm" })} to={`/programs/${data.id}/workouts/${workout.entry_id}`}>Змінити склад</Link></div>}
                </div>
                {schedulingEntry === workout.entry_id && <div className="rounded-field border border-outline bg-muted p-space-3"><ScheduleForm source={{ user_program_workout_id: workout.entry_id }} onCreated={() => program.reload()} onClose={() => setSchedulingEntry(null)} /></div>}
                <ol className="m-0 grid list-none gap-space-1 p-0 text-small">
                  {workout.exercises.map((item) => (
                    <li key={item.position} className="flex justify-between gap-space-3 border-b border-outline py-space-2 last:border-0">
                      <span>{item.position}. {names.get(item.exercise_id) ?? `Вправа #${item.exercise_id}`}</span>
                      <span className="text-muted-foreground tabular-nums">{describeParameters(item)}</span>
                    </li>
                  ))}
                </ol>
              </Card>
            </li>
          ))}
        </ol>
      </div>
    </>
  );
}
