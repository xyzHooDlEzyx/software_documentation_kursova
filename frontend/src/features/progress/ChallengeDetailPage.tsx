import { useState } from "react";
import { useParams } from "react-router";
import { ApiError } from "@/app/api";
import { PageHeader } from "@/components/layout";
import { Alert, Badge, Button, Card, LoadingState } from "@/components/ui";
import { errorMessage } from "@/lib/errors";
import { formatDateTime } from "@/lib/format";
import { useResource } from "@/lib/useResource";
import { getChallenge, joinChallenge } from "./api";
export function ChallengeDetailPage() {
  const id = Number(useParams().id);
  const resource = useResource(() => getChallenge(id), [id]);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");
  async function join() {
    if (!window.confirm("Приєднатися до цього челенджу?")) return;
    setBusy(true);
    setError("");
    try {
      await joinChallenge(id);
      setNotice("Ви приєдналися до челенджу.");
      resource.reload();
    } catch (reason) {
      setError(
        reason instanceof ApiError && reason.status === 409
          ? "Термін вступу до челенджу вже минув."
          : errorMessage(reason),
      );
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <PageHeader
        title={resource.data?.name ?? "Деталі челенджу"}
        eyebrow="Челенджі"
        description="Умови та строки участі."
      />
      <div aria-live="polite">
        {resource.status === "loading" && !resource.data && <LoadingState text="Завантажуємо челендж…" />}
        {resource.status === "error" && <Alert tone="error">{errorMessage(resource.error)}</Alert>}
        {notice && <Alert tone="success">{notice}</Alert>}
        {error && <Alert tone="error">{error}</Alert>}
        {resource.data && (
          <Card className="grid gap-space-3 p-space-5">
            <div>{resource.data.joined && <Badge tone="success">Ви приєдналися</Badge>}</div>
            <p className="m-0">Початок: {formatDateTime(resource.data.start_at)}</p>
            <p className="m-0">Завершення: {formatDateTime(resource.data.end_at)}</p>
            <p className="m-0">Ціль: {resource.data.goal_value} тренувань</p>
            {!resource.data.joined && (
              <div>
                <Button loading={busy} onClick={() => void join()}>
                  Приєднатися
                </Button>
              </div>
            )}
          </Card>
        )}
      </div>
    </>
  );
}
