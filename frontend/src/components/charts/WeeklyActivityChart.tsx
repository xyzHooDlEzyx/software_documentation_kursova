import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { EmptyState } from "@/components/ui";
import type { WeeklyActivity } from "@/features/progress/api";
import { formatDate, formatDecimal } from "@/lib/format";
import { addIsoDays } from "@/lib/kyivDateTime";

function compactDate(date: string) {
  return formatDate(date).slice(0, 5);
}

export function weeklyActivityLabel(weekStart: string) {
  return `${compactDate(weekStart)}–${compactDate(addIsoDays(weekStart, 6))}`;
}

export function WeeklyActivityChart({ buckets }: { buckets: WeeklyActivity[] }) {
  const data = buckets.map((bucket) => ({ ...bucket, label: weeklyActivityLabel(bucket.week_start) }));
  if (data.length === 0 || data.every((bucket) => bucket.completed_workouts === 0)) {
    return <EmptyState title="Немає активності за цей період" />;
  }
  return (
    <figure
      className="m-0 grid min-w-0 gap-space-3"
      aria-labelledby="activity-chart-title"
      aria-describedby="activity-chart-description"
    >
      <figcaption id="activity-chart-title" className="font-semibold">
        Активність по тижнях
      </figcaption>
      <p id="activity-chart-description" className="sr-only">
        Стовпчастий графік кількості завершених тренувань за тиждень. Таблиця після графіка містить тренування і
        тривалість у хвилинах.
      </p>
      <div className="h-64 min-w-0" aria-hidden="true" data-testid="weekly-activity-bars">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 8, right: 12, bottom: 8, left: 0 }}>
            <CartesianGrid stroke="var(--color-chart-grid)" strokeDasharray="4 4" />
            <XAxis dataKey="label" tick={{ fill: "var(--color-chart-label)", fontSize: 12 }} />
            <YAxis allowDecimals={false} tick={{ fill: "var(--color-chart-label)", fontSize: 12 }} width={36} />
            <Tooltip
              formatter={(value, _name, item) => [
                `${value} тренувань · ${formatDecimal(String(item.payload.total_duration_min), "хв")}`,
                "Активність",
              ]}
            />
            <Bar
              dataKey="completed_workouts"
              name="Завершені тренування"
              fill="var(--color-chart-primary)"
              radius={[6, 6, 0, 0]}
            />
          </BarChart>
        </ResponsiveContainer>
      </div>
      <table className="sr-only">
        <caption>Дані активності по тижнях</caption>
        <thead>
          <tr>
            <th>Тиждень</th>
            <th>Завершені тренування</th>
            <th>Тривалість</th>
          </tr>
        </thead>
        <tbody>
          {data.map((bucket) => (
            <tr key={bucket.week_start}>
              <td>{bucket.label}</td>
              <td>{bucket.completed_workouts}</td>
              <td>{formatDecimal(bucket.total_duration_min, "хв")}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </figure>
  );
}
