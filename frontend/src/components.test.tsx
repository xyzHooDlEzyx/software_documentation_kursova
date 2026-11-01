import { fireEvent, render, screen } from "@testing-library/react";
import { expect, test, vi } from "vitest";
import type { ChangeEvent } from "react";

import { Button, Checkbox, Switch } from "./components/ui";

test("Switch onChange receives the updated hidden input checked value", () => {
  const onChange = vi.fn((event: ChangeEvent<HTMLInputElement>) => event.target.checked);
  render(<Switch id="daily-reminder" label="Нагадування" onChange={onChange} />);

  fireEvent.click(screen.getByRole("switch", { name: "Нагадування" }));

  expect(onChange).toHaveBeenCalledTimes(1);
  expect(onChange.mock.results[0]?.value).toBe(true);
});

test("Checkbox keeps its label and toggles with Space from the keyboard", () => {
  const onChange = vi.fn((event: ChangeEvent<HTMLInputElement>) => event.target.checked);
  render(<Checkbox id="weekly-summary" label="Тижневий звіт" onChange={onChange} />);

  const checkbox = screen.getByRole("checkbox", { name: "Тижневий звіт" });
  expect(checkbox).toHaveAccessibleName("Тижневий звіт");
  checkbox.focus();
  fireEvent.keyDown(checkbox, { key: " ", code: "Space", charCode: 32 });
  fireEvent.keyUp(checkbox, { key: " ", code: "Space", charCode: 32 });

  expect(checkbox).toHaveAttribute("aria-checked", "true");
  expect(onChange).toHaveBeenCalledTimes(1);
  expect(onChange.mock.results[0]?.value).toBe(true);
});

test("Button loading state disables submission and exposes its busy state", () => {
  render(<Button loading>Зберегти</Button>);

  const button = screen.getByRole("button", { name: "Зачекайте…" });
  expect(button).toBeDisabled();
  expect(button).toHaveAttribute("aria-busy", "true");
});

test("primary Button keeps foreground color and font size through class merging", () => {
  render(<Button>Продовжити</Button>);

  expect(screen.getByRole("button", { name: "Продовжити" })).toHaveClass(
    "text-primary-foreground",
    "text-sm",
  );
});
