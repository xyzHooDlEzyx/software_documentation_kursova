import { useParams } from "react-router";
import { PageHeader } from "@/components/layout";
import { Alert, LoadingState } from "@/components/ui";
import { errorMessage } from "@/lib/errors";
import { useResource } from "@/lib/useResource";
import { getCompletedSession } from "./api";
import { CompletedSessionView } from "./CompletedSessionView";
export function HistoryDetailPage() {
  const id = Number(useParams().id);
  const resource = useResource(() => getCompletedSession(id), [id]);
  return (
    <>
      <PageHeader title="Завершене тренування" eyebrow="Історія" description="Збережений стан на момент завершення." />
      {resource.status === "loading" && !resource.data && <LoadingState text="Завантажуємо результат…" />}
      {resource.status === "error" && <Alert tone="error">{errorMessage(resource.error)}</Alert>}
      {resource.data && <CompletedSessionView session={resource.data} />}
    </>
  );
}
