import { useEffect, useRef } from "react";
import { Link, useLocation, useParams } from "react-router";

import { PageHeader } from "@/components/layout";
import { Alert, Card, buttonVariants } from "@/components/ui";
import { formatDateTime, formatDecimal } from "@/lib/format";
import type { CompletionResponse } from "./api";

export function CompletionResultPage() {
  const id = Number(useParams().id);
  const location = useLocation();
  const result = (location.state as { completion?: CompletionResponse } | null)?.completion;
  const headingRef = useRef<HTMLDivElement>(null);

  useEffect(() => { headingRef.current?.focus(); }, []);

  if (!result || result.id !== id) {
    return (
      <div ref={headingRef} tabIndex={-1} className="grid gap-space-4 outline-none">
        <h1 className="m-0 text-title-large">Результат недоступний після оновлення сторінки</h1>
        <Alert tone="info">Історія завершених тренувань з’явиться на наступному етапі. Поверніться до розкладу або програми.</Alert>
        <div className="flex flex-wrap gap-space-2">
          <Link className={buttonVariants({ variant: "primary" })} to="/schedule">До розкладу</Link>
          <Link className={buttonVariants({ variant: "outlined" })} to="/programs">До програм</Link>
        </div>
      </div>
    );
  }

  const achievements = result.newly_unlocked_achievements ?? result.unlocked_achievements ?? [];
  return (
    <>
      <div ref={headingRef} tabIndex={-1} className="outline-none"><PageHeader title="Тренування завершено" eyebrow="Результат" description={formatDateTime(result.completed_at)} /></div>
      <div className="grid gap-space-4 lg:grid-cols-2" aria-live="polite">
        <Card className="grid gap-space-3 p-space-4 sm:p-space-6">
          <h2 className="m-0 text-title-small">Ваш результат</h2>
          <p className="m-0 text-title-large font-bold text-primary">+{result.workout_points} балів</p>
          {result.planned_day_bonus !== undefined && result.planned_day_bonus > 0 && <p className="m-0 text-small">Бонус за тренування у запланований день: +{result.planned_day_bonus}</p>}
          <p className="m-0">Тривалість: {formatDecimal(result.duration_min)} хв</p>
          <p className="m-0">{result.estimated_calories === null ? "Калорії для цього тренування не розраховуються" : `Калорії: ${formatDecimal(result.estimated_calories)} ккал`}</p>
        </Card>
        {result.program && (
          <Card className="grid gap-space-3 p-space-4 sm:p-space-6">
            <h2 className="m-0 text-title-small">Програма</h2>
            {result.program.status === "completed" && <p className="m-0 font-semibold">Програму завершено</p>}
            <p className="m-0">Прогрес: {formatDecimal(result.program.progress_percent)}%</p>
            {result.program.bonus_earned && <p className="m-0 font-semibold text-status-success">+50 бонусних балів</p>}
            <div><Link className={buttonVariants({ variant: "outlined", size: "sm" })} to={`/programs/${result.program.id}`}>До програми</Link></div>
          </Card>
        )}
        {achievements.length > 0 && (
          <Card className="grid gap-space-3 p-space-4 sm:p-space-6 lg:col-span-2">
            <h2 className="m-0 text-title-small">Нові досягнення</h2>
            <ul className="m-0 grid gap-space-1 pl-space-5">{achievements.map((item, index) => <li key={item.id ?? index}>{item.name_snapshot ?? item.name ?? "Нове досягнення"}</li>)}</ul>
          </Card>
        )}
        <div className="flex flex-wrap gap-space-2 lg:col-span-2">
          <Link className={buttonVariants({ variant: "primary" })} to="/schedule">До розкладу</Link>
          <Link className={buttonVariants({ variant: "outlined" })} to="/programs">До програм</Link>
        </div>
      </div>
    </>
  );
}
