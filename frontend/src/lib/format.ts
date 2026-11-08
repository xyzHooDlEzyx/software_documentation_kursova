const dateFormatter = new Intl.DateTimeFormat("uk-UA", { day: "2-digit", month: "2-digit", year: "numeric" });
const dateTimeFormatter = new Intl.DateTimeFormat("uk-UA", {
  day: "2-digit",
  month: "2-digit",
  year: "numeric",
  hour: "2-digit",
  minute: "2-digit",
  timeZone: "Europe/Kyiv",
});

/** Formats an ISO date (YYYY-MM-DD) without shifting it through UTC. */
export function formatDate(isoDate: string) {
  const [year, month, day] = isoDate.split("-").map(Number);
  return dateFormatter.format(new Date(year, month - 1, day));
}

export function formatDateTime(isoDateTime: string) {
  return dateTimeFormatter.format(new Date(isoDateTime));
}

/** API decimals arrive as strings; show them with a decimal comma. */
export function formatDecimal(value: string | null | undefined, unit = "") {
  if (value === null || value === undefined || value === "") return "—";
  const number = Number(value);
  const text = Number.isFinite(number) ? number.toLocaleString("uk-UA", { maximumFractionDigits: 3 }) : value;
  return unit ? `${text} ${unit}` : text;
}

/** Ukrainian plural: plural(2, ["вправа", "вправи", "вправ"]) → "2 вправи". */
export function plural(count: number, [one, few, many]: [string, string, string]) {
  const mod10 = count % 10;
  const mod100 = count % 100;
  const word = mod10 === 1 && mod100 !== 11 ? one : mod10 >= 2 && mod10 <= 4 && (mod100 < 12 || mod100 > 14) ? few : many;
  return `${count} ${word}`;
}

export const EXERCISE_WORDS: [string, string, string] = ["вправа", "вправи", "вправ"];
