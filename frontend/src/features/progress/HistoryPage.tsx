import { Link, useSearchParams } from "react-router";
import { PageHeader } from "@/components/layout";
import { Alert, Card, EmptyState, LoadingState, Pagination, buttonVariants } from "@/components/ui";
import { errorMessage } from "@/lib/errors";
import { formatDateTime, formatDecimal, plural, POINT_WORDS } from "@/lib/format";
import { useResource } from "@/lib/useResource";
import { listCompletedSessions } from "./api";
import { PeriodPicker } from "./PeriodPicker";
import { usePeriod } from "./usePeriod";
const PAGE_SIZE = 20;
export function HistoryPage() {
  const { preset, period, change } = usePeriod("month");
  const [params, setParams] = useSearchParams();
  const page = Math.max(1, Number(params.get("page")) || 1);
  const data = useResource(
    () => listCompletedSessions(period.startDate, period.endDate, page, PAGE_SIZE),
    [period.startDate, period.endDate, page],
  );
  const setPage = (next: number) => {
    const q = new URLSearchParams(params);
    q.set("page", String(next));
    setParams(q);
  };
  return (
    <>
      <PageHeader
        title="Історія тренувань"
        eyebrow="Прогрес"
        description="Ваші завершені тренування та їхні результати."
      />
      <Card className="mb-space-4 p-space-4">
        <PeriodPicker preset={preset} period={period} onChange={change} />
      </Card>
      <div aria-live="polite" className="grid gap-space-3">
        {data.status === "loading" && !data.data && <LoadingState text="Завантажуємо історію…" />}
        {data.status === "error" && <Alert tone="error">{errorMessage(data.error)}</Alert>}
        {data.data?.results.length === 0 && <EmptyState title="За цей період тренувань немає" />}
        {data.data?.results.map((item) => (
          <Card key={item.id} className="grid gap-space-2 p-space-4 sm:grid-cols-[1fr_auto]">
            <div>
              <h2 className="m-0 text-title-small">{item.performed_workout_name_snapshot}</h2>
              <p className="my-space-1 text-small text-muted-foreground">
                {formatDateTime(item.completed_at)} · {formatDecimal(item.duration_min, "хв")} · +
                {plural(item.workout_points, POINT_WORDS)}
              </p>
              <p className="m-0 text-small">
                {item.estimated_calories === null
                  ? "Калорії не розраховано"
                  : formatDecimal(item.estimated_calories, "ккал")}
              </p>
            </div>
            <Link className={buttonVariants({ variant: "outlined", size: "sm" })} to={`/history/${item.id}`}>
              Деталі
            </Link>
          </Card>
        ))}
        {data.data && <Pagination page={page} pageSize={PAGE_SIZE} count={data.data.count} onPage={setPage} />}
      </div>
    </>
  );
}
