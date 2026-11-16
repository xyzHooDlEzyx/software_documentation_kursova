import { expect, test } from "vitest";

import {
  addIsoDays,
  kyivDateKey,
  kyivDateTimeInput,
  kyivLocalToUtcIso,
  kyivToday,
  kyivWeekMonday,
} from "./kyivDateTime";

test("converts winter and summer Kyiv wall times to UTC", () => {
  expect(kyivLocalToUtcIso("2026-01-15", "12:00")).toBe("2026-01-15T10:00:00Z");
  expect(kyivLocalToUtcIso("2026-07-15", "12:00")).toBe("2026-07-15T09:00:00Z");
});

test("rejects the 2026 spring DST gap", () => {
  expect(() => kyivLocalToUtcIso("2026-03-29", "03:00")).toThrow("invalid_local_datetime");
  expect(() => kyivLocalToUtcIso("2026-03-29", "03:59")).toThrow("invalid_local_datetime");
});

test("chooses the earlier instant in the 2026 autumn DST overlap", () => {
  expect(kyivLocalToUtcIso("2026-10-25", "03:30")).toBe("2026-10-25T00:30:00Z");
});

test("converts ISO instants to Kyiv form fields and today", () => {
  expect(kyivDateTimeInput("2026-07-01T07:15:00Z")).toEqual({ date: "2026-07-01", time: "10:15" });
  expect(kyivToday(new Date("2026-12-31T22:30:00Z"))).toBe("2027-01-01");
});

test("buckets a late UTC slot into the next Kyiv day", () => {
  expect(kyivDateKey("2026-11-14T22:30:00Z")).toBe("2026-11-15");
});

test("finds Monday across month and year boundaries and adds calendar days", () => {
  expect(kyivWeekMonday("2026-01-01")).toBe("2025-12-29");
  expect(addIsoDays("2025-12-31", 1)).toBe("2026-01-01");
  expect(addIsoDays("2026-03-28", 2)).toBe("2026-03-30");
});

test.each([
  ["2026-02-30", "12:00"],
  ["2026-13-01", "12:00"],
  ["2026-01-01", "25:00"],
  ["2026-01-01", "12:60"],
  ["01.01.2026", "12:00"],
  ["2026-01-01", "noon"],
])("rejects invalid wall-clock input %s %s", (date, time) => {
  expect(() => kyivLocalToUtcIso(date, time)).toThrow("invalid_local_datetime");
});

test("rejects invalid date-only inputs", () => {
  expect(() => kyivWeekMonday("2026-02-30")).toThrow("invalid_local_datetime");
  expect(() => addIsoDays("invalid", 1)).toThrow("invalid_local_datetime");
  expect(() => kyivDateKey("invalid")).toThrow("invalid_local_datetime");
});
