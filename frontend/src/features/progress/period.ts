import { TZDate, tz } from "@date-fns/tz";
import { addMonths, format, startOfMonth, subMonths } from "date-fns";

import { addIsoDays, KYIV, kyivToday, kyivWeekMonday } from "@/lib/kyivDateTime";

export type PeriodPreset = "week" | "month" | "three-months" | "custom";
export type DatePeriod = { startDate: string; endDate: string };

const inKyiv = tz(KYIV);

function localDate(value: string) {
  const [year, month, day] = value.split("-").map(Number);
  return new TZDate(year, month - 1, day, KYIV);
}

function dateKey(value: Date) {
  return format(value, "yyyy-MM-dd", { in: inKyiv });
}

export function periodFor(preset: Exclude<PeriodPreset, "custom">, anchor = kyivToday()): DatePeriod {
  if (preset === "week") {
    const startDate = kyivWeekMonday(anchor);
    return { startDate, endDate: addIsoDays(startDate, 7) };
  }
  const monthStart = startOfMonth(localDate(anchor), { in: inKyiv });
  if (preset === "month")
    return { startDate: dateKey(monthStart), endDate: dateKey(addMonths(monthStart, 1, { in: inKyiv })) };
  return {
    startDate: dateKey(subMonths(monthStart, 2, { in: inKyiv })),
    endDate: dateKey(addMonths(monthStart, 1, { in: inKyiv })),
  };
}

export function validPeriod(period: DatePeriod) {
  return (
    /^\d{4}-\d{2}-\d{2}$/.test(period.startDate) &&
    /^\d{4}-\d{2}-\d{2}$/.test(period.endDate) &&
    period.startDate < period.endDate
  );
}
