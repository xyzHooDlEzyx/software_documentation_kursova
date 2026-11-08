/** Ukrainian labels for API enum codes. The API stays the source of codes. */
export const genderLabels: Record<string, string> = {
  male: "Чоловіча",
  female: "Жіноча",
  other: "Інша",
  prefer_not_to_say: "Не вказувати",
};

export const goalLabels: Record<string, string> = {
  weight_loss: "Схуднення",
  muscle_gain: "Набір м’язової маси",
  maintenance: "Підтримка форми",
};

export const levelLabels: Record<string, string> = {
  beginner: "Початківець",
  intermediate: "Середній",
  advanced: "Досвідчений",
};

export const categoryLabels: Record<string, string> = {
  cardio: "Кардіо",
  strength: "Силові",
  yoga: "Йога",
};

export const programStatusLabels: Record<string, string> = {
  draft: "Чернетка",
  active: "Активна",
  completed: "Завершена",
};

export function label(map: Record<string, string>, code: string | null | undefined) {
  if (!code) return "—";
  return map[code] ?? code;
}

export function options(map: Record<string, string>) {
  return Object.entries(map).map(([value, text]) => ({ value, label: text }));
}
