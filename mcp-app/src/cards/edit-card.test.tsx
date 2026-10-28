import { fireEvent, render, screen } from "@testing-library/react";

import { StaticCardHost, stubCardHost } from "@/bridge/static";
import type { ToolResult } from "@/bridge/bridge";
import { action, badge, editResult, frozen, meta } from "@/copy/en";
import { CardView } from "./registry";
import { EditCard, undoMessage, when } from "./edit-card";
import { d06, r01 } from "./edit-card.fixture";

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

test("R01 summary: saved, where, when, on whose OK, with Undo", () => {
  renderCard(r01);
  expect(screen.getAllByText(editResult.saved)).toHaveLength(2);
  expect(screen.getAllByText(badge.done.saved).length).toBeGreaterThan(0);
  expect(screen.getByText(r01.location)).toBeTruthy();
  expect(
    screen.getByText(new RegExp(`${meta.approvedByYou}$`)).textContent,
  ).toMatch(/^Recorded Oct 28, \d\d:\d\d · approved by you$/);
  expect(screen.getByRole("button", { name: action.undo })).toBeTruthy();
});

test("D06: an edit from empty text reads as created", () => {
  renderCard(d06);
  expect(screen.getAllByText(editResult.created)).toHaveLength(2);
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
  expect(screen.queryByRole("button", { name: action.undo })).toBeNull();
});

test.each([
  ["no result", null],
  ["another schema", { ...r01, schema: "knowledge-mcp/edits/2" }],
  ["a bad digest", { ...r01, before_digest: "sha256:nope" }],
  ["no location", { ...r01, location: "" }],
  ["a bad time", { ...r01, time: "yesterday" }],
  ["an unknown basis", { ...r01, allowed_by: { basis: "vibes", text: "" } }],
])("a malformed result (%s) renders nothing", (_, e) => {
  renderCard(e);
  expect(screen.queryByRole("button")).toBeNull();
  expect(screen.queryByText(editResult.saved)).toBeNull();
});

test("CardView draws the edit card for knowledge-mcp/edit/2", () => {
  renderCard(r01, true);
  expect(screen.getAllByText(badge.done.saved).length).toBeGreaterThan(0);
});
