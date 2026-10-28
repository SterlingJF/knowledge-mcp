import { fireEvent, render, screen } from "@testing-library/react";
import { vi } from "vitest";

import { countAccepted, DecisionRows } from "./decision-rows";

const rows = [
  {
    id: "a",
    name: "Decision record",
    cells: ["Decision record", "Decisions/"],
  },
  {
    id: "b",
    name: "Design proposal",
    cells: ["Design proposal", "Proposals/"],
    decided: { tone: "neutral" as const, label: "Not saved" },
  },
];

test("undecided rows offer a choice; decided rows show a badge instead", () => {
  const onChoiceChange = vi.fn<(id: string, v: string) => void>();
  render(
    <DecisionRows
      headers={["Type", "Folder"]}
      rows={rows}
      choices={{}}
      onChoiceChange={onChoiceChange}
    />,
  );
  expect(screen.getAllByRole("button", { name: "Accept" })).toHaveLength(1);
  expect(screen.getByText("Not saved")).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "Accept" }));
  expect(onChoiceChange).toHaveBeenCalledWith("a", "accept");
});

test("apply or keep refused", () => {
  render(
    <DecisionRows
      headers={["Type"]}
      rows={[rows[0]]}
      kind="applyKeepRefused"
      choices={{ a: "apply" }}
      onChoiceChange={() => {}}
    />,
  );
  expect(screen.getByRole("button", { name: "Keep refused" })).toBeTruthy();
  expect(
    screen.getByRole("button", { name: "Apply" }).getAttribute("aria-pressed"),
  ).toBe("true");
});

test("counts accepted and applied rows", () => {
  expect(countAccepted({ a: "accept", b: "drop", c: "apply", d: null })).toBe(
    2,
  );
});
