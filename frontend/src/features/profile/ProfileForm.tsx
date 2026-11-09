import { useState, type FormEvent } from "react";

import { Alert, Button, Select, TextInput } from "@/components/ui";
import { errorMessage, fieldErrors } from "@/lib/errors";
import { genderLabels, goalLabels, levelLabels, options } from "@/lib/labels";
import { createProfile, updateProfile, type Profile, type ProfileInput } from "./api";

type FormValues = Record<keyof ProfileInput, string>;

const EMPTY: FormValues = {
  first_name: "",
  last_name: "",
  date_of_birth: "",
  weight_kg: "",
  height_cm: "",
  gender: "",
  fitness_goal: "",
  experience_level: "",
  workouts_per_week: "3",
};

function toValues(profile: Profile): FormValues {
  return {
    first_name: profile.first_name,
    last_name: profile.last_name,
    date_of_birth: profile.date_of_birth,
    weight_kg: profile.weight_kg,
    height_cm: profile.height_cm,
    gender: profile.gender,
    fitness_goal: profile.fitness_goal,
    experience_level: profile.experience_level,
    workouts_per_week: String(profile.workouts_per_week),
  };
}

function toInput(values: FormValues): ProfileInput {
  return {
    first_name: values.first_name.trim(),
    last_name: values.last_name.trim(),
    date_of_birth: values.date_of_birth,
    weight_kg: values.weight_kg.trim(),
    height_cm: values.height_cm.trim(),
    gender: values.gender,
    fitness_goal: values.fitness_goal,
    experience_level: values.experience_level,
    workouts_per_week: Number(values.workouts_per_week),
  };
}

/** Only changed fields go to P03, so an unchanged weight does not add a WeightEntry. */
function changedFields(initial: Profile, next: ProfileInput): Partial<ProfileInput> {
  const changes: Partial<ProfileInput> = {};
  for (const key of Object.keys(next) as (keyof ProfileInput)[]) {
    const before = initial[key];
    const after = next[key];
    const same = key === "weight_kg" || key === "height_cm" ? Number(before) === Number(after) : String(before) === String(after);
    if (!same) Object.assign(changes, { [key]: after });
  }
  return changes;
}

function localToday() {
  const now = new Date();
  return new Date(now.getTime() - now.getTimezoneOffset() * 60_000).toISOString().slice(0, 10);
}

export function ProfileForm({ profile, onSaved, onCancel }: { profile: Profile | null; onSaved: (profile: Profile) => void; onCancel?: () => void }) {
  const [values, setValues] = useState<FormValues>(profile ? toValues(profile) : EMPTY);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [formError, setFormError] = useState("");
  const [busy, setBusy] = useState(false);

  function set<K extends keyof FormValues>(key: K, value: string) {
    setValues((previous) => ({ ...previous, [key]: value }));
  }

  function validate(input: ProfileInput) {
    const next: Record<string, string> = {};
    if (!input.date_of_birth) next.date_of_birth = "Вкажіть дату народження.";
    if (!input.weight_kg) next.weight_kg = "Вкажіть вагу.";
    if (!input.height_cm) next.height_cm = "Вкажіть зріст.";
    if (!input.gender) next.gender = "Оберіть стать.";
    if (!input.fitness_goal) next.fitness_goal = "Оберіть ціль.";
    if (!input.experience_level) next.experience_level = "Оберіть рівень підготовки.";
    return next;
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFormError("");
    const input = toInput(values);
    const clientErrors = validate(input);
    setErrors(clientErrors);
    if (Object.keys(clientErrors).length) return;
    if (profile) {
      const changes = changedFields(profile, input);
      if (!Object.keys(changes).length) { onCancel?.(); return; }
    }
    setBusy(true);
    try {
      const saved = profile ? await updateProfile(changedFields(profile, input)) : await createProfile(input);
      onSaved(saved);
    } catch (reason) {
      setErrors(fieldErrors(reason));
      setFormError(errorMessage(reason));
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="grid gap-space-5" onSubmit={(event) => void submit(event)} noValidate>
      {formError && <Alert tone="error">{formError}</Alert>}
      <div className="grid gap-space-4 sm:grid-cols-2">
        <TextInput id="first-name" label="Ім’я (необов’язково)" value={values.first_name} maxLength={150} onChange={(e) => set("first_name", e.target.value)} error={errors.first_name} />
        <TextInput id="last-name" label="Прізвище (необов’язково)" value={values.last_name} maxLength={150} onChange={(e) => set("last_name", e.target.value)} error={errors.last_name} />
        <TextInput id="date-of-birth" label="Дата народження" type="date" max={localToday()} value={values.date_of_birth} onChange={(e) => set("date_of_birth", e.target.value)} error={errors.date_of_birth} hint="Вік на момент створення профілю — від 19 до 59 років." />
        <Select id="gender" label="Стать" placeholder="Оберіть…" options={options(genderLabels)} value={values.gender} onChange={(e) => set("gender", e.target.value)} error={errors.gender} />
        <TextInput id="weight" label="Вага, кг" type="number" inputMode="decimal" step="0.1" min="20" max="500" value={values.weight_kg} onChange={(e) => set("weight_kg", e.target.value)} error={errors.weight_kg} hint={profile ? "Зміна ваги додає запис в історію." : undefined} />
        <TextInput id="height" label="Зріст, см" type="number" inputMode="decimal" step="0.1" min="100" max="250" value={values.height_cm} onChange={(e) => set("height_cm", e.target.value)} error={errors.height_cm} />
        <Select id="fitness-goal" label="Ціль" placeholder="Оберіть…" options={options(goalLabels)} value={values.fitness_goal} onChange={(e) => set("fitness_goal", e.target.value)} error={errors.fitness_goal} />
        <Select id="experience-level" label="Рівень підготовки" placeholder="Оберіть…" options={options(levelLabels)} value={values.experience_level} onChange={(e) => set("experience_level", e.target.value)} error={errors.experience_level} />
        <Select id="workouts-per-week" label="Тренувань на тиждень" options={[1, 2, 3, 4, 5, 6, 7].map((n) => ({ value: String(n), label: String(n) }))} value={values.workouts_per_week} onChange={(e) => set("workouts_per_week", e.target.value)} error={errors.workouts_per_week} />
      </div>
      <div className="flex flex-wrap gap-space-2">
        <Button type="submit" loading={busy}>{profile ? "Зберегти зміни" : "Створити профіль"}</Button>
        {onCancel && <Button variant="outlined" onClick={onCancel} disabled={busy}>Скасувати</Button>}
      </div>
    </form>
  );
}
