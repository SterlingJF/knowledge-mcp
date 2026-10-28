import { fireEvent, render, screen } from "@testing-library/react";

import { LeftOut } from "./left-out";

const files = [
  { file: "vendor-quote.xlsx", reason: "Prices a hosted build service." },
  { file: "release-calendar.md", reason: "Covers release dates." },
];

test("closed shows the count and names, then opens to each reason", () => {
  render(<LeftOut files={files} />);
  expect(screen.getByRole("note").textContent).toContain(
    "2 files left out: vendor-quote.xlsx, release-calendar.md.",
  );
  expect(screen.queryByText("Covers release dates.")).toBeNull();
  fireEvent.click(screen.getByRole("button", { name: "Show why" }));
  expect(screen.getByText("Covers release dates.")).toBeTruthy();
  expect(screen.getByText("vendor-quote.xlsx")).toBeTruthy();
});

test("the count shows even at zero", () => {
  render(<LeftOut files={[]} />);
  expect(screen.getByRole("note").textContent).toBe("Nothing left out");
  expect(screen.queryByRole("button")).toBeNull();
});
