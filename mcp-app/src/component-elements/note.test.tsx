import { fireEvent, render, screen } from "@testing-library/react";

import { vi } from "vitest";

import { Note } from "./note";

test("bolds the fact before the reason", () => {
  render(
    <Note kind="info" fact="No naming rule">
      so it goes beside.
    </Note>,
  );
  expect(screen.getByText("No naming rule").tagName).toBe("B");
  expect(screen.getByRole("note").textContent).toBe(
    "No naming rule so it goes beside.",
  );
});

test("a warning is announced", () => {
  render(<Note kind="warning">Prepared again.</Note>);
  expect(screen.getByRole("alert")).toBeTruthy();
});

test("Show why is a button that calls back", () => {
  const onShowWhy = vi.fn<() => void>();
  render(
    <Note kind="leftOut" fact="2 files left out:" onShowWhy={onShowWhy}>
      a, b.
    </Note>,
  );
  fireEvent.click(screen.getByRole("button", { name: "Show why" }));
  expect(onShowWhy).toHaveBeenCalledOnce();
});
