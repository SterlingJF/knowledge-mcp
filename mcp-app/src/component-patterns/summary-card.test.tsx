import { fireEvent, render, screen } from "@testing-library/react";
import { vi } from "vitest";

import { action, badge, frozen } from "@/copy/en";
import type { CardAction } from "./card-shell";
import { useCardLifecycle } from "./card-lifecycle";
import { FullView } from "./full-view";
import { StubHost, stubHost } from "./host-double";
import { SummaryCard } from "./summary-card";

vi.mock("@/bridge/bridge", () => import("./host-double"));

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

function Full() {
  const lifecycle = useCardLifecycle();
  return (
    <FullView
      eyebrow="Review"
      title="a.md"
      actions={[save]}
      lifecycle={lifecycle}
    >
      <p>Every change</p>
    </FullView>
  );
}

test("summary shows the rows and opens the full view", () => {
  const host = stubHost();
  render(
    <StubHost host={host}>
      <Summary />
    </StubHost>,
  );
  expect(screen.getByText("Changes")).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: action.fullView }));
  expect(host.requests).toEqual(["fullscreen"]);
});

test("no Full view button when the host can't", () => {
  render(
    <StubHost host={stubHost({ canFullView: false })}>
      <Summary />
    </StubHost>,
  );
  expect(screen.queryByRole("button", { name: action.fullView })).toBeNull();
});

test("full view is flat, and a press sends then returns inline", () => {
  const host = stubHost({ displayMode: "fullscreen" });
  const { container } = render(
    <StubHost host={host}>
      <Full />
    </StubHost>,
  );
  expect(container.querySelector("section")?.dataset.flat).toBe("true");
  expect(screen.getByText("Every change")).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "Save C1" }));
  expect(host.sent).toEqual(["Save C1 to a.md"]);
  expect(host.requests).toEqual(["inline"]);
  expect(screen.getByText(frozen.approved)).toBeTruthy();
});
