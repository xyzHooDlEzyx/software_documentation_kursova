import { useSearchParams } from "react-router";
import { PageHeader } from "@/components/layout";
import { Alert, Card, EmptyState, LoadingState, Pagination } from "@/components/ui";
import { errorMessage } from "@/lib/errors";
import { formatDateTime } from "@/lib/format";
import { useResource } from "@/lib/useResource";
import { getAllTimePointsSummary, getPointsSummary, listPointTransactions } from "./api";
import { PeriodPicker } from "./PeriodPicker";
import { usePeriod } from "./usePeriod";

const PAGE_SIZE = 20;
const labels = { workout_completion: "тренування", program_completion: "бонус за програму" } as const;

export function PointsPage() {
  const { preset, period, change } = usePeriod("month");
  const [params, setParams] = useSearchParams();
  const page = Math.max(1, Number(params.get("page")) || 1);
  const resource = useResource(async () => {
    const [allTime, summary, transactions] = await Promise.all([
      getAllTimePointsSummary(),
      getPointsSummary(period.startDate, period.endDate),
      listPointTransactions(period.startDate, period.endDate, page, PAGE_SIZE),
    ]);
    return { allTime, summary, transactions };
  }, [period.startDate, period.endDate, page]);
  const setPage = (next: number) => {
    const query = new URLSearchParams(params);
    query.set("page", String(next));
    setParams(query);
  };
  return (
    <>
      <PageHeader
        title="Мої бали"
        eyebrow="Прогрес"
        description="Усі нарахування балів за тренування та бонуси програм."
      />
      <Card className="mb-space-4 p-space-4">
        <PeriodPicker preset={preset} period={period} onChange={change} />
      </Card>
      <div aria-live="polite" className="grid gap-space-4">
        {resource.status === "loading" && !resource.data && <LoadingState text="Завантажуємо бали…" />}
        {resource.status === "error" && <Alert tone="error">{errorMessage(resource.error)}</Alert>}
        {resource.data && (
          <>
            <div className="grid gap-space-3 sm:grid-cols-2 xl:grid-cols-4">
              <Card className="p-space-4">
                <span>Усього балів</span>
                <strong className="block text-title-large">{resource.data.allTime.total_points}</strong>
              </Card>
              <Card className="p-space-4">
                <span>За період</span>
                <strong className="block text-title-large">{resource.data.summary.total_points}</strong>
              </Card>
              <Card className="p-space-4">
                <span>За тренування</span>
                <strong className="block text-title-large">{resource.data.summary.workout_points}</strong>
              </Card>
              <Card className="p-space-4">
                <span>Бонуси програм</span>
                <strong className="block text-title-large">{resource.data.summary.program_bonus_points}</strong>
              </Card>
            </div>
            {resource.data.transactions.results.length === 0 ? (
              <EmptyState title="Нарахувань за цей період немає" />
            ) : (
              <div className="grid gap-space-2">
                {resource.data.transactions.results.map((item) => (
                  <Card key={item.id} className="flex items-center justify-between gap-space-3 p-space-4">
                    <div>
                      <strong className="capitalize">{labels[item.point_kind]}</strong>
                      <span className="block text-small text-muted-foreground">{formatDateTime(item.awarded_at)}</span>
                    </div>
                    <strong>+{item.points}</strong>
                  </Card>
                ))}
                <Pagination
                  page={page}
                  pageSize={PAGE_SIZE}
                  count={resource.data.transactions.count}
                  onPage={setPage}
                />
              </div>
            )}
          </>
        )}
      </div>
    </>
  );
}
