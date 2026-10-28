import { fireEvent, render, screen, within } from "@testing-library/react";

import { StaticCardHost, stubCardHost } from "@/bridge/static";
import type { CardHost, ToolResult } from "@/bridge/bridge";
import {
  action,
  badge,
  eyebrow,
  frozen,
  label,
  line,
  message,
} from "@/copy/en";
import type { Proposal } from "@/contracts/proposal";
import { CardView } from "./registry";
import { ProposalCard, fileName, summaryRows } from "./proposal-card";
import { e02, newDocument } from "./proposal-card.fixture";

const asResult = (p: unknown) => p as ToolResult;

function renderCard(
  p: unknown,
  displayMode: "inline" | "fullscreen" = "inline",
) {
  const host = stubCardHost({ result: asResult(p), displayMode });
  const view = render(
    <StaticCardHost host={host}>
      <ProposalCard result={asResult(p)} />
    </StaticCardHost>,
  );
  const switchTo = (mode: "inline" | "fullscreen") => {
    const next: CardHost = { ...host, displayMode: mode };
    view.rerender(
      <StaticCardHost host={next}>
        <ProposalCard result={asResult(p)} />
      </StaticCardHost>,
    );
  };
  return { host, view, switchTo };
}

const rowCheckbox = (n: number) =>
  within(screen.getAllByRole("row")[n]).getByRole("checkbox");

test("summary data points come from the proposal, at most four", () => {
  const rows = summaryRows(e02);
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
  expect(screen.getByText("cache-proposal.md")).toBeTruthy();
  expect(screen.getByText("C3 Status")).toBeTruthy();
});

test("more than four changes are counted, extra conflicts summed", () => {
  const conflicting = { ...e02.rows[2] };
  const many: Proposal = {
    ...e02,
    rows: [...e02.rows, conflicting, conflicting],
  };
  const rows = summaryRows(many);
  expect(rows.length).toBeLessThanOrEqual(4);
  expect(rows[0].value).toBe("6 changes");
  render(<>{rows[2].value}</>);
  expect(
    screen.getByText(new RegExp(line.andMore(2).replace("+", "\\+"))),
  ).toBeTruthy();
});

test("a minimal proposal draws with only its changes", () => {
  const minimal = {
    schema: "knowledge-mcp/proposal/1",
    summary: "Fix a typo",
    rows: [
      {
        current: { text: "teh" },
        proposed: { text: "the" },
        sources: [],
      },
    ],
    card: "",
  };
  renderCard(minimal);
  expect(screen.getByText("Fix a typo")).toBeTruthy();
  expect(screen.getByText(line.waitsBecause(line.theDocument))).toBeTruthy();
  expect(fileName({ ...e02, instance: undefined })).toBe(line.theDocument);
  expect(
    fileName({
      ...e02,
      instance: { ...newDocument.instance!, subject: "a/b.md" },
    }),
  ).toBe("b.md");
});

test("a malformed result renders nothing", () => {
  const { view } = renderCard({ schema: "knowledge-mcp/proposal/1", rows: 3 });
  expect(view.container.innerHTML).toBe("");
});

test("new document: sections, saved as, Create the file, no why line", () => {
  const rows = summaryRows(newDocument);
  expect(rows.map((r) => r.label)).toEqual([
    label.sections,
    label.evidence,
    label.savedAs,
  ]);
  expect(rows[0].value).toBe("C1 Motivation · C2 Alternatives · C3 Status");
  const { host } = renderCard(newDocument);
  expect(screen.getByText(eyebrow.proposedDocument)).toBeTruthy();
  expect(screen.queryByText(/Waits for you/)).toBeNull();
  fireEvent.click(screen.getByRole("button", { name: action.createFile }));
  expect(host.sent).toEqual([
    message.create("Proposals/cache-rollout.md", "C1–C3"),
  ]);
});

test("unticking C1 in full view then Save sends the rest with the digest", () => {
  const { host } = renderCard(e02, "fullscreen");
  fireEvent.click(rowCheckbox(1));
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

test("the kept set survives switching inline and back", () => {
  const { switchTo } = renderCard(e02, "fullscreen");
  fireEvent.click(rowCheckbox(1));
  switchTo("inline");
  expect(
    screen.getByRole("button", { name: action.save("C2–C4") }),
  ).toBeTruthy();
  switchTo("fullscreen");
  expect(
    screen.getByRole("button", { name: action.save("C2–C4") }),
  ).toBeTruthy();
  expect(screen.getAllByRole("row")[1].getAttribute("data-left-out")).toBe(
    "true",
  );
});

test("Save freezes with the approved badge and Change eyebrow", () => {
  renderCard(e02);
  fireEvent.click(screen.getByRole("button", { name: action.save("C1–C4") }));
  expect(screen.getByText(frozen.approved)).toBeTruthy();
  expect(screen.getByText(badge.done.approved)).toBeTruthy();
  expect(screen.getByText(eyebrow.change)).toBeTruthy();
});

test("Not now freezes the card and sends", () => {
  const { host } = renderCard(e02);
  fireEvent.click(screen.getByRole("button", { name: action.notNow }));
  expect(host.sent).toEqual([message.notNow]);
  expect(host.contexts[0]).toBeUndefined();
  expect(screen.getByText(frozen.notSaved)).toBeTruthy();
  expect(screen.getByText(badge.neutral.notSaved)).toBeTruthy();
  expect(screen.queryByRole("button", { name: action.notNow })).toBeNull();
});

test("Save is disabled when nothing is kept", () => {
  const { host } = renderCard(e02, "fullscreen");
  fireEvent.click(rowCheckbox(0));
  const save = screen.getByRole("button", { name: /^Save/ });
  expect((save as HTMLButtonElement).disabled).toBe(true);
  fireEvent.click(save);
  expect(host.sent).toEqual([]);
});

test("CardView picks the proposal card by schema", () => {
  render(
    <StaticCardHost host={stubCardHost({ result: asResult(e02) })}>
      <CardView result={asResult(e02)} />
    </StaticCardHost>,
  );
  expect(screen.getByText(e02.summary)).toBeTruthy();
});

test("a younger instance starts over with every change kept", () => {
  const { host, view } = renderCard(e02, "fullscreen");
  fireEvent.click(rowCheckbox(1));
  expect(
    screen.getByRole("button", { name: action.save("C2–C4") }),
  ).toBeTruthy();
  const younger = { ...e02, instance: { ...e02.instance, seq: 9 } };
  view.rerender(
    <StaticCardHost host={{ ...host, result: asResult(younger) }}>
      <ProposalCard result={asResult(younger)} />
    </StaticCardHost>,
  );
  expect(
    screen.getByRole("button", { name: action.save("C1–C4") }),
  ).toBeTruthy();
});

test("the full view of a minimal proposal with nothing left out has no LeftOut", () => {
  renderCard(
    {
      schema: "knowledge-mcp/proposal/1",
      summary: "Fix a typo",
      rows: [
        { current: { text: "teh" }, proposed: { text: "the" }, sources: [] },
      ],
      left_out: [],
      card: "",
    },
    "fullscreen",
  );
  expect(screen.getByText("Fix a typo")).toBeTruthy();
  expect(screen.queryByText(line.leftOut(0))).toBeNull();
});
