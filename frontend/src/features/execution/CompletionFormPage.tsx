import { useEffect, useMemo, useRef, useState, type FormEvent } from "react";
import { Link, useLocation, useNavigate, useParams } from "react-router";

import { PageHeader } from "@/components/layout";
import { Alert, Button, Card, Checkbox, LoadingState, TextInput, buttonVariants } from "@/components/ui";
import { getWorkout, type RecommendedParameters } from "@/features/catalog/api";
import { fetchAllExercises } from "@/features/catalog/exerciseIndex";
import { getProgram, getProgramProgress } from "@/features/programs/api";
import { getSession } from "@/features/schedule/api";
import { clearSessionNameCache } from "@/features/schedule/names";
import { errorMessage, isApiError } from "@/lib/errors";
import { decimalInput } from "@/lib/format";
import { useResource } from "@/lib/useResource";
import { completeWorkout, type CompletionInput, type CompletionResultInput } from "./api";

type SourceExercise = RecommendedParameters & {
  position: number;
  exerciseId: number;
  name: string;
  category: string;
  tracksDistance: boolean;
};

type CompletionSource = {
  title: string;
  scheduledSessionId: number | null;
  sourceWorkoutId: number | null;
  userProgramId: number | null;
  exercises: SourceExercise[];
};

type RowState = {
  performed: boolean;
  sets: string;
  reps: string;
  load: string;
  duration: string;
  distance: string;
};

function fixedDecimal(value: string, digits: number) {
  return Number(value).toFixed(digits);
}

async function loadSource(kind: "session" | "workout", id: number): Promise<CompletionSource> {
  if (kind === "workout") {
    const workout = await getWorkout(id);
    return {
      title: workout.name,
      scheduledSessionId: null,
      sourceWorkoutId: workout.id,
      userProgramId: null,
      exercises: workout.exercises.map((item) => ({
        ...item,
        exerciseId: item.exercise.id,
        name: item.exercise.name,
        category: item.exercise.category,
        tracksDistance: item.exercise.tracks_distance,
      })),
    };
  }

  const session = await getSession(id);
  if (session.user_program_id && session.user_program_workout_id) {
    const [program, exercises] = await Promise.all([getProgram(session.user_program_id), fetchAllExercises()]);
    const entry = program.workouts.find((item) => item.entry_id === session.user_program_workout_id);
    if (!entry) throw new Error("program_composition_missing");
    const exerciseMap = new Map(exercises.map((item) => [item.id, item]));
    return {
      title: entry.name,
      scheduledSessionId: session.id,
      sourceWorkoutId: null,
      userProgramId: program.id,
      exercises: entry.exercises.map((item) => {
        const exercise = exerciseMap.get(item.exercise_id);
        return {
          ...item,
          exerciseId: item.exercise_id,
          name: exercise?.name ?? `Вправа #${item.exercise_id}`,
          category: exercise?.category ?? entry.category,
          tracksDistance: exercise?.tracks_distance ?? false,
        };
      }),
    };
  }
  const workout = await getWorkout(session.source_workout_id);
  return {
    title: workout.name,
    scheduledSessionId: session.id,
    sourceWorkoutId: null,
    userProgramId: null,
    exercises: workout.exercises.map((item) => ({
      ...item,
      exerciseId: item.exercise.id,
      name: item.exercise.name,
      category: item.exercise.category,
      tracksDistance: item.exercise.tracks_distance,
    })),
  };
}

function initialRow(exercise: SourceExercise): RowState {
  return {
    performed: true,
    sets: exercise.recommended_sets?.toString() ?? "",
    reps: exercise.recommended_reps?.toString() ?? "",
    load: decimalInput(exercise.recommended_load_kg),
    duration: decimalInput(exercise.recommended_duration_min),
    distance: decimalInput(exercise.recommended_distance_km),
  };
}

export function CompletionFormPage() {
  const id = Number(useParams().id);
  const location = useLocation();
  const navigate = useNavigate();
  const kind = location.pathname.startsWith("/schedule/") ? "session" : "workout";
  const source = useResource(() => loadSource(kind, id), [kind, id]);
  const [rows, setRows] = useState<RowState[]>([]);
  const [duration, setDuration] = useState("");
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [error, setError] = useState("");
  const [profileMissing, setProfileMissing] = useState(false);
  const [busy, setBusy] = useState(false);
  const [attemptBlocked, setAttemptBlocked] = useState(false);
  const headingRef = useRef<HTMLDivElement>(null);
  const storageKey = useMemo(() => `completion-attempt:${kind}:${id}`, [kind, id]);
  const keyRef = useRef("");

  useEffect(() => {
    if (!source.data) return;
    setRows(source.data.exercises.map(initialRow));
  }, [source.data]);

  useEffect(() => {
    keyRef.current = sessionStorage.getItem(storageKey) || crypto.randomUUID();
    sessionStorage.setItem(storageKey, keyRef.current);
    setAttemptBlocked(false);
    setError("");
    setProfileMissing(false);
    headingRef.current?.focus();
  }, [storageKey]);

  function updateRow(index: number, changes: Partial<RowState>) {
    setRows((current) => current.map((row, rowIndex) => (rowIndex === index ? { ...row, ...changes } : row)));
  }

  function buildBody(): { body: CompletionInput; submittedRows: number[] } | null {
    if (!source.data) return null;
    const nextErrors: Record<string, string> = {};
    const total = Number(duration);
    if (!duration || !Number.isFinite(total) || total <= 0 || total > 300)
      nextErrors.duration_min = "Вкажіть тривалість від 0,01 до 300 хвилин.";
    const submittedRows: number[] = [];
    const results: CompletionResultInput[] = [];
    rows.forEach((row, index) => {
      if (!row.performed) return;
      submittedRows.push(index);
      const exercise = source.data!.exercises[index];
      const prefix = `row-${index}-`;
      const positiveInt = (value: string, field: string, text: string) => {
        const number = Number(value);
        if (!value || !Number.isInteger(number) || number <= 0) nextErrors[prefix + field] = text;
        return Number.isInteger(number) && number > 0 ? number : null;
      };
      const positiveDecimal = (value: string, field: string, text: string, allowZero = false) => {
        const number = Number(value);
        if (!value || !Number.isFinite(number) || (allowZero ? number < 0 : number <= 0))
          nextErrors[prefix + field] = text;
        return Number.isFinite(number) && (allowZero ? number >= 0 : number > 0);
      };
      let actualSets: number | null = null;
      let actualReps: number | null = null;
      let actualLoad: string | null = null;
      let actualDuration: string | null = null;
      let actualDistance: string | null = null;
      if (exercise.category === "strength") {
        actualSets = positiveInt(row.sets, "actual_sets", "Вкажіть додатну кількість підходів.");
        actualReps = positiveInt(row.reps, "actual_reps", "Вкажіть додатну кількість повторень.");
        if (row.load) {
          if (positiveDecimal(row.load, "actual_load_kg", "Навантаження не може бути від’ємним.", true))
            actualLoad = fixedDecimal(row.load, 1);
        }
      } else {
        if (positiveDecimal(row.duration, "actual_duration_min", "Вкажіть додатну тривалість."))
          actualDuration = fixedDecimal(row.duration, 2);
        if (exercise.category === "cardio" && exercise.tracksDistance && row.distance) {
          if (positiveDecimal(row.distance, "actual_distance_km", "Дистанція має бути більшою за нуль."))
            actualDistance = fixedDecimal(row.distance, 3);
        }
      }
      results.push({
        position: exercise.position,
        exercise_id: exercise.exerciseId,
        actual_sets: actualSets,
        actual_reps: actualReps,
        actual_load_kg: actualLoad,
        actual_duration_min: actualDuration,
        actual_distance_km: actualDistance,
      });
    });
    if (results.length === 0) nextErrors.results = "Позначте хоча б одну виконану вправу.";
    const segmentDuration = results.reduce((sum, item) => sum + Number(item.actual_duration_min ?? 0), 0);
    if (Number.isFinite(total) && segmentDuration > total)
      nextErrors.duration_min = "Сума тривалості вправ не може перевищувати загальну тривалість.";
    setErrors(nextErrors);
    if (Object.keys(nextErrors).length > 0) return null;
    return {
      body: {
        scheduled_session_id: source.data.scheduledSessionId,
        source_workout_id: source.data.sourceWorkoutId,
        duration_min: fixedDecimal(duration, 2),
        results,
      },
      submittedRows,
    };
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (attemptBlocked) return;
    setError("");
    setProfileMissing(false);
    const built = buildBody();
    if (!built) return;
    setBusy(true);
    try {
      const completion = await completeWorkout(built.body, keyRef.current);
      sessionStorage.removeItem(storageKey);
      if (source.data?.scheduledSessionId !== null) {
        clearSessionNameCache();
        const refreshes: Promise<unknown>[] = [getSession(source.data!.scheduledSessionId!)];
        if (source.data?.userProgramId)
          refreshes.push(getProgram(source.data.userProgramId), getProgramProgress(source.data.userProgramId));
        await Promise.allSettled(refreshes);
      }
      navigate(`/completed/${completion.id}`, { state: { completion } });
    } catch (reason) {
      if (isApiError(reason, 404, "profile_missing")) {
        setProfileMissing(true);
        setError("");
      } else if (
        isApiError(reason, 409, "idempotency_conflict") ||
        (kind === "session" && isApiError(reason, 409, "duplicate_completion"))
      ) {
        sessionStorage.removeItem(storageKey);
        setAttemptBlocked(true);
        setError("");
      } else if (isApiError(reason, 409, "invalid_state")) {
        setError("Неможливо завершити заняття для програми в поточному стані.");
      } else {
        const fieldMap: Record<string, string> = {};
        if (reason && typeof reason === "object" && "fields" in reason) {
          const fields = (reason as { fields: Record<string, string[]> }).fields;
          for (const [field, messages] of Object.entries(fields)) {
            const match = /^results\[(\d+)]\.(.+)$/.exec(field);
            if (match) {
              const original = built.submittedRows[Number(match[1])];
              if (original !== undefined) fieldMap[`row-${original}-${match[2]}`] = messages.join(" ");
            } else fieldMap[field] = messages.join(" ");
          }
        }
        setErrors(fieldMap);
        setError(errorMessage(reason));
      }
    } finally {
      setBusy(false);
    }
  }

  if (source.status === "loading" && !source.data) return <LoadingState text="Готуємо форму завершення…" />;
  if (source.status === "error" && !source.data)
    return (
      <Alert tone="error">
        {isApiError(source.error, 404) ? "Джерело тренування не знайдено." : errorMessage(source.error)}
      </Alert>
    );
  const data = source.data!;
  const backPath = kind === "session" ? `/schedule/${id}` : `/catalog/workouts/${id}`;

  return (
    <>
      <div ref={headingRef} tabIndex={-1} className="outline-none">
        <PageHeader
          title="Завершити тренування"
          eyebrow={data.title}
          description="Внесіть лише фактично виконані вправи."
        >
          <Link className={buttonVariants({ variant: "outlined", size: "sm" })} to={backPath}>
            Назад
          </Link>
        </PageHeader>
      </div>
      <form className="grid gap-space-5" onSubmit={(event) => void submit(event)} noValidate>
        {error && <Alert tone="error">{error}</Alert>}
        {attemptBlocked && (
          <Alert tone="info">
            Це тренування вже збережено раніше (можливо, відповідь не дійшла через мережу).{" "}
            {kind === "session" ? (
              <Link to={`/schedule/${id}`}>Переглянути заняття</Link>
            ) : (
              <>
                Поверніться до <Link to={`/catalog/workouts/${id}`}>тренування</Link> або{" "}
                <Link to="/schedule">розкладу</Link>.
              </>
            )}
          </Alert>
        )}
        {profileMissing && (
          <Alert tone="error">
            Вкажіть вагу в профілі. <Link to="/profile">Перейти до профілю</Link>
          </Alert>
        )}
        {errors.results && <Alert tone="error">{errors.results}</Alert>}
        <Card className="p-space-4 sm:p-space-6">
          <TextInput
            id="completion-duration"
            label="Загальна тривалість, хв"
            type="number"
            inputMode="decimal"
            min="0.01"
            max="300"
            step="0.01"
            value={duration}
            onChange={(event) => setDuration(event.target.value)}
            error={errors.duration_min}
          />
        </Card>
        <div className="grid gap-space-4">
          {data.exercises.map((exercise, index) => {
            const row = rows[index];
            if (!row) return null;
            const prefix = `completion-${index}`;
            return (
              <fieldset
                key={`${exercise.position}-${exercise.exerciseId}`}
                className="min-w-0 rounded-panel border border-input-border bg-card p-space-4 shadow-panel sm:p-space-6"
              >
                <legend className="max-w-full px-space-2 text-title-small font-bold">
                  {exercise.position}. {exercise.name}
                </legend>
                <div className="grid gap-space-4">
                  <Checkbox
                    id={`${prefix}-performed`}
                    label="Виконано"
                    checked={row.performed}
                    onChange={(event) => updateRow(index, { performed: event.target.checked })}
                  />
                  {row.performed && (
                    <div className="grid gap-space-3 sm:grid-cols-2 lg:grid-cols-3">
                      {exercise.category === "strength" && (
                        <>
                          <TextInput
                            id={`${prefix}-sets`}
                            label="Підходи"
                            type="number"
                            min="1"
                            step="1"
                            value={row.sets}
                            onChange={(event) => updateRow(index, { sets: event.target.value })}
                            error={errors[`row-${index}-actual_sets`]}
                          />
                          <TextInput
                            id={`${prefix}-reps`}
                            label="Повторення"
                            type="number"
                            min="1"
                            step="1"
                            value={row.reps}
                            onChange={(event) => updateRow(index, { reps: event.target.value })}
                            error={errors[`row-${index}-actual_reps`]}
                          />
                          <TextInput
                            id={`${prefix}-load`}
                            label="Навантаження, кг"
                            type="number"
                            min="0"
                            step="0.1"
                            value={row.load}
                            onChange={(event) => updateRow(index, { load: event.target.value })}
                            error={errors[`row-${index}-actual_load_kg`]}
                          />
                        </>
                      )}
                      {exercise.category !== "strength" && (
                        <TextInput
                          id={`${prefix}-duration`}
                          label="Тривалість, хв"
                          type="number"
                          min="0.01"
                          max="300"
                          step="0.01"
                          value={row.duration}
                          onChange={(event) => updateRow(index, { duration: event.target.value })}
                          error={errors[`row-${index}-actual_duration_min`]}
                        />
                      )}
                      {exercise.category === "cardio" && exercise.tracksDistance && (
                        <TextInput
                          id={`${prefix}-distance`}
                          label="Дистанція, км"
                          type="number"
                          min="0.001"
                          step="0.001"
                          value={row.distance}
                          onChange={(event) => updateRow(index, { distance: event.target.value })}
                          error={errors[`row-${index}-actual_distance_km`]}
                        />
                      )}
                    </div>
                  )}
                </div>
              </fieldset>
            );
          })}
        </div>
        <div className="flex flex-wrap gap-space-2">
          <Button type="submit" loading={busy} disabled={attemptBlocked}>
            Зберегти результат
          </Button>
          <Link className={buttonVariants({ variant: "outlined", size: "md" })} to={backPath}>
            Скасувати
          </Link>
        </div>
      </form>
    </>
  );
}
