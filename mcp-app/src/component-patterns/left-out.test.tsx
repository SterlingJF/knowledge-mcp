import { render, screen } from "@testing-library/react";

import { LeftOut } from "./left-out";

const files = [
  { file: "vendor-quote.xlsx", reason: "Prices a hosted build service." },
  { file: "release-calendar.md", reason: "Covers release dates." },
];

test("names the count, then each file with its reason", () => {
  render(<LeftOut files={files} />);
  expect(screen.getByText("2 files left out")).toBeTruthy();
  expect(screen.getByText("vendor-quote.xlsx")).toBeTruthy();
  expect(screen.getByText("Covers release dates.")).toBeTruthy();
  expect(screen.queryByRole("button")).toBeNull();
});

test("the count shows even at zero", () => {
  render(<LeftOut files={[]} />);
  expect(screen.getByRole("note").textContent).toBe("Nothing left out");
});
