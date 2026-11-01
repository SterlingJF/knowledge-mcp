import { fireEvent, render, screen } from "@testing-library/react";

import { StaticCardHost, stubCardHost } from "@/bridge/static";
import type { ToolResult } from "@/bridge/bridge";
import { action, badge, editResult, eyebrow, frozen, meta } from "@/copy/en";
import { CardView } from "./registry";
import { EditCard, undoMessage, when } from "./edit-card";
import { d06, long, r01, r03 } from "./edit-card.fixture";

const asResult = (e: unknown) => e as ToolResult;

function renderCard(e: unknown, viaRegistry = false) {
  const host = stubCardHost({ result: asResult(e) });
  render(
    <StaticCardHost host={host}>
      {viaRegistry ? (
        <CardView result={asResult(e)} />
      ) : (
        <EditCard result={asResult(e)} />
      )}
    </StaticCardHost>,
  );
  return host;
}

test("formats the recorded time terse", () => {
  expect(when(r01.time, "UTC")).toEqual({
    full: "Oct 28, 09:41",
    time: "09:41",
  });
  expect(undoMessage(r01, "UTC")).toBe(
    "Undo the 09:41 edit to cache-proposal.md",
  );
});

test("R01 summary: change, title with count, when and whose OK, with Undo", () => {
  renderCard(r01);
  expect(screen.getByText(eyebrow.change)).toBeTruthy();
  expect(screen.getByText(badge.done.saved)).toBeTruthy();
  expect(screen.getByText("cache-proposal.md · 4 changes")).toBeTruthy();
  expect(
    screen.getByText(new RegExp(`${meta.approvedByYou}$`)).textContent,
  ).toMatch(
    new RegExp(
      `^Recorded Oct 28, \\d\\d:\\d\\d${meta.join}${meta.approvedByYou}$`,
    ),
  );
  expect(screen.getByRole("button", { name: action.undo })).toBeTruthy();
});

test("without changes the title is the file name alone", () => {
  renderCard({ ...r01, changes: undefined });
  expect(screen.getByText("cache-proposal.md")).toBeTruthy();
});

test("D06: a created file reads Document, Created", () => {
  renderCard(d06);
  expect(screen.getByText(editResult.document)).toBeTruthy();
  expect(screen.getByText(badge.done.created)).toBeTruthy();
  expect(screen.getByText("Proposals/cache-rollout.md")).toBeTruthy();
  expect(
    screen.getByText(new RegExp(`${meta.approvedByYou}$`)).textContent,
  ).toMatch(/^Recorded /);
  expect(screen.getAllByRole("button").map((b) => b.textContent)).toEqual([
    action.undo,
  ]);
});

test("an empty before digest alone is not created", () => {
  renderCard({ ...d06, created: undefined });
  expect(screen.getByText(badge.done.saved)).toBeTruthy();
});

test("R03: an undo reads Change, Undone, undoes the earlier edit's time, no buttons", () => {
  renderCard(r03);
  expect(screen.getByText(eyebrow.change)).toBeTruthy();
  expect(screen.getByText(badge.done.undone)).toBeTruthy();
  const undone = editResult.undoes(when(r01.time).time);
  expect(screen.getByText(new RegExp(`${undone}$`)).textContent).toMatch(
    new RegExp(`^Recorded Oct 28, \\d\\d:\\d\\d${meta.join}${undone}$`),
  );
  expect(screen.queryAllByRole("button")).toHaveLength(0);
});

test("R02: Show the change opens the diff without sending or freezing, then hides it", () => {
  const host = renderCard(r01);
  const show = screen.getByRole("button", { name: action.showChange });
  expect(show.getAttribute("aria-expanded")).toBe("false");
  expect(screen.queryByText("Title: Evening build retirement")).toBeNull();
  fireEvent.click(show);
  expect(
    screen.getByText("Title: Evening build retirement").closest("ins")?.tagName,
  ).toBe("INS");
  expect(
    screen.getByText("Title: Build schedule and cache rollout").closest("del")
      ?.tagName,
  ).toBe("DEL");
  const hide = screen.getByRole("button", { name: action.hideChange });
  const panel = document.getElementById(
    hide.getAttribute("aria-controls") ?? "",
  );
  expect(panel?.textContent).toContain("Evening build retirement");
  expect(host.sent).toEqual([]);
  expect(screen.queryByText(frozen.undoRequested)).toBeNull();
  expect(screen.getByRole("button", { name: action.undo })).toBeTruthy();
  fireEvent.click(hide);
  expect(screen.queryByText("Title: Evening build retirement")).toBeNull();
});

test("a long diff counts the lines it leaves out", () => {
  renderCard(long);
  fireEvent.click(screen.getByRole("button", { name: action.showChange }));
  expect(screen.getByText(editResult.moreLines(5))).toBeTruthy();
});

test("no changes, no disclosure", () => {
  renderCard({ ...r01, changes: undefined });
  expect(screen.queryByRole("button", { name: action.showChange })).toBeNull();
});

test("an instruction-allowed edit says so instead of approved by you", () => {
  renderCard({
    ...r01,
    allowed_by: { basis: "instruction", text: "AGENTS.md" },
  });
  expect(
    screen.getByText(new RegExp(editResult.allowedByInstruction)),
  ).toBeTruthy();
});

test("R03: Undo sends its message with the edit's id and digests, then freezes", () => {
  const host = renderCard(r01);
  const undo = screen.getByRole("button", { name: action.undo });
  fireEvent.click(undo);
  fireEvent.click(undo);
  expect(host.sent).toEqual([undoMessage(r01)]);
  expect(host.contexts).toEqual([
    {
      edit: {
        id: r01.id,
        location: r01.location,
        time: r01.time,
        before_digest: r01.before_digest,
        after_digest: r01.after_digest,
      },
    },
  ]);
  expect(screen.getByText(frozen.undoRequested)).toBeTruthy();
  expect(screen.getByText(badge.neutral.undoRequested)).toBeTruthy();
  expect(screen.queryByText(badge.done.saved)).toBeNull();
  expect(screen.queryByRole("button", { name: action.undo })).toBeNull();
});

test.each([
  ["no result", null],
  ["another schema", { ...r01, schema: "knowledge-mcp/edits/2" }],
  ["a bad digest", { ...r01, before_digest: "sha256:nope" }],
  ["no location", { ...r01, location: "" }],
  ["a bad time", { ...r01, time: "yesterday" }],
  ["bad changes", { ...r01, changes: { hunks: 1, lines: "x", more: 0 } }],
  [
    "an undoes time that is not a string",
    { ...r01, undoes: { id: r01.id, time: 0 } },
  ],
  ["an old undoes id", { ...r01, undoes: r01.id }],
  ["an unknown basis", { ...r01, allowed_by: { basis: "vibes", text: "" } }],
])("a malformed result (%s) renders nothing", (_, e) => {
  renderCard(e);
  expect(screen.queryByRole("button")).toBeNull();
  expect(screen.queryByText(badge.done.saved)).toBeNull();
});

test("CardView draws the edit card for knowledge-mcp/edit/2", () => {
  renderCard(r01, true);
  expect(screen.getByText(badge.done.saved)).toBeTruthy();
});
