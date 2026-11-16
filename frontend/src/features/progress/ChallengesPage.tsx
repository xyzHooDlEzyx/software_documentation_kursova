import { Link, useSearchParams } from "react-router";
import type { Paginated } from "@/app/api";
import { PageHeader } from "@/components/layout";
import { Alert, Badge, Card, EmptyState, LoadingState, Pagination, Select, buttonVariants } from "@/components/ui";
import { errorMessage } from "@/lib/errors";
import { formatDateTime } from "@/lib/format";
import { useResource } from "@/lib/useResource";
import { listChallenges, listParticipations, type Challenge, type ChallengeParticipation } from "./api";

const PAGE_SIZE = 20;

export function ChallengesPage() {
  const [params, setParams] = useSearchParams();
  const tab = params.get("tab") === "mine" ? "mine" : "available";
  const state = params.get("state") || "active";
  const status = params.get("status") || "joined";
  const page = Math.max(1, Number(params.get("page")) || 1);
  const resource = useResource<Paginated<Challenge | ChallengeParticipation>>(
    () => (tab === "mine" ? listParticipations(status, page, PAGE_SIZE) : listChallenges(state, page, PAGE_SIZE)),
    [tab, state, status, page],
  );
  const update = (key: string, value: string) => {
    const query = new URLSearchParams(params);
    query.set(key, value);
    query.delete("page");
    setParams(query);
  };
  const setPage = (next: number) => {
    const query = new URLSearchParams(params);
    query.set("page", String(next));
    setParams(query);
  };
  return (
    <>
      <PageHeader title="Челенджі" eyebrow="Прогрес" description="Доступні цілі та прогрес після вступу." />
      <div className="mb-space-4 flex flex-wrap gap-space-2" role="tablist">
        <button
          className={buttonVariants({ variant: tab === "available" ? "primary" : "outlined" })}
          onClick={() => update("tab", "available")}
        >
          Доступні
        </button>
        <button
          className={buttonVariants({ variant: tab === "mine" ? "primary" : "outlined" })}
          onClick={() => update("tab", "mine")}
        >
          Мої челенджі
        </button>
      </div>
      <Card className="mb-space-4 p-space-4">
        {tab === "available" ? (
          <Select
            id="challenge-state"
            label="Стан"
            value={state}
            options={[
              { value: "active", label: "Активні" },
              { value: "upcoming", label: "Майбутні" },
            ]}
            onChange={(event) => update("state", event.target.value)}
          />
        ) : (
          <Select
            id="challenge-status"
            label="Статус"
            value={status}
            options={[
              { value: "joined", label: "Тривають" },
              { value: "completed", label: "Завершені" },
              { value: "expired", label: "Прострочені" },
            ]}
            onChange={(event) => update("status", event.target.value)}
          />
        )}
      </Card>
      <div aria-live="polite" className="grid gap-space-3">
        {resource.status === "loading" && !resource.data && <LoadingState text="Завантажуємо челенджі…" />}
        {resource.status === "error" && <Alert tone="error">{errorMessage(resource.error)}</Alert>}
        {resource.data?.results.length === 0 && <EmptyState title="Челенджів у цьому розділі немає" />}
        {resource.data?.results.map((raw) =>
          "challenge_name" in raw ? (
            <Card key={raw.id} className="grid gap-space-2 p-space-4">
              <div className="flex justify-between gap-space-2">
                <h2 className="m-0 text-title-small">{raw.challenge_name}</h2>
                <Badge tone={raw.status === "completed" ? "success" : "neutral"}>
                  {raw.status === "joined" ? "Триває" : raw.status === "completed" ? "Завершено" : "Прострочено"}
                </Badge>
              </div>
              <p className="m-0">
                Прогрес: {raw.progress_value} / {raw.goal_value}
              </p>
              <progress
                className="w-full"
                value={raw.progress_value}
                max={raw.goal_value}
                aria-label={`Прогрес ${raw.challenge_name}`}
              />
              <p className="m-0 text-small text-muted-foreground">Вступ: {formatDateTime(raw.joined_at)}</p>
            </Card>
          ) : (
            <Card key={raw.id} className="grid gap-space-2 p-space-4 sm:grid-cols-[1fr_auto]">
              <div>
                <h2 className="m-0 text-title-small">{raw.name}</h2>
                <p className="my-space-1 text-small">Ціль: {raw.goal_value} тренувань</p>
                {raw.joined && <Badge tone="success">Ви приєдналися</Badge>}
              </div>
              <Link className={buttonVariants({ variant: "outlined", size: "sm" })} to={`/challenges/${raw.id}`}>
                Деталі
              </Link>
            </Card>
          ),
        )}
        {resource.data && <Pagination page={page} pageSize={PAGE_SIZE} count={resource.data.count} onPage={setPage} />}
      </div>
    </>
  );
}
