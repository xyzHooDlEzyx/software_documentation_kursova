import { useState } from "react";

import { Alert, Card, EmptyState, LoadingState, Pagination } from "@/components/ui";
import { errorMessage } from "@/lib/errors";
import { formatDateTime, formatDecimal } from "@/lib/format";
import { useResource } from "@/lib/useResource";
import { WeightLineChart } from "@/components/charts/WeightLineChart";
import { listWeightEntries } from "./api";

const PAGE_SIZE = 20;

export function WeightHistory({ refreshKey }: { refreshKey: number }) {
  const [page, setPage] = useState(1);
  const history = useResource(() => listWeightEntries(page, PAGE_SIZE), [page, refreshKey]);
  const entries = history.data?.results ?? [];

  return (
    <Card className="grid gap-space-4 p-space-4 sm:p-space-6">
      <div className="grid gap-space-1">
        <h2 className="m-0 text-title-medium font-bold">Історія ваги</h2>
        <p className="m-0 text-small text-muted-foreground">
          Кожна зміна ваги в профілі зберігається окремим записом; старі записи не переписуються.
        </p>
      </div>
      {history.status === "loading" && !history.data && <LoadingState text="Завантажуємо історію…" />}
      {history.status === "error" && <Alert tone="error">{errorMessage(history.error)}</Alert>}
      {history.data && entries.length === 0 && <EmptyState title="Записів ще немає" />}
      {entries.length > 0 && (
        <>
          <WeightLineChart points={entries} title="Графік останніх вимірів" />
          <table className="w-full border-collapse text-small">
            <thead>
              <tr className="text-left text-muted-foreground">
                <th className="border-b border-outline py-space-2 font-semibold" scope="col">
                  Дата
                </th>
                <th className="border-b border-outline py-space-2 text-right font-semibold" scope="col">
                  Вага
                </th>
              </tr>
            </thead>
            <tbody>
              {entries.map((entry) => (
                <tr key={entry.id}>
                  <td className="border-b border-outline py-space-2">{formatDateTime(entry.measured_at)}</td>
                  <td className="border-b border-outline py-space-2 text-right font-semibold tabular-nums">
                    {formatDecimal(entry.weight_kg, "кг")}
                  </td>
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
