import { fireEvent, render, screen } from "@testing-library/react";

import { PlanLines, PlanTable } from "./plan-table";

const rows = ["a", "b", "c", "d", "e"].map((id) => ({
  id,
  cells: [<PlanLines primary={`${id}.md`} secondary="Notes/" />, `${id} goes`],
}));

test("headers and cells render", () => {
  render(
    <PlanTable headers={["File", "Goes to"]} columns={[40, 60]} rows={rows} />,
  );
  expect(screen.getAllByRole("columnheader").map((h) => h.textContent)).toEqual(
    ["File", "Goes to"],
  );
  expect(screen.getByText("a.md")).toBeTruthy();
  expect(screen.getAllByText("Notes/")).toHaveLength(5);
  expect(screen.getByText("e goes")).toBeTruthy();
});

test("a limit shows the first rows and opens the rest in place", () => {
  render(
    <PlanTable
      headers={["File", "Goes to"]}
      columns={[40, 60]}
      rows={rows}
      limit={3}
    />,
  );
  expect(screen.queryByText("d.md")).toBeNull();
  fireEvent.click(screen.getByRole("button", { name: "+2 more" }));
  expect(screen.getByText("d.md")).toBeTruthy();
  expect(screen.queryByRole("button")).toBeNull();
});

test("no more line when every row fits", () => {
  render(
    <PlanTable
      headers={["File", "Goes to"]}
      columns={[40, 60]}
      rows={rows}
      limit={5}
    />,
  );
  expect(screen.queryByRole("button")).toBeNull();
});

test("rows stack under 560px with each cell's header label", () => {
  render(
    <PlanTable headers={["File", "Goes to"]} columns={[40, 60]} rows={rows} />,
  );
  const row = screen.getByText("a.md").closest("[role=row]");
  expect(row?.className).toContain("@max-[560px]:grid-cols-1");
  const labels = row?.querySelectorAll("[data-stack-label]") ?? [];
  expect([...labels].map((l) => l.textContent)).toEqual(["File", "Goes to"]);
  expect(
    (screen.getByRole("table") as HTMLElement).style.getPropertyValue(
      "--plan-cols",
    ),
  ).toBe("minmax(0,40fr) minmax(0,60fr)");
});

test("columns sit a group gap apart, rows a row gap", () => {
  render(
    <PlanTable headers={["File", "Goes to"]} columns={[40, 60]} rows={rows} />,
  );
  const row = screen.getByText("a.md").closest("[role=row]");
  expect(row?.className).toContain("gap-x-km-gap-group");
  expect(row?.className).toContain("py-km-gap-row");
});
