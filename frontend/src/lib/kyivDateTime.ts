import { TZDate, tz } from "@date-fns/tz";
import { addDays, format, isValid, startOfWeek, subHours } from "date-fns";

export const KYIV = "Europe/Kyiv";
const inKyiv = tz(KYIV);
const DATE_PATTERN = /^\d{4}-\d{2}-\d{2}$/;
const TIME_PATTERN = /^\d{2}:\d{2}$/;

function kyivWallClock(date: string, time = "00:00") {
  if (!DATE_PATTERN.test(date) || !TIME_PATTERN.test(time)) throw new Error("invalid_local_datetime");
  const [year, month, day] = date.split("-").map(Number);
  const [hour, minute] = time.split(":").map(Number);
  const value = new TZDate(year, month - 1, day, hour, minute, 0, KYIV);
  // Reject the spring DST gap by round-trip; for an autumn overlap, explicitly pick the earlier matching instant.
  if (!isValid(value) || format(value, "yyyy-MM-dd HH:mm", { in: inKyiv }) !== `${date} ${time}`) {
    throw new Error("invalid_local_datetime");
  }
  const earlier = subHours(value, 1, { in: inKyiv });
  return format(earlier, "yyyy-MM-dd HH:mm", { in: inKyiv }) === `${date} ${time}` ? earlier : value;
}

export function kyivLocalToUtcIso(date: string, time: string) {
  return new Date(kyivWallClock(date, time).getTime()).toISOString().replace(".000Z", "Z");
}

export function kyivDateTimeInput(isoDateTime: string) {
  const value = new TZDate(isoDateTime, KYIV);
  if (!isValid(value)) throw new Error("invalid_local_datetime");
  return { date: format(value, "yyyy-MM-dd", { in: inKyiv }), time: format(value, "HH:mm", { in: inKyiv }) };
}

export function kyivToday(now = new Date()) {
  return format(new TZDate(now, KYIV), "yyyy-MM-dd", { in: inKyiv });
}

export function kyivWeekMonday(date: string) {
  return format(startOfWeek(kyivWallClock(date), { weekStartsOn: 1, in: inKyiv }), "yyyy-MM-dd", { in: inKyiv });
}

export function addIsoDays(date: string, days: number) {
  return format(addDays(kyivWallClock(date), days, { in: inKyiv }), "yyyy-MM-dd", { in: inKyiv });
}

export function kyivDateKey(isoDateTime: string) {
  const value = new TZDate(isoDateTime, KYIV);
  if (!isValid(value)) throw new Error("invalid_local_datetime");
  return format(value, "yyyy-MM-dd", { in: inKyiv });
}
