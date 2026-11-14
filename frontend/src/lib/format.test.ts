import { expect, test } from "vitest";

import { EXERCISE_WORDS, formatDate, formatDateTime, formatTime, formatWeekday, plural } from "./format";

test("formats Kyiv dates and times independently of the machine zone", () => {
  expect(formatDate("2026-11-14")).toBe("14.11.2026");
  expect(formatDateTime("2026-11-14T22:30:00Z")).toBe("15.11.2026, 00:30");
  expect(formatTime("2026-07-01T21:15:00Z")).toBe("00:15");
  expect(formatWeekday("2026-11-16", "short")).toBe("Пн");
  expect(formatWeekday("2026-11-16", "long")).toBe("Понеділок");
});

test.each([
  [1, "1 вправа"], [2, "2 вправи"], [4, "4 вправи"], [5, "5 вправ"],
  [11, "11 вправ"], [12, "12 вправ"], [21, "21 вправа"], [22, "22 вправи"], [0, "0 вправ"],
])("plural(%i)", (count, expected) => {
  expect(plural(count, EXERCISE_WORDS)).toBe(expected);
});
