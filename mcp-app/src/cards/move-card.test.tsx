import { fireEvent, render, screen } from "@testing-library/react";

import { StaticCardHost, stubCardHost } from "@/bridge/static";
import type { ToolResult } from "@/bridge/bridge";
import { action, badge, frozen, label, line, message, moves } from "@/copy/en";
import { CardView } from "./registry";
import { MoveCard, summaryRows } from "./move-card";
import { m01, m05, m05Link, m05None } from "./move-card.fixture";

const asResult = (p: unknown) => p as ToolResult;

function renderCard(
  p: unknown,
  displayMode: "inline" | "fullscreen" = "inline",
) {
  const host = stubCardHost({ result: asResult(p), displayMode });
  render(
    <StaticCardHost host={host}>
      <MoveCard result={asResult(p)} />
    </StaticCardHost>,
  );
  return host;
}

const moveButton = () =>
  screen.getByRole("button", { name: action.move(3) }) as HTMLButtonElement;

test("summary: moves, renames with rule, links, stays", () => {
  const rows = summaryRows(m01);
  expect(rows.map((r) => r.label)).toEqual([
    moves.label.moves,
    moves.label.renames,
    moves.label.links,
    moves.label.stays,
  ]);
  expect(rows[0].value).toBe("3 · Inbox → Meetings/, Decisions/, Proposals/");
  expect(rows[1].value).toBe("2 · date + title");
  expect(rows[2].value).toBe("5 repaired · 4 notes");
  expect(rows[3].value).toBe("scan-0412.md · no document type");
  renderCard(m01);
  expect(screen.getByText("File the new files")).toBeTruthy();
  expect(screen.getByText(moves.eyebrow)).toBeTruthy();
  expect(screen.getByText("Inbox")).toBeTruthy();
  expect(
    screen.getByText(line.counted(4, moves.newFiles), { normalizer: (t) => t }),
  ).toBeTruthy();
  expect(screen.getByText(badge.waiting.needsOk)).toBeTruthy();
  expect(screen.getByText(moves.why(4))).toBeTruthy();
  expect(moveButton().disabled).toBe(false);
});

test("without a summary the fixed title shows", () => {
  renderCard({ ...m01, summary: undefined });
  expect(screen.getByText(moves.title)).toBeTruthy();
});

test("blocked summary shows Needs you in place of Stays", () => {
  const rows = summaryRows(m05);
  expect(rows.map((r) => r.label)).toEqual([
    moves.label.moves,
    moves.label.renames,
    moves.label.links,
    label.needsYou,
  ]);
  renderCard(m05);
  expect(screen.getByText(moves.blockersValue(2))).toBeTruthy();
  expect(moveButton().disabled).toBe(true);
});

test("full view: moves tab, stays note, links tab with +N more", () => {
  renderCard(m01, "fullscreen");
  expect(
    screen.getByRole("table").textContent?.replace(/\u2060|\u00ad/g, ""),
  ).toContain(moves.as("2026-10-27 build review.md"));
  expect(screen.getByText(moves.staysFact(1))).toBeTruthy();
  fireEvent.click(
    screen.getByRole("tab", { name: label.withCount(moves.label.links, 5) }),
  );
  expect(screen.getByText(line.andMore(2))).toBeTruthy();
  fireEvent.click(screen.getByText(line.andMore(2)));
  expect(screen.getAllByText(/^\[\[/).length).toBe(5);
});

test("blocker choices come from the plan; Move waits for each answer", () => {
  renderCard(m05Link, "fullscreen");
  expect(screen.getByText(badge.waiting.needsChoice)).toBeTruthy();
  expect(moveButton().disabled).toBe(true);
  fireEvent.click(
    screen.getByRole("radio", {
      name: moves.linkTo("Proposals/timings-notes"),
    }),
  );
  expect(moveButton().disabled).toBe(false);
});

test("a single skip_move blocker is a tick box; answering both enables Move", () => {
  const host = renderCard(m05, "fullscreen");
  expect(moveButton().disabled).toBe(true);
  fireEvent.click(screen.getByRole("checkbox", { name: moves.skipFile }));
  expect(moveButton().disabled).toBe(true);
  fireEvent.click(
    screen.getByRole("radio", {
      name: moves.linkTo("Proposals/cache-proposal"),
    }),
  );
  expect(moveButton().disabled).toBe(false);
  fireEvent.click(moveButton());
  const ctx = host.contexts[0] as {
    document_moves: { blockers: Array<{ answer: unknown }> };
  };
  expect(ctx.document_moves.blockers.map((b) => b.answer)).toEqual([
    { action: "skip_move", path: "Inbox/retire-evening.md" },
    { action: "bind_link", path: "Proposals/cache-proposal.md" },
  ]);
});

test("a blocker with no choices keeps Move off and points to chat", () => {
  renderCard(m05None, "fullscreen");
  expect(screen.queryByRole("checkbox")).toBeNull();
  expect(screen.getByText(moves.whyBlocked)).toBeTruthy();
  expect(moveButton().disabled).toBe(true);
});

test("Move sends the message with digests and the chosen binding, then freezes", () => {
  const host = renderCard(m05Link, "fullscreen");
  fireEvent.click(
    screen.getByRole("radio", {
      name: moves.linkTo("Proposals/timings-notes"),
    }),
  );
  fireEvent.click(moveButton());
  expect(host.sent).toEqual([moves.message(3, 5)]);
  const ctx = host.contexts[0] as {
    document_moves: { based_on: unknown; blockers: Array<{ answer: unknown }> };
  };
  expect(ctx.document_moves.based_on).toEqual(m05.based_on);
  expect(ctx.document_moves.blockers[0].answer).toEqual({
    action: "bind_link",
    path: "Proposals/timings-notes.md",
  });
  expect(screen.getByText(frozen.approved)).toBeTruthy();
  expect(host.requested).toEqual(["inline"]);
});

test("Not now sends the not-now message and freezes", () => {
  const host = renderCard(m01);
  fireEvent.click(screen.getByRole("button", { name: action.notNow }));
  expect(host.sent).toEqual([message.notNow]);
  expect(screen.getByText(frozen.notMoved)).toBeTruthy();
  expect(screen.getByText(badge.neutral.notMoved)).toBeTruthy();
});

test("a malformed result renders nothing", () => {
  for (const bad of [
    { schema: "knowledge-mcp/document-moves/1" },
    { ...m01, moves: [{ path: 3 }] },
    { ...m01, status: "texts_needed" },
  ]) {
    const { container } = render(
      <StaticCardHost host={stubCardHost({ result: asResult(bad) })}>
        <MoveCard result={asResult(bad)} />
      </StaticCardHost>,
    );
    expect(container.innerHTML).toBe("");
  }
});

test("CardView picks the move card by schema", () => {
  render(
    <StaticCardHost host={stubCardHost({ result: asResult(m01) })}>
      <CardView result={asResult(m01)} />
    </StaticCardHost>,
  );
  expect(screen.getByText("File the new files")).toBeTruthy();
});
