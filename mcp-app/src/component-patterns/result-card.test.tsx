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

test("result: done badge, what · when · who, Undo first", () => {
  const life = lifecycle();
  render(
    <ResultCard
      kind="result"
      eyebrow="Edit"
      title="cache-proposal.md"
      badgeLabel={badge.done.saved}
      what="4 changes"
      when="just now"
      who="you"
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
  expect(screen.getByText("4 changes · just now · you")).toBeTruthy();
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
