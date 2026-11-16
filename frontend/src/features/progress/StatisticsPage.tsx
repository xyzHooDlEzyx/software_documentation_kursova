import { PageHeader } from "@/components/layout";
import { Alert, Card, LoadingState } from "@/components/ui";
import { WeightLineChart } from "@/components/charts/WeightLineChart";
import { WeeklyActivityChart } from "@/components/charts/WeeklyActivityChart";
import { errorMessage } from "@/lib/errors";
import { formatDecimal } from "@/lib/format";
import { useResource } from "@/lib/useResource";
import { getOverview, getWeightChart } from "./api";
import { PeriodPicker } from "./PeriodPicker";
import { usePeriod } from "./usePeriod";

export function StatisticsPage() {
  const { preset, period, change } = usePeriod("week");
  const resource = useResource(async () => {
    const [overview, weight] = await Promise.all([
      getOverview(period.startDate, period.endDate),
      getWeightChart(period.startDate, period.endDate),
    ]);
    return { overview, weight };
  }, [period.startDate, period.endDate]);
  return (
    <>
      <PageHeader
        title="Моя статистика"
        eyebrow="Прогрес"
        description="Показники обчислено лише із завершених тренувань."
      />
      <Card className="mb-space-4 p-space-4 sm:p-space-5">
        <PeriodPicker preset={preset} period={period} onChange={change} />
      </Card>
      <div aria-live="polite" className="grid gap-space-4">
        {resource.status === "loading" && !resource.data && <LoadingState text="Завантажуємо статистику…" />}
        {resource.status === "error" && <Alert tone="error">{errorMessage(resource.error)}</Alert>}
        {resource.data && (
          <>
            <div className="grid gap-space-3 sm:grid-cols-2 xl:grid-cols-4">
              {[
                ["Заняття", String(resource.data.overview.completed_workouts)],
                ["Хвилини", formatDecimal(resource.data.overview.total_duration_min)],
                ["Вправи", String(resource.data.overview.performed_exercises)],
                ["Калорії", `${formatDecimal(resource.data.overview.estimated_calories_total)} ккал`],
              ].map(([label, value]) => (
                <Card key={label} className="p-space-4">
                  <p className="m-0 text-small text-muted-foreground">{label}</p>
                  <p className="my-space-1 text-title-large font-bold tabular-nums">{value}</p>
                  {label === "Калорії" && (resource.data?.overview.workouts_without_calorie_estimate ?? 0) > 0 && (
                    <p className="m-0 text-small">
                      {resource.data?.overview.workouts_without_calorie_estimate} занять без оцінки калорій
                    </p>
                  )}
                </Card>
              ))}
            </div>
            <div className="grid min-w-0 gap-space-4 xl:grid-cols-2">
              <Card className="min-w-0 p-space-4 sm:p-space-6">
                <WeeklyActivityChart buckets={resource.data.overview.weekly_activity} />
              </Card>
              <Card className="min-w-0 p-space-4 sm:p-space-6">
                <WeightLineChart points={resource.data.weight.points} />
              </Card>
            </div>
          </>
        )}
      </div>
    </>
  );
}
