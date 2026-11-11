import { useState } from "react";
import { Link, useNavigate } from "react-router";

import { PageHeader } from "@/components/layout";
import { Alert, Badge, Button, Card, EmptyState, LoadingState, buttonVariants } from "@/components/ui";
import { errorMessage, isApiError } from "@/lib/errors";
import { goalLabels, label, levelLabels } from "@/lib/labels";
import { useResource } from "@/lib/useResource";
import { createProgram, getRecommendation } from "./api";

const STRATEGY_LABELS: Record<string, string> = {
  WeightLossSelectionStrategy: "Схуднення: більша частка кардіо",
  MuscleGainSelectionStrategy: "Набір маси: більша частка силових",
  MaintenanceSelectionStrategy: "Підтримка: збалансований склад",
};

export function RecommendationPage() {
  const recommendation = useResource(getRecommendation, []);
  const navigate = useNavigate();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function accept(templateId: number) {
    setBusy(true);
    setError("");
    try {
      const program = await createProgram(templateId);
      navigate(`/programs/${program.id}`, { state: { message: "Програму створено. Це ваша особиста копія — її можна змінювати." } });
    } catch (reason) {
      if (isApiError(reason, 409, "recommendation_mismatch")) {
        setError("Рекомендація змінилась (наприклад, після редагування профілю). Оновили пропозицію — перегляньте її ще раз.");
        recommendation.reload();
      } else {
        setError(errorMessage(reason));
      }
    } finally {
      setBusy(false);
    }
  }

  const header = <PageHeader title="Рекомендована програма" eyebrow="Програми" description="Шаблон добирається за ціллю, рівнем і частотою з вашого профілю; критерій складу залежить від цілі (патерн Strategy)." />;

  if (recommendation.status === "loading") return <>{header}<LoadingState text="Підбираємо програму…" /></>;
  if (recommendation.status === "error") {
    if (isApiError(recommendation.error, 404, "profile_missing")) {
      return <>{header}<EmptyState title="Спершу заповніть профіль">Без цілі, рівня і частоти тренувань рекомендацію не побудувати.<div className="mt-space-3"><Link className={buttonVariants({ variant: "primary", size: "md" })} to="/profile">Заповнити профіль</Link></div></EmptyState></>;
    }
    if (isApiError(recommendation.error, 404, "recommendation_unavailable")) {
      return <>{header}<EmptyState title="Немає відповідного шаблону">Для вашої цілі й рівня ще немає опублікованих програм. Спробуйте змінити параметри профілю або зверніться до адміністратора.</EmptyState></>;
    }
    return <>{header}<Alert tone="error">{errorMessage(recommendation.error)}</Alert></>;
  }

  const { program_template: template, reason } = recommendation.data;
  return (
    <>
      {header}
      <div className="grid gap-space-6 lg:grid-cols-[2fr_1fr]">
        <Card className="grid gap-space-4 p-space-4 sm:p-space-6">
          <div className="flex flex-wrap gap-space-2">
            <Badge tone="accent">{label(goalLabels, template.fitness_goal)}</Badge>
            <Badge>{label(levelLabels, template.experience_level)}</Badge>
            <Badge tone="outline">{template.workouts_per_week} трен./тиждень</Badge>
          </div>
          <h2 className="m-0 text-title-large font-bold">{template.name}</h2>
          {template.description && <p className="m-0 text-body text-muted-foreground">{template.description}</p>}
          <ol className="m-0 grid list-none gap-space-2 p-0">
            {template.workouts.map((workout) => (
              <li key={workout.position} className="flex items-center gap-space-3 rounded-field border border-outline px-space-4 py-space-3">
                <span className="grid size-8 shrink-0 place-items-center rounded-full bg-muted text-small font-bold">{workout.position}</span>
                <Link to={`/catalog/workouts/${workout.workout_id}`} className="font-semibold text-foreground">{workout.name}</Link>
              </li>
            ))}
          </ol>
          {error && <Alert tone="error">{error}</Alert>}
          <div><Button loading={busy} onClick={() => void accept(template.id)}>Прийняти й створити мою програму</Button></div>
        </Card>
        <Card className="grid content-start gap-space-3 p-space-4 sm:p-space-6">
          <h2 className="m-0 text-title-small font-bold">Чому саме ця програма</h2>
          <dl className="m-0 grid gap-space-2 text-small">
            <div><dt className="text-muted-foreground">Ціль збігається</dt><dd className="m-0 font-semibold">{reason.exact_goal ? "Так" : "Ні"}</dd></div>
            <div><dt className="text-muted-foreground">Рівень збігається</dt><dd className="m-0 font-semibold">{reason.exact_level ? "Так" : "Ні"}</dd></div>
            <div><dt className="text-muted-foreground">Різниця в частоті</dt><dd className="m-0 font-semibold">{reason.frequency_difference} трен./тиждень</dd></div>
            <div><dt className="text-muted-foreground">Стратегія добору</dt><dd className="m-0 font-semibold">{STRATEGY_LABELS[reason.strategy] ?? reason.strategy}</dd></div>
            <div><dt className="text-muted-foreground">Критерій складу</dt><dd className="m-0 font-semibold">{reason.composition_criterion}</dd></div>
          </dl>
        </Card>
      </div>
    </>
  );
}
