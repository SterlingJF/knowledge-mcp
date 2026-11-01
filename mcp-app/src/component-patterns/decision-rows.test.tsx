import { fireEvent, render, screen } from "@testing-library/react";
import { vi } from "vitest";

import { badge } from "@/copy/en";

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
    decided: { tone: "neutral" as const, label: badge.neutral.dropped },
  },
];

test("undecided rows offer a choice; decided rows show a badge instead", () => {
  const onChoiceChange = vi.fn<(id: string, v: string | null) => void>();
  render(
    <DecisionRows
      headers={["Type", "Folder"]}
      rows={rows}
      choices={{}}
      onChoiceChange={onChoiceChange}
    />,
  );
  expect(screen.getAllByRole("radio", { name: "Accept" })).toHaveLength(1);
  expect(screen.getByText("Dropped")).toBeTruthy();
  fireEvent.click(screen.getByRole("radio", { name: "Accept" }));
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
  expect(screen.getByRole("radio", { name: "Keep refused" })).toBeTruthy();
  expect(
    screen.getByRole("radio", { name: "Apply" }).getAttribute("aria-checked"),
  ).toBe("true");
});

test("counts accepted and applied rows", () => {
  expect(countAccepted({ a: "accept", b: "drop", c: "apply", d: null })).toBe(
    2,
  );
});

test("a row brings its own options: one is a tick box, five stack", () => {
  const onChoiceChange = vi.fn<(id: string, v: string | null) => void>();
  render(
    <DecisionRows
      headers={["Blocker"]}
      rows={[
        {
          id: "s",
          name: "scan",
          cells: ["scan-0412.md"],
          options: [{ value: "skip", label: "Skip this file" }],
        },
        {
          id: "l",
          name: "link",
          cells: ["[[retire-evening]]"],
          options: ["a", "b", "c", "d", "e"].map((v) => ({
            value: v,
            label: v,
          })),
          value: "c",
        },
      ]}
      onChoiceChange={onChoiceChange}
    />,
  );
  fireEvent.click(screen.getByRole("checkbox", { name: "Skip this file" }));
  expect(onChoiceChange).toHaveBeenCalledWith("s", "skip");
  expect(
    screen
      .getByRole("radiogroup", { name: "link" })
      .getAttribute("data-layout"),
  ).toBe("stacked");
  expect(
    screen.getByRole("radio", { name: "c" }).getAttribute("aria-checked"),
  ).toBe("true");
});

test("a one-option row is a tick box that sets and clears the value", () => {
  const onChoiceChange = vi.fn<(id: string, v: string | null) => void>();
  const row = (value: string | null) => ({
    id: "s",
    name: "scan",
    cells: ["scan-0412.md"],
    options: [{ value: "skip", label: "Skip this file" }],
    value,
  });
  const { rerender } = render(
    <DecisionRows
      headers={["Blocker"]}
      rows={[row(null)]}
      onChoiceChange={onChoiceChange}
    />,
  );
  expect(screen.queryByRole("radiogroup")).toBeNull();
  fireEvent.click(screen.getByRole("checkbox", { name: "Skip this file" }));
  expect(onChoiceChange).toHaveBeenLastCalledWith("s", "skip");
  rerender(
    <DecisionRows
      headers={["Blocker"]}
      rows={[row("skip")]}
      onChoiceChange={onChoiceChange}
    />,
  );
  fireEvent.click(screen.getByRole("checkbox", { name: "Skip this file" }));
  expect(onChoiceChange).toHaveBeenLastCalledWith("s", null);
});

test("narrow layout marks the title, detail and hidden cells", () => {
  render(
    <DecisionRows
      headers={["Type", "Folder", "Example", "Choice"]}
      rows={[
        {
          id: "a",
          name: "a",
          cells: ["Decision record", "Decisions/", "x.md"],
        },
      ]}
      onChoiceChange={() => {}}
    />,
  );
  expect(screen.getByText("Decision record").className).toContain(
    "@max-[560px]:font-semibold",
  );
  expect(screen.getByText("Decisions/").className).toContain(
    "@max-[560px]:hidden",
  );
  expect(screen.getByText("x.md").className).toContain(
    "@max-[560px]:text-secondary",
  );
  expect(screen.getByText("Choice").tagName).toBe("TH");
});

test("move blockers: no title, nothing hidden, choice at the start", () => {
  render(
    <DecisionRows
      headers={["Problem", "Your choice"]}
      rows={[
        {
          id: "a",
          name: "a",
          cells: ["a.md already exists"],
          options: [{ value: "s", label: "Skip" }],
        },
      ]}
      narrow={{}}
      align="start"
      onChoiceChange={() => {}}
    />,
  );
  const cell = screen.getByText("a.md already exists");
  expect(cell.className).not.toContain("@max-[560px]:font-semibold");
  expect(cell.className).not.toContain("hidden");
  expect(screen.getByText("Your choice").className).not.toContain("text-right");
});

test("a row with no options asks for an answer in chat and stays unanswered", () => {
  const onChoiceChange = vi.fn<(id: string, v: string | null) => void>();
  render(
    <DecisionRows
      headers={["Problem", "Your choice"]}
      rows={[
        {
          id: "x",
          name: "x",
          cells: ["scan-0412.md has no type"],
          options: [],
        },
      ]}
      align="start"
      onChoiceChange={onChoiceChange}
    />,
  );
  expect(screen.getByText("Answer in chat")).toBeTruthy();
  expect(screen.queryByRole("button")).toBeNull();
  expect(screen.queryByRole("checkbox")).toBeNull();
  expect(document.querySelector("[data-tone]")).toBeNull();
  expect(countAccepted({ x: null })).toBe(0);
});
