import { PageHeader } from "@/components/layout";
import { Alert, Badge, Card, EmptyState, LoadingState } from "@/components/ui";
import { errorMessage } from "@/lib/errors";
import { formatDateTime } from "@/lib/format";
import { useResource } from "@/lib/useResource";
import { listAchievements, listUserAchievements } from "./api";
export function AchievementsPage() {
  const resource = useResource(async () => {
    const [definitions, unlocks] = await Promise.all([listAchievements(), listUserAchievements()]);
    return { definitions, unlocks };
  }, []);
  return (
    <>
      <PageHeader
        title="Досягнення"
        eyebrow="Прогрес"
        description="П’ять доступних нагород і ваші фактичні розблокування."
      />
      <div aria-live="polite" className="grid gap-space-3">
        {resource.status === "loading" && !resource.data && <LoadingState text="Завантажуємо досягнення…" />}
        {resource.status === "error" && <Alert tone="error">{errorMessage(resource.error)}</Alert>}
        {resource.data?.definitions.results.length === 0 && <EmptyState title="Досягнення недоступні" />}
        {resource.data?.definitions.results.map((item) => {
          const unlocked = resource.data!.unlocks.results.find(
            (value) => value.achievement_id === item.id || value.rule_code_snapshot === item.code,
          );
          return (
            <Card key={item.id} className="grid gap-space-2 p-space-4">
              <div className="flex flex-wrap items-center justify-between gap-space-2">
                <h2 className="m-0 text-title-small">{item.name}</h2>
                <Badge tone={unlocked ? "success" : "neutral"}>{unlocked ? "Відкрито" : "Заблоковано"}</Badge>
              </div>
              <p className="m-0 text-muted-foreground">{item.description}</p>
              {unlocked && <p className="m-0 text-small">Відкрито {formatDateTime(unlocked.unlocked_at)}</p>}
            </Card>
          );
        })}
      </div>
    </>
  );
}
