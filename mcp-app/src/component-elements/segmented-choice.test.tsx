import { render, screen } from "@testing-library/react";

import { ToggleGroup, ToggleGroupItem } from "./segmented-choice";

function Group({ orientation }: { orientation: "horizontal" | "vertical" }) {
  return (
    <ToggleGroup aria-label="Pick" orientation={orientation} spacing={0}>
      <ToggleGroupItem value="a">A</ToggleGroupItem>
      <ToggleGroupItem value="b">B</ToggleGroupItem>
    </ToggleGroup>
  );
}

test("side by side, items join with a left rule", () => {
  render(<Group orientation="horizontal" />);
  const item = screen.getByRole("button", { name: "B" });
  expect(item.className).toContain(
    "[&+&]:border-l-(length:--border-width-regular)",
  );
  expect(item.className).not.toContain("justify-start");
});

test("stacked, items fill the width and join with a top rule", () => {
  render(<Group orientation="vertical" />);
  const item = screen.getByRole("button", { name: "B" });
  expect(item.className).toContain(
    "[&+&]:border-t-(length:--border-width-regular)",
  );
  expect(item.className).toContain("justify-start");
});
