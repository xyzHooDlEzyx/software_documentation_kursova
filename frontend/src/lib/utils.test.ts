import { expect, test } from "vitest";

import { cn } from "./utils";

test("custom font-size tokens are not merged away as text colours", () => {
  expect(cn("text-caption", "text-muted-foreground")).toBe("text-caption text-muted-foreground");
  expect(cn("text-small", "text-caption")).toBe("text-caption");
  expect(cn("text-foreground", "text-muted-foreground")).toBe("text-muted-foreground");
});
