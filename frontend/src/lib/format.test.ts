import { expect, test } from "vitest";

import { EXERCISE_WORDS, plural } from "./format";

test.each([
  [1, "1 вправа"], [2, "2 вправи"], [4, "4 вправи"], [5, "5 вправ"],
  [11, "11 вправ"], [12, "12 вправ"], [21, "21 вправа"], [22, "22 вправи"], [0, "0 вправ"],
])("plural(%i)", (count, expected) => {
  expect(plural(count, EXERCISE_WORDS)).toBe(expected);
});
