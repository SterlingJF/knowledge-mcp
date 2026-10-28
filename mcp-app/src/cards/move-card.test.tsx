import { fireEvent, render, screen } from "@testing-library/react";

import { StaticCardHost, stubCardHost } from "@/bridge/static";
import type { ToolResult } from "@/bridge/bridge";
import { action, badge, decision, frozen, message, moves } from "@/copy/en";
import { CardView } from "./registry";
import { MoveCard, summaryRows } from "./move-card";
import { m01, m05 } from "./move-card.fixture";

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

test("summary: moves, renames, links from a real-shaped plan", () => {
  const rows = summaryRows(m01);
  expect(rows.map((r) => r.label)).toEqual([
    moves.label.moves,
    moves.label.renames,
    moves.label.links,
  ]);
  expect(rows[0].value).toBe("3 · Inbox/ → Meetings/, Decisions/, Proposals/");
  expect(rows[1].value).toBe("2");
  expect(rows[2].value).toBe("5 repaired · 4 notes");
  renderCard(m01);
  expect(screen.getByText(moves.eyebrow)).toBeTruthy();
  expect(screen.getByText(badge.waiting.needsOk)).toBeTruthy();
  expect(screen.getByText(moves.why(4))).toBeTruthy();
  expect(moveButton().disabled).toBe(false);
});

test("full view lists every move and every link repair", () => {
  renderCard(m01, "fullscreen");
  for (const m of m01.moves) expect(screen.getByText(m.path)).toBeTruthy();
  for (const l of m01.links)
    expect(screen.getAllByText(l.replacement!).length).toBeGreaterThan(0);
  expect(screen.getAllByText(/weekly-2026-43\.md/).length).toBe(2);
});

test("blockers keep Move off until each is answered", () => {
  renderCard(m05, "fullscreen");
  expect(screen.getByText(badge.waiting.needsChoice)).toBeTruthy();
  expect(moveButton().disabled).toBe(true);
  const accepts = screen.getAllByRole("button", { name: decision.accept });
  fireEvent.click(accepts[0]);
  expect(moveButton().disabled).toBe(true);
  fireEvent.click(screen.getAllByRole("button", { name: decision.drop })[1]);
  expect(moveButton().disabled).toBe(false);
});

test("inline blocked plan names the blockers and keeps Move off", () => {
  renderCard(m05);
  expect(screen.getByText(moves.blockersValue(2))).toBeTruthy();
  expect(moveButton().disabled).toBe(true);
});

test("Move sends the message with digests and answers, then freezes", () => {
  const host = renderCard(m05, "fullscreen");
  fireEvent.click(screen.getAllByRole("button", { name: decision.accept })[0]);
  fireEvent.click(screen.getAllByRole("button", { name: decision.drop })[1]);
  fireEvent.click(moveButton());
  expect(host.sent).toEqual([moves.message(3, 5)]);
  const ctx = host.contexts[0] as {
    document_moves: {
      based_on: unknown;
      blockers: Array<{ answer: string }>;
    };
  };
  expect(ctx.document_moves.based_on).toEqual(m05.based_on);
  expect(ctx.document_moves.blockers.map((b) => b.answer)).toEqual([
    "accept",
    "drop",
  ]);
  expect(screen.getByText(frozen.approved)).toBeTruthy();
  expect(screen.getByText(badge.done.approved)).toBeTruthy();
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
  expect(screen.getByText(moves.title)).toBeTruthy();
});
