import { render, screen } from "@testing-library/react";

import { badge } from "@/copy/en";
import { Badge } from "./badge";

describe("Badge", () => {
  it("leads a waiting badge with a pulsing dot", () => {
    const { container } = render(
      <Badge tone="waiting">{badge.waiting.needsOk}</Badge>,
    );
    expect(screen.getByText(badge.waiting.needsOk)).toBeTruthy();
    const first = container.querySelector(
      "[data-tone=waiting]",
    )!.firstElementChild;
    expect(first?.getAttribute("data-testid")).toBe("pulse-dot");
  });

  it("keeps the dot when motion is reduced", () => {
    vi.stubGlobal("matchMedia", (q: string) => ({
      matches: q.includes("reduce"),
      media: q,
      addEventListener() {},
      removeEventListener() {},
    }));
    render(<Badge tone="waiting">{badge.waiting.needsOk}</Badge>);
    expect(screen.getByTestId("pulse-dot")).toBeTruthy();
    vi.unstubAllGlobals();
  });

  it("marks done with a check and refused with a warning", () => {
    const { container } = render(
      <>
        <Badge tone="done">{badge.done.saved}</Badge>
        <Badge tone="refused">{badge.refused.cantUndo}</Badge>
      </>,
    );
    expect(
      container.querySelector("[data-tone=done] [data-icon=done]"),
    ).not.toBeNull();
    expect(
      container.querySelector("[data-tone=refused] [data-icon=refused]"),
    ).not.toBeNull();
  });

  it.each(["neutral"] as const)("shows %s without dot or icon", (tone) => {
    const { container } = render(<Badge tone={tone}>x</Badge>);
    expect(container.querySelector("svg, [data-testid=pulse-dot]")).toBeNull();
  });
});
