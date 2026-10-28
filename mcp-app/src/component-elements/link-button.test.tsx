import { fireEvent, render, screen } from "@testing-library/react";
import { vi } from "vitest";

import { LinkButton } from "./link-button";

test("a plain button that passes aria and clicks through", () => {
  const onClick = vi.fn<() => void>();
  render(
    <LinkButton aria-expanded={false} aria-controls="d" onClick={onClick}>
      Show the change
    </LinkButton>,
  );
  const b = screen.getByRole("button", { name: "Show the change" });
  expect(b.getAttribute("type")).toBe("button");
  expect(b.getAttribute("aria-expanded")).toBe("false");
  expect(b.getAttribute("aria-controls")).toBe("d");
  expect(b.className).toContain("pointer-coarse:before:h-(--km-target)");
  fireEvent.click(b);
  expect(onClick).toHaveBeenCalledOnce();
});
