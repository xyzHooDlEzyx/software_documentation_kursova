import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis, CartesianGrid } from "recharts";

import { EmptyState } from "@/components/ui";
import { formatDateTime, formatDecimal } from "@/lib/format";

export type WeightChartPoint = { measured_at: string; weight_kg: string };

export function WeightLineChart({ points, title = "Зміна ваги" }: { points: WeightChartPoint[]; title?: string }) {
  const data = [...points]
    .sort((a, b) => a.measured_at.localeCompare(b.measured_at))
    .map((point) => ({ ...point, value: Number(point.weight_kg), label: formatDateTime(point.measured_at) }));
  if (data.length === 0) return <EmptyState title="Немає вимірів ваги за цей період" />;
  return (
    <figure
      className="m-0 grid min-w-0 gap-space-3"
      aria-labelledby="weight-chart-title"
      aria-describedby="weight-chart-description"
    >
      <figcaption id="weight-chart-title" className="font-semibold">
        {title}
      </figcaption>
      <p id="weight-chart-description" className="sr-only">
        Лінійний графік ваги в кілограмах у хронологічному порядку. Таблиця після графіка містить усі значення.
      </p>
      <div className="h-64 min-w-0" aria-hidden="true">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 8, right: 12, bottom: 8, left: 0 }}>
            <CartesianGrid stroke="var(--color-chart-grid)" strokeDasharray="4 4" />
            <XAxis
              dataKey="label"
              tick={{ fill: "var(--color-chart-label)", fontSize: 12 }}
              tickFormatter={(value: string) => value.slice(0, 10)}
            />
            <YAxis
              unit=" кг"
              domain={["dataMin - 1", "dataMax + 1"]}
              tick={{ fill: "var(--color-chart-label)", fontSize: 12 }}
              width={58}
            />
            <Tooltip formatter={(value) => [formatDecimal(String(value), "кг"), "Вага"]} />
            <Line
              type="monotone"
              dataKey="value"
              stroke="var(--color-chart-primary)"
              strokeWidth={3}
              dot={{ fill: "var(--color-chart-secondary)", r: 4 }}
              activeDot={{ r: 6 }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
      <div className="sr-only">
        <h3>Дані графіка ваги</h3>
        <ul>
          {data.map((point) => (
            <li key={point.measured_at}>
              {point.label}: {formatDecimal(point.weight_kg, "кг")}
            </li>
          ))}
        </ul>
      </div>
    </figure>
  );
}
