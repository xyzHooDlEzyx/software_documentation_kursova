import { plural, POINT_WORDS } from "@/lib/format";
import { Link, useSearchParams } from "react-router";
import { PageHeader } from "@/components/layout";
import { Alert, Card, LoadingState, Pagination, buttonVariants } from "@/components/ui";
import { errorMessage } from "@/lib/errors";
import { useResource } from "@/lib/useResource";
import { getLeaderboard } from "./api";
const PAGE_SIZE = 20;
export function LeaderboardPage() {
  const [params, setParams] = useSearchParams();
  const period = ["week", "month", "all"].includes(params.get("period") || "") ? params.get("period")! : "week";
  const page = Math.max(1, Number(params.get("page")) || 1);
  const resource = useResource(() => getLeaderboard(period, page, PAGE_SIZE), [period, page]);
  const update = (key: string, value: string) => {
    const q = new URLSearchParams(params);
    q.set(key, value);
    if (key === "period") q.delete("page");
    setParams(q);
  };
  return (
    <>
      <PageHeader
        title="Рейтинг"
        eyebrow="Прогрес"
        description="Лише псевдоніми, бали та позиції учасників, які погодилися на показ."
      />
      <div className="mb-space-4 flex flex-wrap gap-space-2" aria-label="Період рейтингу">
        {[
          ["week", "Тиждень"],
          ["month", "Місяць"],
          ["all", "Увесь час"],
        ].map(([value, label]) => (
          <button
            key={value}
            className={buttonVariants({ variant: period === value ? "primary" : "outlined" })}
            aria-pressed={period === value}
            onClick={() => update("period", value)}
          >
            {label}
          </button>
        ))}
      </div>
      <div aria-live="polite" className="grid gap-space-3">
        {resource.status === "loading" && !resource.data && <LoadingState text="Завантажуємо рейтинг…" />}
        {resource.status === "error" && <Alert tone="error">{errorMessage(resource.error)}</Alert>}
        {resource.data && !resource.data.self.opted_in && (
          <Alert tone="info">
            Ви не берете участі в публічному рейтингу. Ваші бали: {resource.data.self.points}.{" "}
            <Link to="/settings">Налаштувати участь</Link>
          </Alert>
        )}
        {resource.data?.self.opted_in && (
          <Card className="border-2 border-brand p-space-4" data-testid="leaderboard-self">
            <strong>Ваша позиція: {resource.data.self.rank ?? "—"}</strong>
            <span className="ml-space-3">{plural(resource.data.self.points, POINT_WORDS)}</span>
          </Card>
        )}
        {resource.data?.results.map((row) => (
          <Card
            key={`${row.rank}-${row.public_alias}`}
            className={`grid grid-cols-[3rem_1fr_auto] gap-space-3 p-space-4 ${resource.data?.self.opted_in && row.rank === resource.data.self.rank ? "bg-selected-state" : ""}`}
          >
            <strong>#{row.rank}</strong>
            <span>{row.public_alias}</span>
            <span>{row.points}</span>
          </Card>
        ))}
        {resource.data && (
          <Pagination
            page={page}
            pageSize={PAGE_SIZE}
            count={resource.data.count}
            onPage={(next) => update("page", String(next))}
          />
        )}
      </div>
    </>
  );
}
