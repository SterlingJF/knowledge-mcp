import { fireEvent, render, screen, within } from "@testing-library/react";

import { StaticCardHost, stubCardHost } from "@/bridge/static";
import type { CardHost, ToolResult } from "@/bridge/bridge";
import {
  action,
  badge,
  change,
  eyebrow,
  frozen,
  label,
  line,
  message,
  proposal,
} from "@/copy/en";
import type { Proposal } from "@/contracts/proposal";
import { CardView } from "./registry";
import { ProposalCard, fileName, summaryRows } from "./proposal-card";
import { e02, newDocument } from "./proposal-card.fixture";

// Expected breakdowns are written plainly; the card joins with line.summaryJoin and keeps each number with its noun.
const joined = (text: string) =>
  text
    .replaceAll(" · ", line.summaryJoin)
    .replace(/(\d+) ([a-z][a-z ]*?)(?= ·|$)/g, (_, n: string, noun: string) =>
      line.counted(Number(n), noun),
    );

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
    joined("C1 Title · C2 Motivation · C3 Status · C4 Open question"),
  );
  expect(rows[1].value).toBe(
    joined("1 supported · 1 partly answered · 1 conflicting · 1 suggested"),
  );
  expect(rows[3].value).toBe(joined("vendor-quote.xlsx · release-calendar.md"));
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
  expect(rows[0].value).toBe(change.count(6));
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
  const { view } = renderCard(minimal);
  expect(screen.getByText("Fix a typo")).toBeTruthy();
  // No instance, type, reader or filing: no meta line at all.
  expect(
    view.container.querySelector("[data-slot=card-description]"),
  ).toBeNull();
  expect(
    view.container.querySelector("[data-slot=card-header]")?.textContent,
  ).not.toContain(proposal.guess);
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
    label.needsYou,
  ]);
  expect(rows[2].value).toBe(
    ["Proposals/cache-rollout.md", "no naming rule"].join(line.summaryJoin),
  );
  expect(rows[3].value).toBe(joined("Rollout owner · no source"));
  expect(rows[0].value).toBe(
    joined("C1 Motivation · C2 Alternatives · C3 Status"),
  );
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

test("meta shows the type, the reader and a guess badge", () => {
  renderCard(newDocument);
  expect(screen.getByText("Design proposal · for maintainers")).toBeTruthy();
  expect(screen.getByText(proposal.guess)).toBeTruthy();
});

test("a confirmed reader gets no guess badge, and a rule names the file", () => {
  renderCard(e02);
  expect(screen.getByText("Design proposal · for maintainers")).toBeTruthy();
  expect(screen.queryByText(proposal.guess)).toBeNull();
  const named = summaryRows({
    ...newDocument,
    filing: { path: "Proposals/x.md", naming_rule: "kebab-case title" },
  });
  expect(named[2].value).toBe(
    ["Proposals/x.md", "named by kebab-case title"].join(line.summaryJoin),
  );
});

test("more open questions add +n more, still at most four rows", () => {
  const rows = summaryRows({
    ...newDocument,
    open_questions: [
      { label: "Rollout owner", text: "?" },
      { text: "Budget" },
      { text: "Date" },
    ],
  });
  expect(rows.length).toBe(4);
  expect(rows[3].value).toBe(
    ["Rollout owner", "no source", "+2 more"].join(line.summaryJoin),
  );
});

test("D05F full view: filing note, open questions, whole-file chip", () => {
  renderCard(newDocument, "fullscreen");
  expect(screen.getByText(proposal.readerGuess)).toBeTruthy();
  expect(screen.getByText(proposal.noRuleFor("Design proposal"))).toBeTruthy();
  expect(screen.getByText(proposal.toAnswer(1))).toBeTruthy();
  expect(
    screen.getByText(/Rollout owner · no source\. It stays an open question/),
  ).toBeTruthy();
  expect(screen.getByText("vendor-quote.xlsx")).toBeTruthy();
});

test("a label-less row names its change once, with a short head", () => {
  const text = "Status: Draft. Approval is disputed.";
  const p: Proposal = {
    ...e02,
    rows: [{ proposed: { text }, mark: "conflicting", sources: [] }],
  };
  const rows = summaryRows(p);
  expect(rows[0].value).toBe("C1 Status: Draft. Approval…");
  render(<>{rows.find((r) => r.label === label.needsYou)?.value}</>);
  expect(screen.getByText("C1").tagName).toBe("B");
  expect(document.body.textContent).toBe(["C1", text].join(line.summaryJoin));
});

test("an absolute subject shows its file name, the full path on hover", () => {
  const path =
    "/Users/someone/Desktop/side_projects/knowledge-mcp-live-check/cache-proposal.md";
  const p = {
    ...e02,
    instance: { ...e02.instance, subject: path },
  } as Proposal;
  for (const mode of ["inline", "fullscreen"] as const) {
    const { view } = renderCard(p, mode);
    const chip = screen.getByText("cache-proposal.md").closest("[title]");
    expect(chip?.getAttribute("title")).toBe(path);
    expect(screen.queryByText(path)).toBeNull();
    view.unmount();
  }
});

test("a remounted frozen card shows what was kept", () => {
  const { host, view } = renderCard(e02, "fullscreen");
  fireEvent.click(rowCheckbox(1));
  fireEvent.click(screen.getByRole("button", { name: action.save("C2–C4") }));
  view.unmount();
  render(
    <StaticCardHost host={{ ...host, displayMode: "inline" }}>
      <ProposalCard result={asResult(e02)} />
    </StaticCardHost>,
  );
  expect(screen.getByText(frozen.approved)).toBeTruthy();
  expect(screen.getByText(badge.done.approved)).toBeTruthy();
  expect(document.body.textContent).toContain(
    joined("C2 Motivation · C3 Status · C4 Open question"),
  );
  expect(document.body.textContent).not.toContain("C1 Title");
});
