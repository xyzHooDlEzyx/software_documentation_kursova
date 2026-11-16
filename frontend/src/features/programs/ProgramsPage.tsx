import { Link, useSearchParams } from "react-router";

import { PageHeader } from "@/components/layout";
import { Alert, Badge, Card, EmptyState, LoadingState, Pagination, buttonVariants } from "@/components/ui";
import { errorMessage } from "@/lib/errors";
import { formatDecimal } from "@/lib/format";
import { label, programStatusLabels } from "@/lib/labels";
import { useResource } from "@/lib/useResource";
import { cn } from "@/lib/utils";
import { listPrograms } from "./api";

const FILTERS = [
  { value: "", text: "Усі" },
  { value: "draft", text: "Чернетки" },
  { value: "active", text: "Активні" },
  { value: "completed", text: "Завершені" },
];

export function ProgramsPage() {
  const [params, setParams] = useSearchParams();
  const status = params.get("status") ?? "";
  const archived = params.get("archived") === "true";
  const page = Math.max(1, Number(params.get("page")) || 1);
  const programs = useResource(
    () => listPrograms({ status: status || undefined, archived, page }),
    [status, archived, page],
  );

  function update(changes: Record<string, string>) {
    const next = new URLSearchParams(params);
    for (const [key, value] of Object.entries(changes)) {
      if (value) next.set(key, value);
      else next.delete(key);
    }
    if (!("page" in changes)) next.delete("page");
    setParams(next, { replace: true });
  }

  return (
    <>
      <PageHeader
        title="Мої програми"
        eyebrow="Програми"
        description="Персональні копії шаблонів: їх можна перейменовувати й змінювати склад тренувань."
      >
        <Link className={buttonVariants({ variant: "primary", size: "md" })} to="/programs/recommendation">
          Підібрати програму
        </Link>
      </PageHeader>
      <div className="grid gap-space-5">
        <div className="flex flex-wrap gap-space-2" role="group" aria-label="Фільтр програм">
          {FILTERS.map((filter) => (
            <button
              key={filter.value}
              type="button"
              aria-pressed={status === filter.value && !archived}
              onClick={() => update({ status: filter.value, archived: "" })}
              className={cn(
                "min-h-9 rounded-chip border px-space-3 text-small font-semibold",
                status === filter.value && !archived
                  ? "border-primary bg-primary text-primary-foreground"
                  : "border-input-border bg-card hover:bg-interactive-hover-state",
              )}
            >
              {filter.text}
            </button>
          ))}
          <button
            type="button"
            aria-pressed={archived}
            onClick={() => update({ archived: archived ? "" : "true", status: "" })}
            className={cn(
              "min-h-9 rounded-chip border px-space-3 text-small font-semibold",
              archived
                ? "border-primary bg-primary text-primary-foreground"
                : "border-input-border bg-card hover:bg-interactive-hover-state",
            )}
          >
            Архів
          </button>
        </div>
        {programs.status === "error" && <Alert tone="error">{errorMessage(programs.error)}</Alert>}
        {!programs.data && programs.status === "loading" && <LoadingState text="Завантажуємо програми…" />}
        {programs.data && programs.data.results.length === 0 && (
          <EmptyState title={status || archived ? "Програм із таким фільтром немає" : "У вас ще немає програм"}>
            {!status && !archived && (
              <>Почніть із рекомендації: система підбере шаблон за вашою ціллю, рівнем і частотою тренувань.</>
            )}
          </EmptyState>
        )}
        {programs.data && programs.data.results.length > 0 && (
          <>
            <ul className="m-0 grid list-none gap-space-4 p-0 sm:grid-cols-2">
              {programs.data.results.map((program) => (
                <li key={program.id}>
                  <Link
                    to={`/programs/${program.id}`}
                    className="block h-full rounded-panel no-underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                  >
                    <Card className="grid h-full gap-space-3 transition-shadow hover:shadow-panel-hover">
                      <div className="flex flex-wrap items-center gap-space-2">
                        <Badge tone={program.status === "active" ? "brand" : "neutral"}>
                          {label(programStatusLabels, program.status)}
                        </Badge>
                        {program.is_archived && <Badge tone="outline">В архіві</Badge>}
                      </div>
                      <h2 className="m-0 text-title-small font-bold text-foreground">{program.name}</h2>
                      <div className="grid gap-space-1">
                        <div className="h-2 overflow-hidden rounded-chip bg-muted" aria-hidden="true">
                          <div
                            className="h-full bg-accent"
                            style={{ width: `${Math.min(100, Number(program.progress_percent))}%` }}
                          />
                        </div>
                        <span className="text-caption text-muted-foreground">
                          Прогрес: {formatDecimal(program.progress_percent)}%
                        </span>
                      </div>
                    </Card>
                  </Link>
                </li>
              ))}
            </ul>
            <Pagination
              page={page}
              pageSize={20}
              count={programs.data.count}
              onPage={(next) => update({ page: String(next) })}
            />
          </>
        )}
      </div>
    </>
  );
}
