import { act, fireEvent, render, screen } from "@testing-library/react";

import { label } from "@/copy/en";

import { SegmentedChoice } from "./segmented-choice";

const two = [
  { value: "current", label: label.current },
  { value: "proposed", label: label.proposed },
] as const;
const five = ["a", "b", "c", "d", "e"].map((v) => ({ value: v, label: v }));

describe("SegmentedChoice", () => {
  it("is a radio group showing the controlled value and reporting a new pick", () => {
    const onValueChange = vi.fn<(...args: unknown[]) => void>();
    render(
      <SegmentedChoice
        aria-label={label.changes}
        options={two}
        value="current"
        onValueChange={onValueChange}
      />,
    );
    expect(
      screen.getByRole("radiogroup", { name: label.changes }),
    ).toBeTruthy();
    const current = screen.getByRole("radio", { name: label.current });
    expect(current.getAttribute("aria-checked")).toBe("true");
    expect(current.hasAttribute("aria-pressed")).toBe(false);
    fireEvent.click(screen.getByRole("radio", { name: label.proposed }));
    expect(onValueChange).toHaveBeenCalledWith("proposed");
  });

  it("starts undecided with nothing checked", () => {
    render(
      <SegmentedChoice
        aria-label="x"
        options={two}
        value={null}
        onValueChange={() => {}}
      />,
    );
    for (const r of screen.getAllByRole("radio"))
      expect(r.getAttribute("aria-checked")).toBe("false");
  });

  it("never deselects by re-clicking the current option", () => {
    const onValueChange = vi.fn<(...args: unknown[]) => void>();
    render(
      <SegmentedChoice
        aria-label="x"
        options={two}
        value="current"
        onValueChange={onValueChange}
      />,
    );
    fireEvent.click(screen.getByRole("radio", { name: label.current }));
    expect(onValueChange).not.toHaveBeenCalled();
  });

  it("arrow keys move between options", async () => {
    render(
      <SegmentedChoice
        aria-label="x"
        options={two}
        value={null}
        onValueChange={() => {}}
      />,
    );
    const first = screen.getByRole("radio", { name: label.current });
    await act(async () => first.focus());
    await act(async () => {
      fireEvent.keyDown(first, { key: "ArrowRight", code: "ArrowRight" });
    });
    expect(document.activeElement).toBe(
      screen.getByRole("radio", { name: label.proposed }),
    );
  });

  it("three options sit side by side", () => {
    const three = [...two, { value: "x", label: "x" }];
    render(
      <SegmentedChoice
        aria-label="x"
        options={three}
        value={null}
        onValueChange={() => {}}
      />,
    );
    expect(screen.getByRole("radiogroup").getAttribute("data-layout")).toBe(
      "row",
    );
    expect(screen.getAllByRole("radio")).toHaveLength(3);
  });

  it("more than three options always stack", () => {
    render(
      <SegmentedChoice
        aria-label="x"
        options={five}
        value="c"
        onValueChange={() => {}}
      />,
    );
    const group = screen.getByRole("radiogroup");
    expect(group.getAttribute("data-layout")).toBe("stacked");
    expect(group.getAttribute("aria-orientation")).toBe("vertical");
    expect(screen.getAllByRole("radio")).toHaveLength(5);
  });

  it("stacks when the row is wider than its space", () => {
    let fire = () => {};
    vi.stubGlobal(
      "ResizeObserver",
      class {
        constructor(cb: () => void) {
          fire = cb;
        }
        observe() {}
        disconnect() {}
      },
    );
    const width = vi
      .spyOn(HTMLElement.prototype, "clientWidth", "get")
      .mockReturnValue(100);
    vi.spyOn(HTMLElement.prototype, "scrollWidth", "get").mockReturnValue(300);
    render(
      <SegmentedChoice
        aria-label="x"
        options={two}
        value={null}
        onValueChange={() => {}}
      />,
    );
    expect(screen.getByRole("radiogroup").getAttribute("data-layout")).toBe(
      "stacked",
    );
    width.mockReturnValue(400);
    act(() => fire());
    expect(screen.getByRole("radiogroup").getAttribute("data-layout")).toBe(
      "row",
    );
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("refuses fewer than 2 options", () => {
    vi.spyOn(console, "error").mockImplementation(() => {});
    expect(() =>
      render(
        <SegmentedChoice
          aria-label="x"
          options={[two[0]]}
          value={null}
          onValueChange={() => {}}
        />,
      ),
    ).toThrow("2 or more options");
    vi.restoreAllMocks();
  });
});
