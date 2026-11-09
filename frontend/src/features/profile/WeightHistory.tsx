import { useState } from "react";

import { Alert, Card, EmptyState, LoadingState, Pagination } from "@/components/ui";
import { errorMessage } from "@/lib/errors";
import { formatDateTime, formatDecimal } from "@/lib/format";
import { useResource } from "@/lib/useResource";
import { listWeightEntries, type WeightEntry } from "./api";

const PAGE_SIZE = 20;

/** Plain SVG line of the visible entries, oldest to newest. */
function WeightChart({ entries }: { entries: WeightEntry[] }) {
  const points = [...entries].sort((a, b) => a.measured_at.localeCompare(b.measured_at));
  if (points.length < 2) return null;
  const values = points.map((entry) => Number(entry.weight_kg));
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = max - min || 1;
  const width = 600;
  const height = 160;
  const pad = 16;
  const coords = values.map((value, index) => [
    pad + (index * (width - 2 * pad)) / (values.length - 1),
    height - pad - ((value - min) * (height - 2 * pad)) / span,
  ]);
  const path = coords.map(([x, y], index) => `${index ? "L" : "M"}${x.toFixed(1)},${y.toFixed(1)}`).join(" ");
  return (
    <figure className="m-0 grid gap-space-2">
      <svg className="h-40 w-full" viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none" role="img" aria-label={`Графік ваги: від ${formatDecimal(String(values[0]))} до ${formatDecimal(String(values[values.length - 1]))} кг`}>
        <path d={path} fill="none" stroke="var(--color-brand-secondary)" strokeWidth="3" vectorEffect="non-scaling-stroke" strokeLinejoin="round" />
        {coords.map(([x, y], index) => <circle key={points[index].id} cx={x} cy={y} r="4" fill="var(--color-brand-primary)" />)}
      </svg>
      <figcaption className="flex justify-between text-caption text-muted-foreground">
        <span>мін. {formatDecimal(String(min), "кг")}</span>
        <span>макс. {formatDecimal(String(max), "кг")}</span>
      </figcaption>
    </figure>
  );
}

export function WeightHistory({ refreshKey }: { refreshKey: number }) {
  const [page, setPage] = useState(1);
  const history = useResource(() => listWeightEntries(page, PAGE_SIZE), [page, refreshKey]);
  const entries = history.data?.results ?? [];

  return (
    <Card className="grid gap-space-4 p-space-4 sm:p-space-6">
      <div className="grid gap-space-1">
        <h2 className="m-0 text-title-medium font-bold">Історія ваги</h2>
        <p className="m-0 text-small text-muted-foreground">Кожна зміна ваги в профілі зберігається окремим записом; старі записи не переписуються.</p>
      </div>
      {history.status === "loading" && !history.data && <LoadingState text="Завантажуємо історію…" />}
      {history.status === "error" && <Alert tone="error">{errorMessage(history.error)}</Alert>}
      {history.data && entries.length === 0 && <EmptyState title="Записів ще немає" />}
      {entries.length > 0 && (
        <>
          <WeightChart entries={entries} />
          <table className="w-full border-collapse text-small">
            <thead>
              <tr className="text-left text-muted-foreground">
                <th className="border-b border-outline py-space-2 font-semibold" scope="col">Дата</th>
                <th className="border-b border-outline py-space-2 text-right font-semibold" scope="col">Вага</th>
              </tr>
            </thead>
            <tbody>
              {entries.map((entry) => (
                <tr key={entry.id}>
                  <td className="border-b border-outline py-space-2">{formatDateTime(entry.measured_at)}</td>
                  <td className="border-b border-outline py-space-2 text-right font-semibold tabular-nums">{formatDecimal(entry.weight_kg, "кг")}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <Pagination page={page} pageSize={PAGE_SIZE} count={history.data?.count ?? 0} onPage={setPage} />
        </>
      )}
    </Card>
  );
}
