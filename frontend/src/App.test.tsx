import { render, screen } from "@testing-library/react";
import { expect, test } from "vitest";

import App from "./App";

test("renders the Phase 0 application shell", () => {
  render(<App />);
  expect(screen.getByRole("heading", { name: "Фітнес-трекер" })).toBeInTheDocument();
});
