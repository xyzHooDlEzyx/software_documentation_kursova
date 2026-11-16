import { expect, test } from "vitest";
import { periodFor } from "./period";

test("Kyiv week remains local-date based across the autumn DST transition", () => {
  expect(periodFor("week", "2026-10-25")).toEqual({ startDate: "2026-10-19", endDate: "2026-10-26" });
});

test("three month period uses whole Kyiv calendar months and an exclusive end", () => {
  expect(periodFor("three-months", "2026-11-16")).toEqual({ startDate: "2026-09-01", endDate: "2026-12-01" });
});
