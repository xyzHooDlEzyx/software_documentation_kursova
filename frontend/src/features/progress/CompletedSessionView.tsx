import { Card } from "@/components/ui";
import { formatDateTime, formatDecimal } from "@/lib/format";
import type { CompletedSessionDetail } from "./api";

export function CompletedSessionView({ session }: { session: CompletedSessionDetail }) {
  return (
    <div className="grid gap-space-4" aria-live="polite">
      <Card className="grid gap-space-2 p-space-4 sm:p-space-6">
        <h2 className="m-0 text-title-medium">{session.performed_workout_name_snapshot}</h2>
        <p className="m-0">Джерело: {session.source_workout_name_snapshot}</p>
        <p className="m-0">Завершено: {formatDateTime(session.completed_at)}</p>
        <p className="m-0">Тривалість: {formatDecimal(session.duration_min, "хв")}</p>
        <p className="m-0">Бали: +{session.workout_points}</p>
        <p className="m-0">
          {session.estimated_calories === null
            ? "Калорії не розраховано"
            : `Калорії: ${formatDecimal(session.estimated_calories, "ккал")}`}
        </p>
        {session.program_context && (
          <p className="m-0">
            Програма: {session.program_context.user_program_name_snapshot} ·{" "}
            {session.program_context.source_program_template_name_snapshot}
          </p>
        )}
      </Card>
      <Card className="p-space-4 sm:p-space-6">
        <h2 className="mt-0 text-title-medium">Результати вправ</h2>
        <ol className="m-0 grid gap-space-3 pl-space-5">
          {session.results.map((result) => (
            <li key={result.id}>
              <strong>{result.exercise_name_snapshot}</strong>
              <span className="block text-small text-muted-foreground">
                {[
                  result.actual_sets !== null ? `${result.actual_sets} підходів` : null,
                  result.actual_reps !== null ? `${result.actual_reps} повторень` : null,
                  result.actual_load_kg !== null ? formatDecimal(result.actual_load_kg, "кг") : null,
                  result.actual_duration_min !== null ? formatDecimal(result.actual_duration_min, "хв") : null,
                  result.actual_distance_km !== null ? formatDecimal(result.actual_distance_km, "км") : null,
                ]
                  .filter(Boolean)
                  .join(" · ")}
              </span>
            </li>
          ))}
        </ol>
      </Card>
    </div>
  );
}
