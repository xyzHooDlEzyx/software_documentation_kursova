import { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router";

import { PageHeader } from "@/components/layout";
import { Alert, Button, Card, EmptyState, LoadingState, buttonVariants } from "@/components/ui";
import { errorMessage } from "@/lib/errors";
import { formatDate, formatTime, formatWeekday } from "@/lib/format";
import { addIsoDays, kyivDateKey, kyivToday, kyivWeekMonday } from "@/lib/kyivDateTime";
import { label, scheduledSessionStatusLabels } from "@/lib/labels";
import { useResource } from "@/lib/useResource";
import { listAllSessions } from "./api";
import { clearSessionNameCache, resolveSessionNames, type SessionNames } from "./names";

export function CalendarPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const requested = searchParams.get("week") ?? kyivToday();
  const week = kyivWeekMonday(/^\d{4}-\d{2}-\d{2}$/.test(requested) ? requested : kyivToday());
  const end = addIsoDays(week, 7);
  const sessions = useResource(() => listAllSessions(week, end), [week, end]);
  const [names, setNames] = useState(new Map<number, SessionNames>());

  useEffect(() => {
    clearSessionNameCache();
  }, []);

  useEffect(() => {
    let active = true;
    if (sessions.data) void resolveSessionNames(sessions.data).then((value) => { if (active) setNames(value); });
    return () => { active = false; };
  }, [sessions.data]);

  const days = useMemo(() => Array.from({ length: 7 }, (_, index) => addIsoDays(week, index)), [week]);
  function go(next: string) { setSearchParams({ week: kyivWeekMonday(next) }); }

  return (
    <>
      <PageHeader title="Розклад тренувань" eyebrow="Календар" description={`Тиждень ${formatDate(week)} — ${formatDate(addIsoDays(end, -1))}, час за Києвом`}>
        <Link className={buttonVariants({ variant: "outlined", size: "sm" })} to="/programs">Запланувати з програми</Link>
      </PageHeader>
      <div className="mb-space-4 flex flex-wrap items-center justify-between gap-space-2" aria-label="Навігація тижнями">
        <Button variant="outlined" size="sm" onClick={() => go(addIsoDays(week, -7))}>Попередній</Button>
        <Button variant="secondary" size="sm" onClick={() => go(kyivToday())}>Сьогодні</Button>
        <Button variant="outlined" size="sm" onClick={() => go(addIsoDays(week, 7))}>Наступний</Button>
      </div>
      {sessions.status === "loading" && !sessions.data && <LoadingState text="Завантажуємо розклад…" />}
      {sessions.status === "error" && !sessions.data && <Alert tone="error">{errorMessage(sessions.error)}</Alert>}
      {sessions.data?.length === 0 && (
        <EmptyState title="На цей тиждень тренувань немає">
          <p>Заплануйте заняття з особистої програми або каталогу.</p><div className="flex flex-wrap justify-center gap-space-2"><Link className={buttonVariants()} to="/programs">До програм</Link><Link className={buttonVariants({ variant: "outlined" })} to="/catalog">До каталогу</Link></div>
        </EmptyState>
      )}
      {!!sessions.data?.length && (
        // Seven columns only where a day gets ~170px (2xl); narrower screens get a day-per-row agenda.
        <div className="grid gap-space-2 2xl:grid-cols-7 2xl:gap-space-3">
          {days.map((day) => {
            const daySessions = sessions.data!.filter((item) => item.scheduled_at && kyivDateKey(item.scheduled_at) === day);
            const isToday = day === kyivToday();
            return (
              <section key={day} className={`grid min-w-0 gap-space-2 rounded-panel p-space-3 md:grid-cols-[9rem_minmax(0,1fr)] md:items-start 2xl:grid-cols-1 2xl:content-start ${isToday ? "bg-selected-state ring-1 ring-secondary" : ""}`} aria-labelledby={`day-${day}`}>
                <h2 id={`day-${day}`} className="m-0 text-small font-bold md:pt-space-2 2xl:pt-0" aria-current={isToday ? "date" : undefined}>
                  <span className="2xl:hidden">{formatWeekday(day, "long")}, {formatDate(day).slice(0, 5)}</span>
                  <span className="hidden 2xl:inline">{formatWeekday(day, "short")}, {formatDate(day).slice(0, 5)}</span>
                  {isToday && <span className="ml-space-2 text-caption font-semibold text-muted-foreground">сьогодні</span>}
                </h2>
                {daySessions.length ? (
                  <div className="grid min-w-0 gap-space-2 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-1">
                    {daySessions.map((item) => {
                      const displayStatus = item.is_missed ? "missed" : item.status;
                      const dayNames = names.get(item.id);
                      return <Link key={item.id} to={`/schedule/${item.id}`} className={`min-w-0 rounded-panel no-underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring ${item.status === "cancelled" ? "opacity-60" : ""}`}>
                        <Card className={`grid h-full min-w-0 gap-space-1 p-space-3 transition-shadow hover:shadow-panel-hover ${item.status === "completed" ? "bg-muted" : ""}`}>
                          <span className="font-bold tabular-nums text-foreground">{formatTime(item.scheduled_at)}</span>
                          <span className="hyphens-auto text-small font-semibold text-foreground [overflow-wrap:anywhere]">{dayNames?.workout ?? `Тренування #${item.source_workout_id}`}</span>
                          {dayNames?.program && <span className="hyphens-auto text-caption text-muted-foreground [overflow-wrap:anywhere]">{dayNames.program}</span>}
                          <span className="inline-flex min-w-0 items-center gap-space-1 text-caption font-semibold text-foreground">
                            <span aria-hidden="true" className={`size-2 shrink-0 rounded-full ${item.is_missed ? "border border-input-border" : item.status === "planned" ? "bg-brand" : "bg-muted-foreground"}`} />
                            {label(scheduledSessionStatusLabels, displayStatus)}
                          </span>
                        </Card>
                      </Link>;
                    })}
                  </div>
                ) : (
                  <p className="m-0 text-small text-muted-foreground md:pt-space-2 2xl:rounded-field 2xl:border 2xl:border-dashed 2xl:border-outline 2xl:p-space-2 2xl:text-center 2xl:text-caption">Немає тренувань</p>
                )}
              </section>
            );
          })}
        </div>
      )}
    </>
  );
}
