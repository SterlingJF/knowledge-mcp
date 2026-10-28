import { fireEvent, render, screen } from "@testing-library/react";
import { Undo2 } from "lucide-react";

import { action } from "@/copy/en";
import { Button } from "./button";

describe("Button", () => {
  it("fires onClick and renders a leading icon", () => {
    const onClick = vi.fn<(...args: unknown[]) => void>();
    const { container } = render(
      <Button variant="primary" icon={<Undo2 />} onClick={onClick}>
        {action.undo}
      </Button>,
    );
    fireEvent.click(screen.getByRole("button", { name: action.undo }));
    expect(onClick).toHaveBeenCalledOnce();
    expect(container.querySelector("button > svg")).not.toBeNull();
  });

  it("takes keyboard focus", () => {
    render(<Button>{action.undo}</Button>);
    const button = screen.getByRole("button", { name: action.undo });
    button.focus();
    expect(document.activeElement).toBe(button);
  });

  it("does not fire when disabled", () => {
    const onClick = vi.fn<(...args: unknown[]) => void>();
    render(
      <Button disabled onClick={onClick}>
        {action.notNow}
      </Button>,
    );
    const button = screen.getByRole("button", { name: action.notNow });
    fireEvent.click(button);
    expect(onClick).not.toHaveBeenCalled();
  });
});
