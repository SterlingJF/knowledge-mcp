import { render, screen } from "@testing-library/react";

import { CardSkeleton } from "./skeleton";

describe("CardSkeleton", () => {
  it("draws header, rows and actions in the card's shape", () => {
    const { container } = render(
      <CardSkeleton label="Loading" rows={3} actions={2} />,
    );
    expect(screen.getByRole("status", { name: "Loading" })).toBeTruthy();
    expect(container.querySelectorAll('[data-slot="skeleton"]')).toHaveLength(7);
  });

  it("shimmers with the token and stops under reduced motion, with no spinner", () => {
    const { container } = render(<CardSkeleton label="Loading" />);
    const block = container.querySelector('[data-slot="skeleton"]')!;
    expect(block.className).toContain("--km-shimmer");
    expect(block.className).toContain("motion-reduce:animate-none");
    expect(block.className).not.toContain("animate-pulse");
    expect(container.querySelector(".animate-spin")).toBeNull();
  });
});
