import { useState, type FormEvent } from "react";
import { Link, useNavigate, useParams } from "react-router";

import { PageHeader } from "@/components/layout";
import { Alert, Badge, Button, Card, LoadingState, Select, TextInput, buttonVariants } from "@/components/ui";
import type { Exercise } from "@/features/catalog/api";
import { fetchAllExercises } from "@/features/catalog/exerciseIndex";
import { errorMessage, isApiError } from "@/lib/errors";
import { decimalInput } from "@/lib/format";
import { categoryLabels, label } from "@/lib/labels";
import { useResource } from "@/lib/useResource";
import { getProgram, replaceComposition, type CompositionItem, type ProgramWorkout } from "./api";
import { isProgramEditable } from "./ProgramDetailPage";

type Row = { key: number; exerciseId: string; sets: string; reps: string; load: string; duration: string; distance: string };

let rowKey = 0;
const nextKey = () => (rowKey += 1);

/** "15.00" → "15", "4.500" → "4.5": API decimals shown without trailing zeros. */

function toRow(item: ProgramWorkout["exercises"][number]): Row {
  return {
    key: nextKey(),
    exerciseId: String(item.exercise_id),
    sets: item.recommended_sets?.toString() ?? "",
    reps: item.recommended_reps?.toString() ?? "",
    load: decimalInput(item.recommended_load_kg),
    duration: decimalInput(item.recommended_duration_min),
    distance: decimalInput(item.recommended_distance_km),
  };
}

const blank = (value: string) => (value.trim() === "" ? null : value.trim());
const integer = (value: string) => (value.trim() === "" ? null : Number(value));

/** Only parameters that apply to the workout category and exercise are sent (BR-002/BR-004). */
function toItem(row: Row, position: number, category: string, exerciseById: Map<number, Exercise>): CompositionItem {
  const tracksDistance = exerciseById.get(Number(row.exerciseId))?.tracks_distance === true;
  return {
    position,
    exercise_id: Number(row.exerciseId),
    recommended_sets: category === "strength" ? integer(row.sets) : null,
    recommended_reps: category === "strength" ? integer(row.reps) : null,
    recommended_load_kg: category === "strength" ? blank(row.load) : null,
    recommended_duration_min: category === "strength" ? null : blank(row.duration),
    recommended_distance_km: category === "cardio" && tracksDistance ? blank(row.distance) : null,
  };
}

function CompositionForm({ programId, workout, exercises }: { programId: number; workout: ProgramWorkout; exercises: Exercise[] }) {
  const navigate = useNavigate();
  const [name, setName] = useState(workout.name);
  const [rows, setRows] = useState<Row[]>(() => workout.exercises.map(toRow));
  const [errors, setErrors] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);
  const category = workout.category;
  const known = new Set(exercises.map((exercise) => String(exercise.id)));
  const exerciseById = new Map(exercises.map((exercise) => [exercise.id, exercise]));

  function change(key: number, patch: Partial<Row>) {
    setRows((previous) => previous.map((row) => (row.key === key ? { ...row, ...patch } : row)));
  }
  function move(index: number, delta: number) {
    setRows((previous) => {
      const next = [...previous];
      const [row] = next.splice(index, 1);
      next.splice(index + delta, 0, row);
      return next;
    });
  }
  function add() {
    const first = exercises[0];
    if (!first) return;
    setRows((previous) => [...previous, { key: nextKey(), exerciseId: String(first.id), sets: "3", reps: "10", load: "", duration: category === "strength" ? "" : "10", distance: "" }]);
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const local: string[] = [];
    if (!name.trim()) local.push("Назва тренування не може бути порожньою.");
    if (!rows.length) local.push("Додайте хоча б одну вправу.");
    setErrors(local);
    if (local.length) return;
    setBusy(true);
    try {
      await replaceComposition(programId, workout.entry_id, name.trim(), rows.map((row, index) => toItem(row, index + 1, category, exerciseById)));
      navigate(`/programs/${programId}`, { state: { message: `Склад тренування «${name.trim()}» збережено.` } });
    } catch (reason) {
      if (isApiError(reason, 409)) {
        setErrors(["Програма завершена або в архіві — склад змінити не можна."]);
      } else {
        const fields = reason && typeof reason === "object" && "fields" in reason ? (reason.fields as Record<string, string[]>) : {};
        const details = Object.entries(fields).map(([field, messages]) => {
          const match = /^exercises\[(\d+)\]/.exec(field);
          return match ? `Вправа ${Number(match[1]) + 1}: ${messages.join(" ")}` : messages.join(" ");
        });
        setErrors([errorMessage(reason), ...details]);
      }
    } finally {
      setBusy(false);
    }
  }

  const options = exercises.map((exercise) => ({ value: String(exercise.id), label: exercise.name }));
  return (
    <form className="grid gap-space-5" onSubmit={(event) => void submit(event)} noValidate>
      {errors.length > 0 && (
        <Alert tone="error"><ul className="m-0 grid gap-space-1 pl-space-4">{errors.map((text) => <li key={text}>{text}</li>)}</ul></Alert>
      )}
      <TextInput id="workout-name" label="Назва тренування" value={name} maxLength={160} onChange={(event) => setName(event.target.value)} />
      <ol className="m-0 grid list-none gap-space-3 p-0">
        {rows.map((row, index) => {
          const tracksDistance = category === "cardio" && exerciseById.get(Number(row.exerciseId))?.tracks_distance === true;
          return <li key={row.key}>
            <Card className="grid gap-space-3 p-space-4">
              <div className="flex items-center justify-between gap-space-2">
                <span className="text-small font-bold">Вправа {index + 1}</span>
                <div className="flex gap-space-1">
                  <Button variant="outlined" size="sm" disabled={index === 0} onClick={() => move(index, -1)} aria-label={`Підняти вправу ${index + 1}`}>↑</Button>
                  <Button variant="outlined" size="sm" disabled={index === rows.length - 1} onClick={() => move(index, 1)} aria-label={`Опустити вправу ${index + 1}`}>↓</Button>
                  <Button variant="danger" size="sm" disabled={rows.length === 1} onClick={() => setRows((previous) => previous.filter((item) => item.key !== row.key))} aria-label={`Видалити вправу ${index + 1}`}>Видалити</Button>
                </div>
              </div>
              <div className="grid gap-space-3 sm:grid-cols-2 lg:grid-cols-4">
                <div className="sm:col-span-2 lg:col-span-1">
                  <Select id={`exercise-${row.key}`} label="Вправа" value={row.exerciseId} onChange={(event) => {
                    const exerciseId = event.target.value;
                    const keepsDistance = exerciseById.get(Number(exerciseId))?.tracks_distance === true;
                    change(row.key, { exerciseId, ...(keepsDistance ? {} : { distance: "" }) });
                  }}
                    options={known.has(row.exerciseId) ? options : [{ value: row.exerciseId, label: `Вправа #${row.exerciseId} (недоступна)` }, ...options]} />
                </div>
                {category === "strength" && <>
                  <TextInput id={`sets-${row.key}`} label="Підходи" type="number" min="1" step="1" value={row.sets} onChange={(event) => change(row.key, { sets: event.target.value })} />
                  <TextInput id={`reps-${row.key}`} label="Повторення" type="number" min="1" step="1" value={row.reps} onChange={(event) => change(row.key, { reps: event.target.value })} />
                  <TextInput id={`load-${row.key}`} label="Вага, кг (необов’язково)" type="number" min="0" step="0.5" value={row.load} onChange={(event) => change(row.key, { load: event.target.value })} />
                </>}
                {category !== "strength" && (
                  <TextInput id={`duration-${row.key}`} label={category === "cardio" && tracksDistance ? "Тривалість, хв" : "Тривалість, хв (обов’язково)"} type="number" min="0" step="0.5" value={row.duration} onChange={(event) => change(row.key, { duration: event.target.value })} />
                )}
                {tracksDistance && (
                  <TextInput id={`distance-${row.key}`} label="Дистанція, км" type="number" min="0" step="0.1" value={row.distance} onChange={(event) => change(row.key, { distance: event.target.value })} hint="Потрібна тривалість або дистанція." />
                )}
              </div>
            </Card>
          </li>;
        })}
      </ol>
      <div className="flex flex-wrap gap-space-2">
        <Button variant="outlined" onClick={add} disabled={!exercises.length}>Додати вправу</Button>
        <Button type="submit" loading={busy}>Зберегти склад</Button>
        <Link className={buttonVariants({ variant: "outlined", size: "md" })} to={`/programs/${programId}`}>Скасувати</Link>
      </div>
    </form>
  );
}

export function CompositionEditorPage() {
  const params = useParams();
  const programId = Number(params.id);
  const entryId = Number(params.entryId);
  const program = useResource(() => getProgram(programId), [programId]);
  const workout = program.data?.workouts.find((item) => item.entry_id === entryId);
  const back = <Link className={buttonVariants({ variant: "outlined", size: "sm" })} to={`/programs/${programId}`}>До програми</Link>;

  if (program.status === "error") return <div className="grid gap-space-3"><Alert tone="error">{isApiError(program.error, 404) ? "Програму не знайдено." : errorMessage(program.error)}</Alert><div>{back}</div></div>;
  if (!program.data) return <LoadingState text="Завантажуємо програму…" />;
  if (!workout) return <div className="grid gap-space-3"><Alert tone="error">Тренування в цій програмі не знайдено.</Alert><div>{back}</div></div>;
  if (!isProgramEditable(program.data)) return <div className="grid gap-space-3"><Alert tone="info">Завершену або архівну програму змінювати не можна.</Alert><div>{back}</div></div>;

  return (
    <>
      <PageHeader title="Склад тренування" eyebrow={program.data.name} description="Зміни стосуються лише вашої копії; спільний каталог не змінюється.">{back}</PageHeader>
      <div className="mb-space-4 flex items-center gap-space-2"><Badge tone="accent">{label(categoryLabels, workout.category)}</Badge><span className="text-small text-muted-foreground">доступні вправи лише цієї категорії</span></div>
      <EditorBody key={workout.entry_id} programId={programId} workout={workout} />
    </>
  );
}

/** Mounted only once the workout is known, so the picker never starts empty. */
function EditorBody({ programId, workout }: { programId: number; workout: ProgramWorkout }) {
  const exercises = useResource(() => fetchAllExercises(workout.category), [workout.category]);
  if (exercises.status === "error") return <Alert tone="error">{errorMessage(exercises.error)}</Alert>;
  if (exercises.status === "loading") return <LoadingState text="Завантажуємо вправи…" />;
  return <CompositionForm programId={programId} workout={workout} exercises={exercises.data} />;
}
