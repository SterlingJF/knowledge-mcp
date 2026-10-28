import { fireEvent, render, screen } from "@testing-library/react";

import { label } from "@/copy/en";
import { SegmentedChoice } from "./segmented-choice";

const options = [
  { value: "current", label: label.current },
  { value: "proposed", label: label.proposed },
] as const;

describe("SegmentedChoice", () => {
  it("shows the controlled value as pressed and reports a new pick", () => {
    const onValueChange = vi.fn<(...args: unknown[]) => void>();
    render(
      <SegmentedChoice
        aria-label={label.changes}
        options={options}
        value="current"
        onValueChange={onValueChange}
      />,
    );
    expect(
      screen
        .getByRole("button", { name: label.current })
        .getAttribute("aria-pressed"),
    ).toBe("true");
    fireEvent.click(screen.getByRole("button", { name: label.proposed }));
    expect(onValueChange).toHaveBeenCalledWith("proposed");
    // Controlled: nothing changes until the parent updates value.
    expect(
      screen
        .getByRole("button", { name: label.proposed })
        .getAttribute("aria-pressed"),
    ).toBe("false");
  });

  it("starts undecided with nothing pressed", () => {
    render(
      <SegmentedChoice
        aria-label={label.changes}
        options={options}
        value={null}
        onValueChange={() => {}}
      />,
    );
    for (const name of [label.current, label.proposed]) {
      expect(
        screen.getByRole("button", { name }).getAttribute("aria-pressed"),
      ).toBe("false");
    }
  });

  it("never deselects by re-clicking the current option", () => {
    const onValueChange = vi.fn<(...args: unknown[]) => void>();
    render(
      <SegmentedChoice
        aria-label={label.changes}
        options={options}
        value="current"
        onValueChange={onValueChange}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: label.current }));
    expect(onValueChange).not.toHaveBeenCalled();
  });

  it("refuses fewer than 2 or more than 3 options", () => {
    vi.spyOn(console, "error").mockImplementation(() => {});
    expect(() =>
      render(
        <SegmentedChoice
          aria-label="x"
          options={[options[0]]}
          value="current"
          onValueChange={() => {}}
        />,
      ),
    ).toThrow("2 or 3 options");
  });
});
