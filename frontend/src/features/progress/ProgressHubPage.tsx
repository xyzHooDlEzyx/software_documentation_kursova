import { Link } from "react-router";
import { PageHeader } from "@/components/layout";
import { Card, buttonVariants } from "@/components/ui";

const sections = [
  ["/stats", "Статистика", "Підсумки занять і графік ваги"],
  ["/history", "Історія", "Завершені тренування та результати"],
  ["/points", "Бали", "Баланс та історія нарахувань"],
  ["/achievements", "Досягнення", "Відкриті й майбутні нагороди"],
  ["/challenges", "Челенджі", "Цілі та особистий прогрес"],
  ["/leaderboard", "Рейтинг", "Публічний рейтинг за псевдонімами"],
] as const;
export function ProgressHubPage() {
  return (
    <>
      <PageHeader title="Прогрес" eyebrow="Результати" description="Уся ваша активність в одному місці." />
      <div className="grid gap-space-4 sm:grid-cols-2 xl:grid-cols-3">
        {sections.map(([to, title, text]) => (
          <Card key={to} className="grid content-between gap-space-4 p-space-5">
            <div>
              <h2 className="m-0 text-title-medium">{title}</h2>
              <p className="mb-0 text-muted-foreground">{text}</p>
            </div>
            <Link className={buttonVariants({ variant: "outlined" })} to={to}>
              Відкрити
            </Link>
          </Card>
        ))}
      </div>
    </>
  );
}
