import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router";

import { ApiError, updateLeaderboard } from "../app/api";
import { useAuth } from "../app/auth/AuthProvider";
import { Alert, Button, Card, Switch, TextInput } from "../components/ui";
import { PageHeader } from "../components/layout";

export function SettingsPage() {
  const { account, setAccount, notice } = useAuth();
  const navigate = useNavigate();
  const [alias, setAlias] = useState(account?.public_alias ?? "");
  const [optIn, setOptIn] = useState(account?.leaderboard_opt_in ?? false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [fieldError, setFieldError] = useState("");

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setMessage("");
    setError("");
    setFieldError("");
    if (optIn && !alias.trim()) {
      setFieldError("Введіть псевдонім, щоб увімкнути показ у рейтингу.");
      return;
    }
    setBusy(true);
    try {
      const nextAccount = await updateLeaderboard(alias.trim() || null, optIn);
      setAccount(nextAccount);
      setAlias(nextAccount.public_alias ?? "");
      setOptIn(nextAccount.leaderboard_opt_in);
      setMessage("Налаштування рейтингу збережено.");
    } catch (reason) {
      if (reason instanceof ApiError) {
        setFieldError(reason.fields.public_alias?.join(" ") ?? "");
        if (reason.status === 401) {
          setAccount(null);
          navigate("/login", { replace: true, state: { from: { pathname: "/settings" } } });
          return;
        }
      }
      setError(reason instanceof ApiError ? reason.message : "Не вдалося виконати запит. Спробуйте ще раз.");
    } finally { setBusy(false); }
  }

  return (
    <>
      <PageHeader title="Налаштування" eyebrow="Акаунт" description="Керуйте ім’ям, яке бачать інші учасники рейтингу." />
      <Card className="grid gap-space-4 p-space-4 sm:p-space-6">
        {notice && <Alert tone="error">{notice}</Alert>}
        {message && <Alert tone="success">{message}</Alert>}
        {error && <Alert tone="error">{error}</Alert>}
        <form className="grid gap-space-5" onSubmit={(event) => void submit(event)}>
          <TextInput id="public-alias" label="Псевдонім" value={alias} maxLength={80} onChange={(event) => setAlias(event.target.value)} error={fieldError} hint="Псевдонім обов’язковий, якщо ви вмикаєте показ у рейтингу." />
          <Switch id="leaderboard-opt-in" label="Показувати мене в рейтингу" checked={optIn} onChange={(event) => { setOptIn(event.target.checked); if (!event.target.checked) setFieldError(""); }} />
          <Button type="submit" loading={busy}>Зберегти</Button>
        </form>
      </Card>
    </>
  );
}
