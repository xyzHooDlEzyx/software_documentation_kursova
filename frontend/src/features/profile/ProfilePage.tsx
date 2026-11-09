import { useState } from "react";

import { PageHeader } from "@/components/layout";
import { Alert, Button, Card, LoadingState } from "@/components/ui";
import { errorMessage, isApiError } from "@/lib/errors";
import { formatDate, formatDecimal } from "@/lib/format";
import { genderLabels, goalLabels, label, levelLabels } from "@/lib/labels";
import { useResource } from "@/lib/useResource";
import { getProfile, type Profile } from "./api";
import { ProfileForm } from "./ProfileForm";
import { WeightHistory } from "./WeightHistory";

function Stat({ title, value }: { title: string; value: string }) {
  return (
    <div className="grid gap-space-1 rounded-field bg-muted px-space-4 py-space-3">
      <span className="text-caption font-semibold uppercase tracking-[0.06em] text-muted-foreground">{title}</span>
      <span className="text-title-small font-bold text-foreground">{value}</span>
    </div>
  );
}

function ProfileOverview({ profile }: { profile: Profile }) {
  return (
    <div className="grid gap-space-3 sm:grid-cols-2 lg:grid-cols-4">
      <Stat title="Вік" value={`${profile.age} р.`} />
      <Stat title="Вага" value={formatDecimal(profile.weight_kg, "кг")} />
      <Stat title="Зріст" value={formatDecimal(profile.height_cm, "см")} />
      <Stat title="Стать" value={label(genderLabels, profile.gender)} />
      <Stat title="Ціль" value={label(goalLabels, profile.fitness_goal)} />
      <Stat title="Рівень" value={label(levelLabels, profile.experience_level)} />
      <Stat title="Тренувань на тиждень" value={String(profile.workouts_per_week)} />
      <Stat title="Дата народження" value={formatDate(profile.date_of_birth)} />
    </div>
  );
}

export function ProfilePage() {
  const profile = useResource(getProfile, []);
  const [editing, setEditing] = useState(false);
  const [message, setMessage] = useState("");
  const [historyKey, setHistoryKey] = useState(0);
  const missing = profile.status === "error" && isApiError(profile.error, 404, "profile_missing");

  function saved(next: Profile, text: string) {
    profile.setData(next);
    setEditing(false);
    setMessage(text);
    setHistoryKey((value) => value + 1);
  }

  if (profile.status === "loading" && !profile.data) return <LoadingState text="Завантажуємо профіль…" />;

  if (missing) {
    return (
      <>
        <PageHeader title="Створіть профіль" eyebrow="Профіль" description="Ці дані потрібні для добору програми тренувань і розрахунку статистики." />
        <Card className="p-space-4 sm:p-space-6">
          <ProfileForm profile={null} onSaved={(next) => saved(next, "Профіль створено.")} />
        </Card>
      </>
    );
  }

  if (profile.status === "error" && !profile.data) {
    return <div className="grid gap-space-3"><Alert tone="error">{errorMessage(profile.error)}</Alert><div><Button onClick={profile.reload}>Спробувати ще раз</Button></div></div>;
  }

  const data = profile.data!;
  const fullName = [data.first_name, data.last_name].filter(Boolean).join(" ");
  return (
    <>
      <PageHeader title="Мій профіль" eyebrow="Профіль" description={fullName || "Ім’я не вказано"}>
        {!editing && <Button variant="outlined" onClick={() => { setMessage(""); setEditing(true); }}>Редагувати</Button>}
      </PageHeader>
      <div className="grid gap-space-6">
        {message && <Alert tone="success">{message}</Alert>}
        <Card className="p-space-4 sm:p-space-6">
          {editing
            ? <ProfileForm profile={data} onSaved={(next) => saved(next, "Зміни збережено.")} onCancel={() => setEditing(false)} />
            : <ProfileOverview profile={data} />}
        </Card>
        <WeightHistory refreshKey={historyKey} />
      </div>
    </>
  );
}
