import { fireEvent, render, screen } from "@testing-library/react";

import { PlanLines, PlanTable } from "./plan-table";

const rows = ["a", "b", "c", "d", "e"].map((id) => ({
  id,
  cells: [
    <PlanLines key="file" primary={`${id}.md`} secondary="Notes/" />,
    `${id} goes`,
  ],
}));

test("headers and cells render", () => {
  render(<PlanTable headers={["File", "Goes to"]} rows={rows} />);
  expect(screen.getAllByRole("columnheader").map((h) => h.textContent)).toEqual(
    ["File", "Goes to"],
  );
  expect(screen.getByText("a.md")).toBeTruthy();
  expect(screen.getAllByText("Notes/")).toHaveLength(5);
  expect(screen.getByText("e goes")).toBeTruthy();
});

test("a limit shows the first rows and opens the rest in place", () => {
  render(<PlanTable headers={["File", "Goes to"]} rows={rows} limit={3} />);
  expect(screen.queryByText("d.md")).toBeNull();
  fireEvent.click(screen.getByRole("button", { name: "+2 more" }));
  expect(screen.getByText("d.md")).toBeTruthy();
  expect(screen.queryByRole("button")).toBeNull();
});

test("no more line when every row fits", () => {
  render(<PlanTable headers={["File", "Goes to"]} rows={rows} limit={5} />);
  expect(screen.queryByRole("button")).toBeNull();
});

test("stacked, each cell carries its header for sight; the header row stays for screen readers", () => {
  render(<PlanTable headers={["File", "Goes to"]} rows={rows} />);
  const row = screen.getByText("a.md").closest("tr");
  const labels = row?.querySelectorAll("[data-stack-label]") ?? [];
  expect([...labels].map((l) => l.textContent)).toEqual(["File", "Goes to"]);
  expect(screen.getAllByRole("columnheader")).toHaveLength(2);
});
