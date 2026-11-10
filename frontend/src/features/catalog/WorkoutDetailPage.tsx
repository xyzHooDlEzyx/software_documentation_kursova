import { Link, useParams } from "react-router";

import { PageHeader } from "@/components/layout";
import { Alert, Badge, Card, LoadingState, buttonVariants } from "@/components/ui";
import { errorMessage, isApiError } from "@/lib/errors";
import { EXERCISE_WORDS, plural } from "@/lib/format";
import { categoryLabels, label } from "@/lib/labels";
import { useResource } from "@/lib/useResource";
import { getWorkout } from "./api";
import { describeParameters } from "./parameters";

export function WorkoutDetailPage() {
  const id = Number(useParams().id);
  const workout = useResource(() => getWorkout(id), [id]);
  const back = <Link className={buttonVariants({ variant: "outlined", size: "sm" })} to="/catalog">До каталогу</Link>;

  if (workout.status === "loading") return <LoadingState text="Завантажуємо тренування…" />;
  if (workout.status === "error") {
    const text = isApiError(workout.error, 404) ? "Тренування не знайдено або воно більше не доступне." : errorMessage(workout.error);
    return <div className="grid gap-space-3"><Alert tone="error">{text}</Alert><div>{back}</div></div>;
  }

  const data = workout.data;
  return (
    <>
      <PageHeader title={data.name} eyebrow="Тренування" description={data.description || undefined}>{back}</PageHeader>
      <Card className="grid gap-space-4 p-space-4 sm:p-space-6">
        <div className="flex items-center gap-space-2">
          <Badge tone="accent">{label(categoryLabels, data.category)}</Badge>
          <span className="text-small text-muted-foreground">{plural(data.exercises.length, EXERCISE_WORDS)} у порядку виконання</span>
        </div>
        <ol className="m-0 grid list-none gap-space-2 p-0">
          {data.exercises.map((item) => (
            <li key={item.entry_id} className="flex items-center gap-space-3 rounded-field border border-outline px-space-4 py-space-3">
              <span className="grid size-8 shrink-0 place-items-center rounded-full bg-muted text-small font-bold">{item.position}</span>
              <span className="min-w-0 flex-1 font-semibold">{item.exercise.name}</span>
              <span className="text-small text-muted-foreground tabular-nums">{describeParameters(item)}</span>
            </li>
          ))}
        </ol>
      </Card>
    </>
  );
}
