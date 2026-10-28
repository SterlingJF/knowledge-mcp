import { fireEvent, render, screen } from "@testing-library/react";
import { vi } from "vitest";

import type { ProposalRow } from "@/contracts/proposal";

import { ChangeTable } from "./change-table";

const rows: ProposalRow[] = [
  {
    current: { label: "Title", text: "Build schedule" },
    proposed: { label: "Title", text: "Evening build retirement" },
    mark: "suggested",
    sources: [{ file: "meeting-notes.md", line_number: 15 }],
  },
  {
    proposed: { label: "Motivation", text: "7 of 9 runs" },
    mark: "conflicting",
    sources: [
      { file: "notes.md", line_number: 12 },
      { file: "notes.md", line_number: 19 },
    ],
  },
];

test("one row per Cn with mark, sources and the addition line", () => {
  render(
    <ChangeTable rows={rows} kept={new Set([1, 2])} onKeptChange={() => {}} />,
  );
  expect(screen.getByText("C1")).toBeTruthy();
  expect(screen.getByText("C2")).toBeTruthy();
  expect(screen.getByText("Suggested")).toBeTruthy();
  expect(screen.getByText("meeting-notes.md:15")).toBeTruthy();
  expect(screen.getByText("— addition")).toBeTruthy();
});

test("a second line in the same file shows as a short chip", () => {
  render(<ChangeTable rows={rows} />);
  expect(screen.getByText("notes.md:12")).toBeTruthy();
  expect(screen.getByText(":19")).toBeTruthy();
  expect(screen.getByText("vs")).toBeTruthy();
});

test("a left-out row stays, marked out", () => {
  render(
    <ChangeTable rows={rows} kept={new Set([1])} onKeptChange={() => {}} />,
  );
  const out = screen.getByText("C2").closest("[role=row]");
  expect(out?.getAttribute("data-left-out")).toBe("true");
  const cells = out?.querySelectorAll("[role=cell]") ?? [];
  expect(cells[0].className).not.toContain("line-through");
  expect(cells[1].querySelector(".line-through")).toBeTruthy();
  expect(cells[2].className).not.toContain("line-through");
  expect(
    cells[2].querySelector("[data-mark]")?.closest(".line-through"),
  ).toBeNull();
  expect(cells[2].querySelector(".line-through")?.textContent).toContain(
    "7 of 9 runs",
  );
  expect(cells[3].className).not.toContain("line-through");
  expect(out?.outerHTML).not.toContain("opacity-out");
});

test("ticking and select-all report the kept set to the parent", () => {
  const onKeptChange = vi.fn<(k: Set<number>) => void>();
  render(
    <ChangeTable rows={rows} kept={new Set([1])} onKeptChange={onKeptChange} />,
  );
  const boxes = screen.getAllByRole("checkbox");
  expect(boxes).toHaveLength(3);
  fireEvent.click(boxes[2]);
  expect([...onKeptChange.mock.calls[0][0]]).toEqual([1, 2]);
  fireEvent.click(boxes[0]);
  expect([...onKeptChange.mock.calls[1][0]]).toEqual([1, 2]);
});

test("frozen drops the boxes and keeps the numbers", () => {
  render(<ChangeTable rows={rows} />);
  expect(screen.queryAllByRole("checkbox")).toHaveLength(0);
  expect(screen.getByText("C1")).toBeTruthy();
  expect(screen.queryByText("All")).toBeNull();
});

test("the sources cell stacks its chips one per line", () => {
  render(<ChangeTable rows={rows} />);
  const stacks = screen.getAllByTestId("sources");
  expect(stacks[1].className).toContain("flex-col");
  expect(stacks[1].children).toHaveLength(2);
});

test("draft mode: no boxes, no Current column, Section and Draft headers", () => {
  render(<ChangeTable rows={rows} draft onKeptChange={() => {}} />);
  expect(screen.queryAllByRole("checkbox")).toHaveLength(0);
  expect(screen.queryByText("Current")).toBeNull();
  expect(screen.queryByText("All")).toBeNull();
  expect(screen.getByText("Section")).toBeTruthy();
  expect(screen.getByText("Draft")).toBeTruthy();
  expect(screen.getByText("Evening build retirement")).toBeTruthy();
  expect(screen.getByText("Suggested")).toBeTruthy();
  expect(document.querySelector("[data-left-out]")).toBeNull();
});

test("columns sit a group gap apart, chips in a cell a tight gap", () => {
  render(<ChangeTable rows={rows} />);
  const row = screen.getAllByTestId("sources")[1].closest("[role=row]");
  expect(row?.className).toContain("gap-x-(--km-gap-group)");
  expect(screen.getAllByTestId("sources")[1].className).toContain(
    "gap-(--km-gap-tight)",
  );
});

test("on touch, every row with a tick box is at least the target tall", () => {
  render(
    <ChangeTable rows={rows} kept={new Set([1])} onKeptChange={() => {}} />,
  );
  const [header, first] = screen.getAllByRole("row");
  expect(header.className).toContain("pointer-coarse:min-h-(--km-target)");
  expect(first.className).toContain("pointer-coarse:min-h-(--km-target)");
});
