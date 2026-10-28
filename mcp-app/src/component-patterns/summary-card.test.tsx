import { fireEvent, render, screen } from "@testing-library/react";

import { action, badge, frozen } from "@/copy/en";
import type { CardAction } from "./card-shell";
import { useCardLifecycle } from "./card-lifecycle";
import { StaticCardHost, stubCardHost } from "@/bridge/static";
import { SummaryCard } from "./summary-card";

const save: CardAction = {
  label: "Save C1",
  message: "Save C1 to a.md",
  frozenLine: frozen.approved,
  variant: "primary",
};

function Summary() {
  const lifecycle = useCardLifecycle();
  return (
    <SummaryCard
      eyebrow="Review"
      title="a.md"
      badge={{ tone: "waiting", label: badge.waiting.needsOk }}
      rows={[{ label: "Changes", value: "4" }]}
      actions={[save]}
      lifecycle={lifecycle}
    />
  );
}

test("summary shows the rows and opens the full view", () => {
  const host = stubCardHost();
  render(
    <StaticCardHost host={host}>
      <Summary />
    </StaticCardHost>,
  );
  expect(screen.getByText("Changes")).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: action.fullView }));
  expect(host.requested).toEqual(["fullscreen"]);
});

test("no Full view button when the host can't", () => {
  render(
    <StaticCardHost host={stubCardHost({ canFullView: false })}>
      <Summary />
    </StaticCardHost>,
  );
  expect(screen.queryByRole("button", { name: action.fullView })).toBeNull();
});
