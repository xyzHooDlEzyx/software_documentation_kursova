import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router";

import { PageHeader } from "@/components/layout";
import { Alert, Badge, Card, EmptyState, LoadingState, Pagination, TextInput } from "@/components/ui";
import { errorMessage } from "@/lib/errors";
import { categoryLabels, label } from "@/lib/labels";
import { EXERCISE_WORDS, formatDecimal, plural } from "@/lib/format";
import { useResource } from "@/lib/useResource";
import { cn } from "@/lib/utils";
import { listCategories, listExercises, listWorkouts } from "./api";

const PAGE_SIZE = 12;
type View = "workouts" | "exercises";

function Chip({ active, onClick, children }: { active: boolean; onClick: () => void; children: string }) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={active}
      className={cn("min-h-9 rounded-chip border px-space-3 text-small font-semibold transition-colors", active ? "border-primary bg-primary text-primary-foreground" : "border-input-border bg-card text-foreground hover:bg-interactive-hover-state")}
    >
      {children}
    </button>
  );
}

function WorkoutList({ category, search, page, onPage }: { category: string; search: string; page: number; onPage: (page: number) => void }) {
  const workouts = useResource(() => listWorkouts({ category, search, page, pageSize: PAGE_SIZE }), [category, search, page]);
  if (workouts.status === "error") return <Alert tone="error">{errorMessage(workouts.error)}</Alert>;
  if (!workouts.data) return <LoadingState text="Завантажуємо тренування…" />;
  if (!workouts.data.results.length) return <EmptyState title="Тренувань не знайдено">Змініть категорію або пошуковий запит.</EmptyState>;
  return (
    <div className="grid gap-space-4">
      <ul className="m-0 grid list-none gap-space-4 p-0 sm:grid-cols-2 xl:grid-cols-3">
        {workouts.data.results.map((workout) => (
          <li key={workout.id}>
            <Link to={`/catalog/workouts/${workout.id}`} className="block h-full rounded-panel no-underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
              <Card className="grid h-full gap-space-2 transition-shadow hover:shadow-panel-hover">
                <div className="flex items-center justify-between gap-space-2">
                  <Badge tone="accent">{label(categoryLabels, workout.category)}</Badge>
                  <span className="text-caption text-muted-foreground">{plural(workout.exercise_count, EXERCISE_WORDS)}</span>
                </div>
                <h2 className="m-0 text-title-small font-bold text-foreground">{workout.name}</h2>
                {workout.description && <p className="m-0 text-small text-muted-foreground">{workout.description}</p>}
              </Card>
            </Link>
          </li>
        ))}
      </ul>
      <Pagination page={page} pageSize={PAGE_SIZE} count={workouts.data.count} onPage={onPage} />
    </div>
  );
}

function ExerciseList({ category, search, page, onPage }: { category: string; search: string; page: number; onPage: (page: number) => void }) {
  const exercises = useResource(() => listExercises({ category, search, page, pageSize: PAGE_SIZE }), [category, search, page]);
  if (exercises.status === "error") return <Alert tone="error">{errorMessage(exercises.error)}</Alert>;
  if (!exercises.data) return <LoadingState text="Завантажуємо вправи…" />;
  if (!exercises.data.results.length) return <EmptyState title="Вправ не знайдено">Змініть категорію або пошуковий запит.</EmptyState>;
  return (
    <div className="grid gap-space-4">
      <ul className="m-0 grid list-none gap-space-4 p-0 sm:grid-cols-2 xl:grid-cols-3">
        {exercises.data.results.map((exercise) => (
          <li key={exercise.id}>
            <Card className="grid h-full gap-space-2">
              <div className="flex flex-wrap gap-space-2">
                <Badge tone="accent">{label(categoryLabels, exercise.category)}</Badge>
                {exercise.category === "cardio" && <Badge tone="outline">{exercise.tracks_distance ? "з дистанцією" : "лише тривалість"}</Badge>}
              </div>
              <h2 className="m-0 text-title-small font-bold text-foreground">{exercise.name}</h2>
              {exercise.description && <p className="m-0 text-small text-muted-foreground">{exercise.description}</p>}
              {exercise.met_value && (
                <p className="m-0 text-caption text-muted-foreground" title={exercise.met_activity_description ?? undefined}>
                  MET {formatDecimal(exercise.met_value)} · код {exercise.met_activity_code} ({exercise.met_reference_version})
                </p>
              )}
            </Card>
          </li>
        ))}
      </ul>
      <Pagination page={page} pageSize={PAGE_SIZE} count={exercises.data.count} onPage={onPage} />
    </div>
  );
}

export function CatalogPage() {
  const [params, setParams] = useSearchParams();
  const view: View = params.get("view") === "exercises" ? "exercises" : "workouts";
  const category = params.get("category") ?? "";
  const search = params.get("search") ?? "";
  const page = Math.max(1, Number(params.get("page")) || 1);
  const [searchText, setSearchText] = useState(search);
  const categories = useResource(listCategories, []);

  function update(changes: Record<string, string>) {
    const next = new URLSearchParams(params);
    for (const [key, value] of Object.entries(changes)) {
      if (value) next.set(key, value); else next.delete(key);
    }
    if (!("page" in changes)) next.delete("page");
    setParams(next, { replace: true });
  }

  // Debounce typing so every keystroke does not hit the API.
  useEffect(() => {
    if (searchText.trim() === search) return;
    const timer = window.setTimeout(() => update({ search: searchText.trim() }), 300);
    return () => window.clearTimeout(timer);
  });

  return (
    <>
      <PageHeader title="Бібліотека тренувань" eyebrow="Каталог" description="Кардіо, силові та йога: готові тренування і окремі вправи з довідковими значеннями MET." />
      <div className="grid gap-space-5">
        <div className="flex flex-wrap gap-space-2" role="group" aria-label="Розділ каталогу">
          <Chip active={view === "workouts"} onClick={() => update({ view: "" })}>Тренування</Chip>
          <Chip active={view === "exercises"} onClick={() => update({ view: "exercises" })}>Вправи</Chip>
        </div>
        <div className="grid gap-space-3 md:grid-cols-[1fr_auto] md:items-end">
          <TextInput id="catalog-search" label="Пошук за назвою" type="search" value={searchText} maxLength={160} onChange={(event) => setSearchText(event.target.value)} />
          <div className="flex flex-wrap gap-space-2" role="group" aria-label="Категорія">
            <Chip active={!category} onClick={() => update({ category: "" })}>Усі</Chip>
            {(categories.data?.results ?? []).map((item) => (
              <Chip key={item.code} active={category === item.code} onClick={() => update({ category: item.code })}>{label(categoryLabels, item.code)}</Chip>
            ))}
          </div>
        </div>
        {categories.status === "error" && <Alert tone="warning">Не вдалося завантажити категорії: {errorMessage(categories.error)}</Alert>}
        {view === "workouts"
          ? <WorkoutList category={category} search={search} page={page} onPage={(next) => update({ page: String(next) })} />
          : <ExerciseList category={category} search={search} page={page} onPage={(next) => update({ page: String(next) })} />}
      </div>
    </>
  );
}
