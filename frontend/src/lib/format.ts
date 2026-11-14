import { TZDate, tz } from "@date-fns/tz";
import { format } from "date-fns";
import { uk } from "date-fns/locale/uk";

import { KYIV } from "./kyivDateTime";

const inKyiv = tz(KYIV);

/** Formats an ISO date (YYYY-MM-DD) without shifting it through the machine zone. */
export function formatDate(isoDate: string) {
  const [year, month, day] = isoDate.split("-").map(Number);
  return format(new TZDate(year, month - 1, day, KYIV), "dd.MM.yyyy", { in: inKyiv });
}

export function formatDateTime(isoDateTime: string) {
  return format(new TZDate(isoDateTime, KYIV), "dd.MM.yyyy, HH:mm", { in: inKyiv });
}

export function formatTime(isoDateTime: string) {
  return format(new TZDate(isoDateTime, KYIV), "HH:mm", { in: inKyiv });
}

export function formatWeekday(isoDate: string, width: "short" | "long") {
  const [year, month, day] = isoDate.split("-").map(Number);
  const text = format(new TZDate(year, month - 1, day, KYIV), width === "short" ? "EEEEEE" : "EEEE", { in: inKyiv, locale: uk });
  return text.charAt(0).toLocaleUpperCase("uk-UA") + text.slice(1);
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
