import { fireEvent, render, screen } from "@testing-library/react";

import { action } from "@/copy/en";
import { FullViewButton } from "./full-view-button";

it("asks for the full view and marks itself as chrome", () => {
  const onRequestFullView = vi.fn<(...args: unknown[]) => void>();
  render(<FullViewButton onRequestFullView={onRequestFullView} />);
  const button = screen.getByRole("button", { name: action.fullView });
  expect(button.getAttribute("data-km-chrome")).toBe("full-view");
  fireEvent.click(button);
  expect(onRequestFullView).toHaveBeenCalledOnce();
});
