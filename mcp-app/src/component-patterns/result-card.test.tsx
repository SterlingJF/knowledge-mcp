import { fireEvent, render, screen } from "@testing-library/react";
import { vi } from "vitest";

import { action, badge, frozen } from "@/copy/en";
import type { CardLifecycle } from "./card-lifecycle";
import { ResultCard } from "./result-card";

function lifecycle(): CardLifecycle {
  return {
    state: "live",
    frozenLine: undefined,
    press: vi.fn<CardLifecycle["press"]>(),
  };
}

test("result: done badge, recorded when and by whom, Undo first", () => {
  const life = lifecycle();
  render(
    <ResultCard
      kind="result"
      eyebrow="Edit"
      title="cache-proposal.md"
      badgeLabel={badge.done.saved}
      when="Oct 28, 09:41"
      undoMessage="Undo edit 12"
      secondary={{
        label: "Open",
        message: "Open edit 12",
        frozenLine: frozen.approved,
      }}
      lifecycle={life}
    />,
  );
  expect(
    screen.getByText(badge.done.saved).closest("[data-tone]"),
  ).toHaveProperty("dataset.tone", "done");
  expect(
    screen.getByText("Recorded Oct 28, 09:41 · approved by you"),
  ).toBeTruthy();
  const buttons = screen.getAllByRole("button");
  expect(buttons.map((b) => b.textContent)).toEqual([action.undo, "Open"]);
  fireEvent.click(buttons[0]!);
  expect(life.press).toHaveBeenCalledWith({
    label: action.undo,
    message: "Undo edit 12",
    frozenLine: frozen.undoRequested,
    variant: "secondary",
    icon: expect.anything(),
  });
});

test("refusal: refused badge, warning note, one next step", () => {
  render(
    <ResultCard
      kind="refusal"
      eyebrow="Edit"
      title="cache-proposal.md"
      badgeLabel={badge.refused.cantUndo}
      reason="The file changed after the edit."
      nextStep={{
        label: action.prepareAgain,
        message: "Prepare again",
        frozenLine: frozen.notSaved,
      }}
      lifecycle={lifecycle()}
    />,
  );
  expect(
    screen.getByText(badge.refused.cantUndo).closest("[data-tone]"),
  ).toHaveProperty("dataset.tone", "refused");
  expect(screen.getByRole("alert").textContent).toBe(
    "The file changed after the edit. Nothing was changed.",
  );
  expect(screen.getAllByRole("button")).toHaveLength(1);
});

test("result: the disclosure toggles the change without sending or freezing", () => {
  const life = lifecycle();
  const onToggle = vi.fn<() => void>();
  render(
    <ResultCard
      kind="result"
      eyebrow="Change"
      title="cache-proposal.md · 4 changes"
      badgeLabel={badge.done.saved}
      when="Oct 28, 09:41"
      undoMessage="Undo edit 12"
      disclosure={{
        label: action.hideChange,
        expanded: true,
        onToggle,
        controls: "diff-12",
      }}
      lifecycle={life}
    >
      <div id="diff-12">the diff</div>
    </ResultCard>,
  );
  const buttons = screen.getAllByRole("button");
  expect(buttons.map((b) => b.textContent)).toEqual([
    action.undo,
    action.hideChange,
  ]);
  fireEvent.click(buttons[1]!);
  expect(onToggle).toHaveBeenCalledOnce();
  expect(life.press).not.toHaveBeenCalled();
  expect(buttons[1]!.getAttribute("aria-expanded")).toBe("true");
  expect(document.getElementById("diff-12")).toBeTruthy();
});

test("result without Undo or any action draws no action row", () => {
  const { container } = render(
    <ResultCard
      kind="result"
      eyebrow="Change"
      title="cache-proposal.md · 4 changes"
      badgeLabel={badge.done.undone}
      when="Oct 28, 09:44"
      who="undoes the 09:41 edit"
      lifecycle={lifecycle()}
    />,
  );
  expect(screen.queryAllByRole("button")).toHaveLength(0);
  expect(container.textContent).toContain("Recorded Oct 28, 09:44");
});
