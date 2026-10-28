import { fireEvent, render, screen, within } from "@testing-library/react";

import { StaticCardHost, stubCardHost } from "@/bridge/static";
import type { ToolResult } from "@/bridge/bridge";
import { action, eyebrow, frozen, label, message } from "@/copy/en";
import type { Proposal } from "@/contracts/proposal";
import { CardView } from "./registry";
import { ProposalCard, summaryRows } from "./proposal-card";
import { e02, newDocument } from "./proposal-card.fixture";

const asResult = (p: Proposal) => p as unknown as ToolResult;

function renderCard(
  p: Proposal,
  displayMode: "inline" | "fullscreen" = "inline",
) {
  const host = stubCardHost({ result: asResult(p), displayMode });
  render(
    <StaticCardHost host={host}>
      <ProposalCard result={asResult(p)} />
    </StaticCardHost>,
  );
  return host;
}

test("summary data points come from the proposal, at most four", () => {
  const rows = summaryRows(e02);
  expect(rows.length).toBeLessThanOrEqual(4);
  expect(rows.map((r) => r.label)).toEqual([
    label.changes,
    label.evidence,
    label.needsYou,
    label.leftOut,
  ]);
  expect(rows[0].value).toBe(
    "C1 Title · C2 Motivation · C3 Status · C4 Open question",
  );
  expect(rows[1].value).toBe(
    "1 supported · 1 partly answered · 1 conflicting · 1 suggested",
  );
  expect(rows[3].value).toBe("vendor-quote.xlsx · release-calendar.md");
  renderCard(e02);
  expect(screen.getByText(eyebrow.proposedChanges)).toBeTruthy();
  expect(screen.getByText("docs/proposals/cache-proposal.md")).toBeTruthy();
  expect(screen.getByText("C3 Status")).toBeTruthy();
});

test("a new document says Proposed document and lists sections", () => {
  const rows = summaryRows(newDocument);
  expect(rows[0].label).toBe(label.sections);
  expect(rows.map((r) => r.label)).not.toContain(label.leftOut);
  renderCard(newDocument);
  expect(screen.getByText(eyebrow.proposedDocument)).toBeTruthy();
});

test("unticking C1 in full view then Save sends the rest with the digest", () => {
  const host = renderCard(e02, "fullscreen");
  const c1 = within(screen.getAllByRole("row")[1]).getByRole("checkbox");
  fireEvent.click(c1);
  fireEvent.click(screen.getByRole("button", { name: action.save("C2–C4") }));
  expect(host.sent).toEqual(["Save C2–C4 to cache-proposal.md; leave out C1"]);
  expect(host.contexts[0]).toEqual({
    proposal: {
      subject: e02.instance?.subject,
      based_on: e02.based_on,
      instance: e02.instance,
      kept: [2, 3, 4],
    },
  });
  expect(host.requested).toEqual(["inline"]);
});

test("Not now freezes the card and sends", () => {
  const host = renderCard(e02);
  fireEvent.click(screen.getByRole("button", { name: action.notNow }));
  expect(host.sent).toEqual([message.notNow]);
  expect(host.contexts[0]).toBeUndefined();
  expect(screen.getByText(frozen.notSaved)).toBeTruthy();
  expect(screen.queryByRole("button", { name: action.notNow })).toBeNull();
});

test("Save is not offered when nothing is kept", () => {
  renderCard(e02, "fullscreen");
  const selectAll = within(screen.getAllByRole("row")[0]).getByRole("checkbox");
  fireEvent.click(selectAll);
  expect(screen.queryByRole("button", { name: /^Save/ })).toBeNull();
  expect(screen.getByRole("button", { name: action.notNow })).toBeTruthy();
});

test("CardView picks the proposal card by schema", () => {
  render(
    <StaticCardHost host={stubCardHost({ result: asResult(e02) })}>
      <CardView result={asResult(e02)} />
    </StaticCardHost>,
  );
  expect(screen.getByText(e02.summary)).toBeTruthy();
});
