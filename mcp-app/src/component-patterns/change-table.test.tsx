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
  expect(cells[1].className).toContain("line-through");
  expect(cells[2].className).toContain("line-through");
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
