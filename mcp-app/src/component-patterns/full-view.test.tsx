import { fireEvent, render, screen } from "@testing-library/react";

import { StaticCardHost, stubCardHost } from "@/bridge/static";
import { action, frozen } from "@/copy/en";
import type { CardAction } from "./card-shell";
import { useCardLifecycle } from "./card-lifecycle";
import { FullView } from "./full-view";

const save: CardAction = {
  label: "Save C1",
  message: "Save C1 to a.md",
  frozenLine: frozen.approved,
  variant: "primary",
};

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

test("flat, no Full view button, and a press sends then returns inline", () => {
  const host = stubCardHost({ displayMode: "fullscreen" });
  const { container } = render(
    <StaticCardHost host={host}>
      <Full />
    </StaticCardHost>,
  );
  expect(container.querySelector("section")?.dataset.flat).toBe("true");
  expect(screen.getByText("Every change")).toBeTruthy();
  expect(screen.queryByRole("button", { name: action.fullView })).toBeNull();
  fireEvent.click(screen.getByRole("button", { name: "Save C1" }));
  expect(host.sent).toEqual(["Save C1 to a.md"]);
  expect(host.requested).toEqual(["inline"]);
  expect(screen.getByText(frozen.approved)).toBeTruthy();
});
